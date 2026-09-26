#include "DungeonRunSubsystem.h"
#include "AuthoredDungeonGenerator.h"
#include "../UI/ColdSteelStatusModel.h"
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

    int32 CombatCount = 0;
    for (const FDungeonRunNode& N : Nodes) if (N.bCombatRoom) ++CombatCount;
    UE_LOG(LogTemp, Log, TEXT("[DungeonRun] 运行绑定：Seed=%d 节点=%d 战斗房=%d 刷怪配置=%d RunId=%s"),
        Seed, Nodes.Num(), CombatCount, SpawnConfigs.Num(), *CurrentRunId);
}

void UDungeonRunSubsystem::UnbindDungeon()
{
    bActive = false;
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
        const double D = N.Volume.ComputeSquaredDistanceToPoint(Position);
        if (D <= BestD) { BestD = D; Best = N.Id; }
    }
    return Best;
}

void UDungeonRunSubsystem::CollectActiveRooms(const FVector& PlayerPosition, TArray<int32>& OutNodeIds) const
{
    OutNodeIds.Reset();
    if (!bActive || Nodes.IsEmpty()) return;

    // Same contract as the room-lighting scheduler: rooms containing the player seed the search,
    // connector chains are traversed at most two hops, ordinary rooms never propagate further.
    TArray<TPair<int32, int32>> Queue;
    TArray<bool> Visited;
    TArray<bool> RoomActive;
    Visited.Init(false, Nodes.Num());
    RoomActive.Init(false, Nodes.Num());
    for (const FDungeonRunNode& N : Nodes)
    {
        if (N.Id == INDEX_NONE || !N.Volume.IsValid) continue;
        if (N.Volume.ComputeSquaredDistanceToPoint(PlayerPosition) > FMath::Square(100.0)) continue;
        if (Visited[N.Id]) continue;
        Visited[N.Id] = true;
        Queue.Emplace(N.Id, 0);
        if (!N.bConnector) RoomActive[N.Id] = true;
    }
    for (int32 Head = 0; Head < Queue.Num(); ++Head)
    {
        const int32 Depth = Queue[Head].Value;
        const FDungeonRunNode& At = Nodes[Queue[Head].Key];
        for (int32 Next : At.Neighbors)
        {
            if (!Nodes.IsValidIndex(Next) || Nodes[Next].Id != Next || Visited[Next]) continue;
            const bool bNextConnector = Nodes[Next].bConnector;
            if (bNextConnector && Depth >= 2) continue;
            Visited[Next] = true;
            Queue.Emplace(Next, Depth + 1);
            if (!bNextConnector) RoomActive[Next] = true;
        }
    }
    for (const FDungeonRunNode& N : Nodes)
        if (N.Id != INDEX_NONE && RoomActive[N.Id]) OutNodeIds.Add(N.Id);
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

    // Entrance side = connector neighbour whose BFS depth is one below the room
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
    if (!Room->Volume.IsValid || !Conn->Volume.IsValid) return false;

    // The corridor sleeve (slightly expanded) intersected with the room box is the doorway patch.
    const FBox Reach(Conn->Volume.Min - FVector(60, 60, 60), Conn->Volume.Max + FVector(60, 60, 60));
    const FVector PMin = FVector::Max(Room->Volume.Min, Reach.Min);
    const FVector PMax = FVector::Min(Room->Volume.Max, Reach.Max);
    if (PMin.X >= PMax.X || PMin.Y >= PMax.Y || PMin.Z >= PMax.Z) return false;

    // Dominant horizontal axis from the corridor toward the room gives the face normal.
    const FVector Delta = Room->Origin - Conn->Origin;
    FVector Normal = FVector::ZeroVector;
    if (FMath::Abs(Delta.X) >= FMath::Abs(Delta.Y)) Normal = FVector(Delta.X >= 0 ? 1.0 : -1.0, 0, 0);
    else Normal = FVector(0, Delta.Y >= 0 ? 1.0 : -1.0, 0);

    // A 300 cm interface must leave a plausible lateral patch; reject degenerate touches.
    const double Lateral = Normal.X != 0 ? (PMax.Y - PMin.Y) : (PMax.X - PMin.X);
    if (Lateral < 150.0) return false;

    FVector Center = (PMin + PMax) * 0.5;
    // Snap to the room face and stand the door on the room floor (standard 280 cm opening).
    if (Normal.X > 0) Center.X = Room->Volume.Min.X;
    else if (Normal.X < 0) Center.X = Room->Volume.Max.X;
    if (Normal.Y > 0) Center.Y = Room->Volume.Min.Y;
    else if (Normal.Y < 0) Center.Y = Room->Volume.Max.Y;
    Center.Z = Room->Volume.Min.Z + 140.0;
    OutCenter = Center;
    OutNormal = Normal;
    return true;
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
    return FName(*FString::Printf(TEXT("DungeonEnemy.%s.%d.%d"), *CurrentRunId, NodeId, SlotIndex));
}

FName UDungeonRunSubsystem::RoomKey(int32 NodeId)
{
    return FName(*FString::Printf(TEXT("Node%d"), NodeId));
}

bool UDungeonRunSubsystem::ParseLayoutManifest(const FString& Json)
{
    Nodes.Reset();
    TSharedPtr<FJsonObject> Root;
    if (Json.IsEmpty() || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Json), Root) || !Root.IsValid())
        return false;

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
        int32 Floor = 0;
        if (N->TryGetNumberField(TEXT("floor"), Floor)) Node.Floor = Floor;
        Node.Origin = ReadVec3(N, TEXT("origin"));
        const FVector VMin = ReadVec3(N, TEXT("volume_min"));
        const FVector VMax = ReadVec3(N, TEXT("volume_max"));
        Node.Volume = FBox(FVector::Min(VMin, VMax), FVector::Max(VMin, VMax));
        Node.bConnector = IsConnectorModuleId(Node.Module);
        Node.bCombatRoom = RoomIds.Contains(Node.Module);
        Node.bJunction = Node.Module == TEXT("Junction");
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
    const FVector N = ReadVec3(Root, TEXT("start_normal"));
    if (!N.IsNearlyZero()) StartNormal = N;

    const TArray<TSharedPtr<FJsonValue>>* Modules = nullptr;
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
                SpawnConfigs.Add(Id, *Spawn);
        }
    }
}

void UDungeonRunSubsystem::ComputeDepth()
{
    if (Nodes.IsEmpty()) return;
    // Root: the piece placed against the authored entry socket.
    int32 Root = INDEX_NONE;
    double Best = TNumericLimits<double>::Max();
    for (const FDungeonRunNode& N : Nodes)
    {
        if (N.Id == INDEX_NONE) continue;
        const double D = FVector::DistSquared(N.Origin, StartPosition);
        if (D < Best) { Best = D; Root = N.Id; }
    }
    if (Root == INDEX_NONE) return;

    TArray<int32> Queue;
    TArray<bool> Visited;
    Visited.Init(false, Nodes.Num());
    Queue.Add(Root);
    Visited[Root] = true;
    Nodes[Root].Depth = 0;
    for (int32 Head = 0; Head < Queue.Num(); ++Head)
    {
        const FDungeonRunNode& At = Nodes[Queue[Head]];
        for (int32 Next : At.Neighbors)
        {
            if (!NodeById(Next) || Visited[Next]) continue;
            Visited[Next] = true;
            // Connectors add no depth; rooms increment (same contract as RoomDistance in lighting).
            Nodes[Next].Depth = At.Depth + (Nodes[Next].bConnector ? 0 : 1);
            Queue.Add(Next);
        }
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
    Model->CommitState(MoveTemp(P));
}

UColdSteelStatusModel* UDungeonRunSubsystem::StatusModel() const
{
    UWorld* World = GetWorld();
    const UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
    return GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
}
