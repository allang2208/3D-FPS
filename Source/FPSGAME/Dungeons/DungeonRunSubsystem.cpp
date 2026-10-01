#include "DungeonRunSubsystem.h"
#include "AuthoredDungeonGenerator.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../UI/StatusEffectsComponent.h"
#include "GameFramework/Pawn.h"
#include "Engine/TargetPoint.h"
#include "Engine/World.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/DateTime.h"

namespace
{
    // Must stay in sync with IsConnectorModule/IsBossModule in AuthoredDungeonLighting.inl:
    // connector sleeves add no room depth, boss pieces are handled by the boss encounter.
    bool IsConnectorModuleId(const FString& Id)
    {
        return Id == TEXT("Transit") || Id == TEXT("Threshold") || Id == TEXT("TreasureLink")
            || Id == TEXT("RouteElbow") || Id == TEXT("BossApproach") || Id == TEXT("StairDrop1080");
    }
    bool IsBossModuleId(const FString& Id)
    {
        return Id == TEXT("BossConfluence") || Id == TEXT("BossPumpHall");
    }
    FVector ReadVec3(const TSharedPtr<FJsonObject>& O, const TCHAR* Key)
    {
        const TArray<TSharedPtr<FJsonValue>>* V = nullptr;
        if (!O.IsValid() || !O->TryGetArrayField(Key, V) || !V || V->Num() < 3) return FVector::ZeroVector;
        return FVector((*V)[0]->AsNumber(), (*V)[1]->AsNumber(), (*V)[2]->AsNumber());
    }
}

void UDungeonRunSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
}

bool UDungeonRunSubsystem::AnyThemedRouteCleared() const
{
    if(!bActive)return false;
    for(int32 R=1;R<=3;++R)
    {
        const FString Route=FString::Printf(TEXT("Route%d"),R);int32 Rooms=0;bool Complete=true;
        for(const auto& Node:Nodes)if(Node.bCombatRoom&&Node.Route==Route)
        {++Rooms;if(!IsRoomCleared(Node.Id)){Complete=false;break;}}
        if(Rooms>0&&Complete)return true;
    }
    return false;
}

void UDungeonRunSubsystem::Deinitialize()
{
    UnbindDungeon();
    Super::Deinitialize();
}

UDungeonRunSubsystem* UDungeonRunSubsystem::Get(const UWorld* World)
{
    return World ? World->GetSubsystem<UDungeonRunSubsystem>() : nullptr;
}

void UDungeonRunSubsystem::BindCompletedDungeon(AAuthoredDungeonGenerator* InGenerator)
{
    UnbindDungeon();
    if (!InGenerator) return;
    UWorld* World = GetWorld();
    if (!World || !World->IsGameWorld()) return;

    Generator = InGenerator;
    // Catalog first: room_ids classify combat rooms while the manifest is parsed.
    ParseCatalog(InGenerator->ModuleCatalogJson);
    Seed = InGenerator->GeneratedSeed;
    if (!ParseLayoutManifest(InGenerator->LayoutManifestJson))
    {
        UE_LOG(LogTemp, Warning, TEXT("[DungeonRun] 布局清单解析失败，运行状态服务未激活。"));
        UnbindDungeon();
        return;
    }
    ComputeDepth();

    CurrentRunId = FString::Printf(TEXT("%d-%08X"), Seed, (uint32)(FDateTime::UtcNow().GetTicks() >> 20));
    BeginProfileRun();
    bActive = true;
    InitializeShrine();

    int32 CombatCount = 0;
    for (const FDungeonRunNode& N : Nodes) if (N.bCombatRoom) ++CombatCount;
    UE_LOG(LogTemp, Log, TEXT("[DungeonRun] 运行绑定：Seed=%d 节点=%d 战斗房=%d 刷怪配置=%d RunId=%s"),
        Seed, Nodes.Num(), CombatCount, SpawnConfigs.Num(), *CurrentRunId);
}

void UDungeonRunSubsystem::UnbindDungeon()
{
    bActive = false;
    bShrineClaimed=false;
    ShrineConfig.Reset();ShrineActor.Reset();ShrineEffects.Reset();ShrineBlessing=NAME_None;
    ShrineName.Reset();ShrineDescription.Reset();ShrineHealFraction=0;
    if(ShrineRecipient.IsValid())UStatusEffectsComponent::Notify(ShrineRecipient.Get());
    ShrineRecipient.Reset();
    bCompleted = false;
    Generator.Reset();
    Nodes.Reset();
    RoomIds.Reset();
    SpawnConfigs.Reset();
    CurrentRunId.Reset();
    Cleared.Reset();
    Explored.Reset();
}

FRandomStream UDungeonRunSubsystem::GameplayStream(uint32 Domain) const
{
    return FRandomStream((int32)HashCombineFast((uint32)Seed, Domain));
}

const FDungeonRunNode* UDungeonRunSubsystem::NodeById(int32 Id) const
{
    if (!Nodes.IsValidIndex(Id) || Nodes[Id].Id != Id) return nullptr;
    return &Nodes[Id];
}

int32 UDungeonRunSubsystem::NodeNearPosition(const FVector& Position, double MaxDistance) const
{
    int32 Best = INDEX_NONE;
    double BestD = FMath::Square(MaxDistance);
    for (const FDungeonRunNode& N : Nodes)
    {
        if (N.Id == INDEX_NONE || N.bConnector || !N.Volume.IsValid) continue;
        const double D = N.DistanceSquared(Position);
        if (D <= BestD) { BestD = D; Best = N.Id; }
    }
    return Best;
}

void UDungeonRunSubsystem::CollectActiveRooms(const FVector& PlayerPosition, TArray<int32>& OutNodeIds) const
{
    OutNodeIds.Reset();
    if (!bActive || Nodes.IsEmpty()) return;
    for (const FDungeonRunNode& N : Nodes)
    {
        if (N.Id == INDEX_NONE || !N.Volume.IsValid) continue;
        if (N.DistanceSquared(PlayerPosition) > FMath::Square(100.0)) continue;
        if(!N.bConnector)OutNodeIds.AddUnique(N.Id);
        TArray<int32> Adjacent;CollectNeighborRooms(N.Id,Adjacent);
        for(int32 Next:Adjacent)OutNodeIds.AddUnique(Next);
    }
}

void UDungeonRunSubsystem::CollectNeighborRooms(int32 NodeId,TArray<int32>& OutNodeIds)const
{
    OutNodeIds.Reset();
    if(!NodeById(NodeId))return;
    TArray<int32> Queue{NodeId};TSet<int32> Seen{NodeId};
    for(int32 Head=0;Head<Queue.Num();++Head)
    {
        for(int32 Next:Nodes[Queue[Head]].Neighbors)
        {
            const auto* N=NodeById(Next);if(!N||Seen.Contains(Next))continue;
            Seen.Add(Next);
            if(N->bConnector)Queue.Add(Next);else OutNodeIds.Add(Next);
        }
    }
}

TArray<ATargetPoint*> UDungeonRunSubsystem::RoomAnchors(int32 NodeId, const TCHAR* RolePrefix) const
{
    TArray<ATargetPoint*> Result;
    UWorld* World = GetWorld();
    const FDungeonRunNode* Node = NodeById(NodeId);
    if (!bActive || !Node || !World) return Result;

    const FName ModuleTag(*FString::Printf(TEXT("DungeonModule.%d.%s"), NodeId, *Node->Module));
    for (TActorIterator<ATargetPoint> It(World); It; ++It)
    {
        ATargetPoint* Anchor = *It;
        if (!Anchor || !Anchor->Tags.Contains(ModuleTag)) continue;
        if (RolePrefix && RolePrefix[0])
        {
            bool bMatch = false;
            for (const FName& Tag : Anchor->Tags)
                if (Tag.ToString().StartsWith(RolePrefix)) { bMatch = true; break; }
            if (!bMatch) continue;
        }
        Result.Add(Anchor);
    }
    return Result;
}

int32 UDungeonRunSubsystem::EntryConnectorFor(int32 RoomNodeId) const
{
    const FDungeonRunNode* Room = NodeById(RoomNodeId);
    if (!Room || Room->bConnector) return INDEX_NONE;

    // Entrance side = connector neighbour whose shortest room depth is one below the room
    // (connectors add no depth). Fallback: shallowest connector neighbour.
    int32 Best = INDEX_NONE;
    double BestD = TNumericLimits<double>::Max();
    int32 Fallback = INDEX_NONE;
    int32 FallbackDepth = MAX_int32;
    double FallbackD = TNumericLimits<double>::Max();
    for (int32 Next : Room->Neighbors)
    {
        const FDungeonRunNode* N = NodeById(Next);
        if (!N || !N->bConnector) continue;
        const double D = FVector::DistSquared(N->Origin, StartPosition);
        if (N->Depth == Room->Depth - 1 && D < BestD) { BestD = D; Best = Next; }
        if (N->Depth < FallbackDepth || (N->Depth == FallbackDepth && D < FallbackD))
        {
            FallbackDepth = N->Depth; FallbackD = D; Fallback = Next;
        }
    }
    return Best != INDEX_NONE ? Best : Fallback;
}

bool UDungeonRunSubsystem::EstimateDoorway(int32 RoomNodeId, int32 ConnectorNodeId, FVector& OutCenter, FVector& OutNormal) const
{
    const FDungeonRunNode* Room = NodeById(RoomNodeId);
    const FDungeonRunNode* Conn = NodeById(ConnectorNodeId);
    if (!Room || !Conn || Room->bConnector || !Conn->bConnector) return false;
    for(const FDungeonRunDoor& Door:Room->Doors)if(Door.Neighbor==ConnectorNodeId)
    {
        OutCenter=Door.FloorCenter+FVector(0,0,Door.Height*.5);
        OutNormal=-Door.OutwardNormal;
        return true;
    }
    // Older manifests without doorway coordinates cannot safely seal an authored
    // irregular room. Leave the encounter open instead of guessing from its AABB.
    return false;
}

const TSharedPtr<FJsonObject>* UDungeonRunSubsystem::SpawnConfigForModule(const FString& ModuleId) const
{
    return SpawnConfigs.Find(ModuleId);
}

void UDungeonRunSubsystem::MarkRoomCleared(int32 NodeId)
{
    const FDungeonRunNode* Node = NodeById(NodeId);
    if (!bActive || !Node || Node->bConnector) return;
    const FName Key = RoomKey(NodeId);
    if (Cleared.Contains(Key)) return;
    Cleared.Add(Key);
    UE_LOG(LogTemp, Log, TEXT("[DungeonRun] 房间清除：Node=%d Module=%s RunId=%s"), NodeId, *Node->Module, *CurrentRunId);
    CommitProfileRunState();
}

void UDungeonRunSubsystem::MarkRoomExplored(int32 NodeId)
{
    const FDungeonRunNode* Node = NodeById(NodeId);
    if (!bActive || !Node || Node->bConnector) return;
    const FName Key = RoomKey(NodeId);
    if (Explored.Contains(Key)) return;
    Explored.Add(Key);
    CommitProfileRunState();
}

void UDungeonRunSubsystem::MarkRunCompleted()
{
    if (!bActive || bCompleted) return;
    bCompleted = true;
    CommitProfileRunState();
}

FName UDungeonRunSubsystem::EnemySlotTag(int32 NodeId, int32 SlotIndex) const
{
    return FName(*FString::Printf(TEXT("DungeonEnemy.%s.%s.%d"), *CurrentRunId, *RoomKey(NodeId).ToString(), SlotIndex));
}

FName UDungeonRunSubsystem::RoomKey(int32 NodeId)const
{
    if(const auto* Node=NodeById(NodeId);Node&&!Node->MissionId.IsEmpty())return FName(*Node->MissionId);
    return FName(*FString::Printf(TEXT("Node%d"), NodeId));
}

bool UDungeonRunSubsystem::ParseLayoutManifest(const FString& Json)
{
    Nodes.Reset();
    EntryNodeId=INDEX_NONE;
    TSharedPtr<FJsonObject> Root;
    if (Json.IsEmpty() || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid())
        return false;
    Root->TryGetNumberField(TEXT("entry_node"),EntryNodeId);

    const TArray<TSharedPtr<FJsonValue>>* NodeValues = nullptr;
    if (!Root->TryGetArrayField(TEXT("nodes"), NodeValues) || !NodeValues) return false;
    for (const TSharedPtr<FJsonValue>& Value : *NodeValues)
    {
        const TSharedPtr<FJsonObject> N = Value.IsValid() ? Value->AsObject() : nullptr;
        if (!N.IsValid()) continue;
        int32 Id = INDEX_NONE;
        if (!N->TryGetNumberField(TEXT("id"), Id) || Id < 0) continue;

        FDungeonRunNode Node;
        Node.Id = Id;
        N->TryGetStringField(TEXT("module"), Node.Module);
        N->TryGetStringField(TEXT("route"), Node.Route);
        N->TryGetStringField(TEXT("mission_id"),Node.MissionId);N->TryGetStringField(TEXT("encounter_role"),Node.EncounterRole);
        N->TryGetNumberField(TEXT("threat_bonus"),Node.ThreatBonus);N->TryGetNumberField(TEXT("reward_multiplier"),Node.RewardMultiplier);
        int32 Floor = 0;
        if (N->TryGetNumberField(TEXT("floor"), Floor)) Node.Floor = Floor;
        Node.Origin = ReadVec3(N, TEXT("origin"));
        const FVector VMin = ReadVec3(N, TEXT("volume_min"));
        const FVector VMax = ReadVec3(N, TEXT("volume_max"));
        Node.Volume = FBox(FVector::Min(VMin, VMax), FVector::Max(VMin, VMax));
        N->TryGetNumberField(TEXT("progression_depth"),Node.ProgressionDepth);
        const TArray<TSharedPtr<FJsonValue>>* Cells=nullptr;
        if(N->TryGetArrayField(TEXT("cells"),Cells))for(const auto& Cell:*Cells)
        {
            const auto C=Cell->AsObject();if(C.IsValid())Node.Cells.Add(FBox(ReadVec3(C,TEXT("min")),ReadVec3(C,TEXT("max"))));
        }
        Node.bConnector = IsConnectorModuleId(Node.Module);
        bool SplitLevelRamp=false;
        N->TryGetBoolField(TEXT("split_level_ramp"),SplitLevelRamp);
        Node.bConnector |= SplitLevelRamp;
        Node.bCombatRoom = RoomIds.Contains(Node.Module);
        if(N->TryGetArrayField(TEXT("walk_cells"),Cells))for(const auto& Cell:*Cells)
        {const auto C=Cell->AsObject();if(C.IsValid())Node.WalkCells.Add(FBox(ReadVec3(C,TEXT("min")),ReadVec3(C,TEXT("max"))));}
        Node.bJunction = Node.Module == TEXT("Junction")||Node.Module.StartsWith(TEXT("Fork"));
        Node.bTreasure = Node.Module == TEXT("Treasure");
        Node.bBossArea = IsBossModuleId(Node.Module) || Node.Route.StartsWith(TEXT("Boss"));
        if (Nodes.Num() <= Id) Nodes.SetNum(Id + 1);
        Nodes[Id] = MoveTemp(Node);
    }

    const TArray<TSharedPtr<FJsonValue>>* Edges = nullptr;
    if (Root->TryGetArrayField(TEXT("connections"), Edges) && Edges)
    {
        for (const TSharedPtr<FJsonValue>& Value : *Edges)
        {
            const TSharedPtr<FJsonObject> E = Value.IsValid() ? Value->AsObject() : nullptr;
            if (!E.IsValid()) continue;
            int32 From = INDEX_NONE, To = INDEX_NONE;
            if (!E->TryGetNumberField(TEXT("from"), From) || !E->TryGetNumberField(TEXT("to"), To)) continue;
            if (!NodeById(From) || !NodeById(To) || From == To) continue;
            Nodes[From].Neighbors.AddUnique(To);
            Nodes[To].Neighbors.AddUnique(From);
            if(E->HasField(TEXT("position"))&&E->HasField(TEXT("from_normal"))&&E->HasField(TEXT("to_normal")))
            {
                double Width=300,Height=280;E->TryGetNumberField(TEXT("width"),Width);E->TryGetNumberField(TEXT("height"),Height);
                const FVector Position=ReadVec3(E,TEXT("position"));
                Nodes[From].Doors.Add({To,Position,ReadVec3(E,TEXT("from_normal")),Width,Height});
                Nodes[To].Doors.Add({From,Position,ReadVec3(E,TEXT("to_normal")),Width,Height});
            }
        }
    }
    return Nodes.Num() > 0;
}

void UDungeonRunSubsystem::ParseCatalog(const FString& Json)
{
    RoomIds.Reset();
    SpawnConfigs.Reset();
    StartPosition = FVector::ZeroVector;
    StartNormal = FVector::ForwardVector;

    TSharedPtr<FJsonObject> Root;
    if (Json.IsEmpty() || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid())
    {
        UE_LOG(LogTemp, Warning, TEXT("[DungeonRun] 模块目录不可解析，战斗房分类与刷怪配置为空。"));
        return;
    }

    const TArray<TSharedPtr<FJsonValue>>* Ids = nullptr;
    if (Root->TryGetArrayField(TEXT("room_ids"), Ids) && Ids)
    {
        for (const TSharedPtr<FJsonValue>& V : *Ids)
            if (V.IsValid() && V->Type == EJson::String) RoomIds.Add(V->AsString());
    }
    StartPosition = ReadVec3(Root, TEXT("start_position"));
    const TSharedPtr<FJsonObject>* Shrine=nullptr;
    if(Root->TryGetObjectField(TEXT("start_shrine"),Shrine))ShrineConfig=*Shrine;
    const FVector N = ReadVec3(Root, TEXT("start_normal"));
    if (!N.IsNearlyZero()) StartNormal = N;

    const TArray<TSharedPtr<FJsonValue>>* Modules = nullptr;
    const TSharedPtr<FJsonObject>* ThemedRoutes = nullptr;
    const bool bThemedRouteClear = Root->TryGetObjectField(TEXT("themed_routes"), ThemedRoutes)
        && ThemedRoutes && ThemedRoutes->IsValid();
    if (Root->TryGetArrayField(TEXT("modules"), Modules) && Modules)
    {
        for (const TSharedPtr<FJsonValue>& Value : *Modules)
        {
            const TSharedPtr<FJsonObject> M = Value.IsValid() ? Value->AsObject() : nullptr;
            if (!M.IsValid()) continue;
            FString Id;
            if (!M->TryGetStringField(TEXT("id"), Id) || Id.IsEmpty()) continue;
            const TSharedPtr<FJsonObject>* Spawn = nullptr;
            if (M->TryGetObjectField(TEXT("spawn"), Spawn) && Spawn && Spawn->IsValid())
            {
                // A clear-to-open exit needs an entry-triggered wave, even when
                // the authored room intentionally leaves its entrance open.
                // Derive this from the same gate specification the assembler uses.
                auto RuntimeSpawn = MakeShared<FJsonObject>();
                RuntimeSpawn->Values = (*Spawn)->Values;
                const TSharedPtr<FJsonObject>* Gate = nullptr;
                RuntimeSpawn->SetBoolField(TEXT("progression_encounter"),
                    M->TryGetObjectField(TEXT("progression_gate"), Gate) && Gate && Gate->IsValid());
                // The archive requires an entire branch, including its ordinary
                // rooms. Their waves need the same entry/reservation guarantee.
                RuntimeSpawn->SetBoolField(TEXT("themed_route_clear_encounter"), bThemedRouteClear);
                SpawnConfigs.Add(Id, RuntimeSpawn);
            }
        }
    }
}

void UDungeonRunSubsystem::ComputeDepth()
{
    if (Nodes.IsEmpty()) return;
    // Root: the piece placed against the authored entry socket.
    int32 Root = EntryNodeId;
    double Best = TNumericLimits<double>::Max();
    if(!NodeById(Root))for (const FDungeonRunNode& N : Nodes)
    {
        if (N.Id == INDEX_NONE) continue;
        const double D = FVector::DistSquared(N.Origin, StartPosition);
        if (D < Best) { Best = D; Root = N.Id; }
    }
    if (Root == INDEX_NONE) return;

    TArray<int32> Queue;
    for(auto& Node:Nodes)Node.Depth=MAX_int32;
    Queue.Add(Root);
    Nodes[Root].Depth = Nodes[Root].bConnector?0:1;
    for (int32 Head = 0; Head < Queue.Num(); ++Head)
    {
        const FDungeonRunNode& At = Nodes[Queue[Head]];
        for (int32 Next : At.Neighbors)
        {
            if (!NodeById(Next)) continue;
            const int32 Candidate=At.Depth+(Nodes[Next].bConnector?0:1);
            if(Candidate<Nodes[Next].Depth){Nodes[Next].Depth=Candidate;Queue.Add(Next);}
        }
    }
    for(auto& Node:Nodes)
    {
        if(Node.Depth==MAX_int32)Node.Depth=0;
        if(Node.ProgressionDepth<0)Node.ProgressionDepth=Node.Depth;
    }
}

void UDungeonRunSubsystem::BeginProfileRun()
{
    UColdSteelStatusModel* Model = StatusModel();
    if (!Model) return;
    Model->SyncRuntime();
    auto P = Model->Snapshot();
    auto& Run = P.DungeonRun;
    Run.RunId = CurrentRunId;
    Run.Seed = Seed;
    if(Generator.IsValid()){Run.GeneratorVersion=5;Run.LayoutManifestJson=Generator->LayoutManifestJson;}
    Run.bCompleted = false;
    // Fresh run: all per-slot kill dedup and room state resets. Legacy Rooms/Connections/Events
    // fields stay untouched (save-compatible, never authored by the randomized dungeon).
    Run.DefeatedEnemies.Reset();
    Run.Cleared.Reset();
    Run.Explored.Reset();
    Run.ActiveEncounters.Reset();
    Run.Claimed.Reset();
    Model->CommitState(MoveTemp(P));
}

void UDungeonRunSubsystem::CommitProfileRunState()
{
    UColdSteelStatusModel* Model = StatusModel();
    if (!Model || CurrentRunId.IsEmpty()) return;
    Model->SyncRuntime();
    auto P = Model->Snapshot();
    // Guard against cross-run contamination when another dungeon bound meanwhile.
    if (P.DungeonRun.RunId != CurrentRunId) return;
    P.DungeonRun.Cleared = Cleared;
    P.DungeonRun.Explored = Explored;
    P.DungeonRun.bCompleted = bCompleted;
    for(const auto& Node:Nodes)if(Node.EncounterRole.StartsWith(TEXT("risk"))&&Cleared.Contains(RoomKey(Node.Id)))
    {
        const FString Key=RoomKey(Node.Id).ToString();bool HadKill=false;
        for(FName Enemy:P.DungeonRun.DefeatedEnemies)if(Enemy.ToString().StartsWith(Key+TEXT("."))){HadKill=true;break;}
        if(!HadKill)continue; // Failed spawn placement must never mint a risk reward.
        const int64 Gold=FMath::Max<int64>(1,FMath::RoundToInt64((8+Node.ProgressionDepth*2)*(Node.RewardMultiplier-1.)));
        if(!Model->AppendDungeonReward(P,FName(*(Key+TEXT(".clear_reward"))),{{TEXT("gold"),Gold}},Node.Origin))return;
    }
    Model->CommitState(MoveTemp(P));
}

UColdSteelStatusModel* UDungeonRunSubsystem::StatusModel() const
{
    UWorld* World = GetWorld();
    const UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
    return GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
}
