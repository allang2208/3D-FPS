#include "DungeonRunSubsystem.h"
#include "DungeonRoomSubsystem.h"
#include "../Multiplayer/ColdSteelAuthorityContext.h"
#include "AuthoredDungeonGenerator.h"
#include "FacilityHallEncounter.h"
#include "DungeonThemeEncounter.h"
#include "DungeonShortcutGate.h"
#include "../UI/ColdSteelStatusModel.h"
#include "../Multiplayer/ColdSteelPlayerState.h"
#include "GameFramework/PlayerController.h"
#include "../UI/StatusEffectsComponent.h"
#include "GameFramework/Pawn.h"
#include "Engine/TargetPoint.h"
#include "Engine/World.h"
#include "Engine/Level.h"
#include "Engine/GameInstance.h"
#include "EngineUtils.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Misc/DateTime.h"

void UDungeonRunSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Collection.InitializeDependency<UTaskTrackingSubsystem>();
    Super::Initialize(Collection);
    GetWorld()->GetSubsystem<UTaskTrackingSubsystem>()->RegisterSource(this);
}

bool UDungeonRunSubsystem::AnyThemedRouteCleared() const
{
    if(!bActive)return false;
    for(int32 R=1;R<=3;++R)
    {
        const FString Route=FString::Printf(TEXT("Route%d"),R);int32 Rooms=0;bool Complete=true;
        for(const auto& Node:Nodes)if(Node.bCombatRoom&&Node.Route==Route)
        {
            ++Rooms;
            const bool Passed=AFacilityHallEncounter::IsMedical(Node.Module) ? IsMedicalBossDefeated()
                : AFacilityHallEncounter::IsFreight(Node.Module) ? IsFreightBossDefeated()
                : AFacilityHallEncounter::IsEcology(Node.Module) ? IsEcologyBossDefeated()
                : AFacilityHallEncounter::IsPower(Node.Module) ? IsPowerBossDefeated()
                : AFacilityHallEncounter::IsIncineration(Node.Module) ? IsIncinerationBossDefeated()
                : AFacilityHallEncounter::IsStaffLiving(Node.Module) ? IsStaffLivingBossDefeated() : IsRoomCleared(Node.Id);
            if(!Passed){Complete=false;break;}
        }
        if(Rooms>0&&Complete)return true;
    }
    return false;
}

void UDungeonRunSubsystem::Deinitialize()
{
    if (auto* Tracking = GetWorld()->GetSubsystem<UTaskTrackingSubsystem>()) Tracking->UnregisterSource(this);
    UnbindDungeon();
    Super::Deinitialize();
}

UDungeonRunSubsystem* UDungeonRunSubsystem::Get(const UWorld* World)
{
    return World ? World->GetSubsystem<UDungeonRunSubsystem>() : nullptr;
}

ULevel* UDungeonRunSubsystem::MapLevel() const
{
    const auto* G=Generator.Get();
    if (!bActive || !G || !G->ActorHasTag(TEXT("DungeonAssembly.Ready")) ||
        (!G->NetworkRunId.IsEmpty() && G->NetworkRunId!=CurrentRunId)) return nullptr;
    ULevel* Level=G->GetLevel();
    if (!Level || !Level->bIsVisible) return nullptr;
    const auto* Room=UDungeonRoomSubsystem::Get(GetWorld());
    return !Room || Room->ReadyDungeonLevel()==Level ? Level : nullptr;
}

bool UDungeonRunSubsystem::BindCompletedDungeon(AAuthoredDungeonGenerator* InGenerator)
{
    UnbindDungeon();
    if (!InGenerator) return false;
    UWorld* World = GetWorld();
    if (!World || !World->IsGameWorld()) return false;

    Generator = InGenerator;
    // Catalog first: room_ids classify combat rooms while the manifest is parsed.
    ParseCatalog(InGenerator->ModuleCatalogJson);
    Seed = InGenerator->GeneratedSeed;
    if (!ParseLayoutManifest(InGenerator->LayoutManifestJson))
    {
        UE_LOG(LogTemp, Warning, TEXT("[DungeonRun] 布局清单解析失败，运行状态服务未激活。"));
        UnbindDungeon();
        return false;
    }
    const FVector Offset=InGenerator->RuntimeOffset();
    StartPosition+=Offset;
    if (ReservedStartRoom.IsValid) ReservedStartRoom=ReservedStartRoom.ShiftBy(Offset);
    for(auto& Node:Nodes)
    {
        Node.Origin+=Offset;Node.Volume=Node.Volume.ShiftBy(Offset);
        for(FBox& Cell:Node.Cells)Cell=Cell.ShiftBy(Offset);
        for(FBox& Cell:Node.WalkCells)Cell=Cell.ShiftBy(Offset);
        for(FVector& Anchor:Node.NavigationAnchors)Anchor+=Offset;
        for(auto& Door:Node.Doors)Door.FloorCenter+=Offset;
    }
    ComputeDepth();

    CurrentRunId = InGenerator->NetworkRunId.IsEmpty()?FString::Printf(TEXT("%d-%08X"),Seed,(uint32)(FDateTime::UtcNow().GetTicks()>>20)):InGenerator->NetworkRunId;
    bActive = true;

    if (World->GetNetMode() != NM_Client)
    {
        TArray<int32> HallRooms;
        TArray<FDungeonRunDoor> ForwardDoors;
        for (const auto& Node : Nodes)
            if (AFacilityHallEncounter::IsHall(Node.Module)) HallRooms.Add(Node.Id);
        // FacilityTransit is the authored three-way junction. Its fourth socket
        // leads back into reception and belongs inside the same combat area.
        for (const auto& Node : Nodes)
            if (Node.Module == TEXT("FacilityTransit"))
                for (const auto& Door : Node.Doors)
                    if (!HallRooms.Contains(Door.Neighbor)) ForwardDoors.Add(Door);
        FActorSpawnParameters ThemeParams;
        ThemeParams.Owner = InGenerator; ThemeParams.ObjectFlags |= RF_Transient;
        if (HallRooms.Num() == 2 && ForwardDoors.Num() == 3)
        {
            auto* Area = World->SpawnActor<ADungeonThemeEncounter>(ADungeonThemeEncounter::StaticClass(), FTransform::Identity, ThemeParams);
            if (Area && Area->Configure(this, InGenerator, HallRooms, ForwardDoors)) HallTheme = Area;
            else if (Area) Area->Destroy();
        }
        if (!HallRooms.IsEmpty() && !HallTheme.IsValid())
            UE_LOG(LogTemp, Error, TEXT("[DungeonTheme] Hall area unavailable: rooms=%d forward_doors=%d; expected two halls and three authored exits."), HallRooms.Num(), ForwardDoors.Num());
        TArray<int32> MedicalRooms;
        TArray<FDungeonRunDoor> MedicalBoundaries;
        for (const auto& Node:Nodes)
            if (AFacilityHallEncounter::IsMedical(Node.Module)) MedicalRooms.Add(Node.Id);
        // Include only connectors whose two endpoints belong to this theme.
        TArray<int32> MedicalAreaRooms=MedicalRooms;
        for (const auto& Node:Nodes) if (Node.bConnector)
        {
            TArray<int32> Neighbors; CollectNeighborRooms(Node.Id,Neighbors);
            if (Neighbors.Num()>=2 && !Neighbors.ContainsByPredicate([&MedicalRooms](int32 Id){return !MedicalRooms.Contains(Id);}))
                MedicalAreaRooms.Add(Node.Id);
        }
        IncludeTreasureSideRooms(MedicalAreaRooms);
        for (const auto& Node:Nodes)
        {
            // Only the doctor's Entry (+Y) and theatre's Service (+X) face
            // outside the medical area. Internal room/corridor doors stay free.
            // Use authored normals: graph depth reverses near the branch merge.
            FVector LocalOutward;
            if (Node.Module==TEXT("MedicalDoctorOffice")) LocalOutward=FVector::RightVector;
            else if (Node.Module==TEXT("AbandonedAnatomyTheatre")) LocalOutward=FVector::ForwardVector;
            else continue;
            const FVector Outward=FRotator(0,Node.Yaw,0).RotateVector(LocalOutward);
            for (const auto& Door:Node.Doors)
                if (!IsOptionalSideNode(Door.Neighbor)&&FVector::DotProduct(Door.OutwardNormal,Outward)>.9)
                    MedicalBoundaries.Add(Door);
        }
        if (MedicalRooms.Num()==3 && MedicalBoundaries.Num()==2)
        {
            auto* Area=World->SpawnActor<ADungeonThemeEncounter>(ADungeonThemeEncounter::StaticClass(),FTransform::Identity,ThemeParams);
            if (Area && Area->Configure(this,InGenerator,MedicalAreaRooms,MedicalBoundaries,EDungeonThemeObjective::MedicalBoss)) MedicalTheme=Area;
            else if (Area) Area->Destroy();
        }
        if (!MedicalRooms.IsEmpty() && !MedicalTheme.IsValid())
            UE_LOG(LogTemp,Error,TEXT("[MedicalEncounter] Expected three medical rooms and two outer boundaries; rooms=%d boundaries=%d"),MedicalRooms.Num(),MedicalBoundaries.Num());
        BindFreightTheme(InGenerator);
        BindEcologyTheme(InGenerator);
        BindPowerTheme(InGenerator);
        BindIncinerationTheme(InGenerator);
        BindStaffLivingTheme(InGenerator);
        BindFinalBossTheme(InGenerator);
        for (const auto& Node : Nodes)
        {
            ADungeonThemeEncounter* Area=AFacilityHallEncounter::IsMedical(Node.Module) ? MedicalTheme.Get()
                : AFacilityHallEncounter::IsFreight(Node.Module) ? FreightTheme.Get()
                : AFacilityHallEncounter::IsEcology(Node.Module) ? EcologyTheme.Get()
                : AFacilityHallEncounter::IsPower(Node.Module) ? PowerTheme.Get()
                : AFacilityHallEncounter::IsIncineration(Node.Module) ? IncinerationTheme.Get()
                : AFacilityHallEncounter::IsStaffLiving(Node.Module) ? StaffLivingTheme.Get()
                : AFacilityHallEncounter::IsFinalBossRoom(Node.Module) ? FinalBossTheme.Get()
                : AFacilityHallEncounter::IsHall(Node.Module) ? HallTheme.Get() : nullptr;
            if (!Area)
            {
                const bool Required=AFacilityHallEncounter::IsHall(Node.Module)||AFacilityHallEncounter::IsMedical(Node.Module)
                    ||AFacilityHallEncounter::IsFreight(Node.Module)||AFacilityHallEncounter::IsEcology(Node.Module)
                    ||AFacilityHallEncounter::IsPower(Node.Module)||AFacilityHallEncounter::IsIncineration(Node.Module)
                    ||AFacilityHallEncounter::IsStaffLiving(Node.Module)||AFacilityHallEncounter::IsFinalBossRoom(Node.Module);
                if(Required){UnbindDungeon();return false;}
                continue;
            }
            FActorSpawnParameters Params;
            Params.Owner = InGenerator;
            Params.ObjectFlags |= RF_Transient;
            if (auto* Encounter = World->SpawnActor<AFacilityHallEncounter>(AFacilityHallEncounter::StaticClass(), FTransform::Identity, Params))
            {
                HallEncounters.Add(Encounter);
                if(!Encounter->Configure(this, Node.Id, InGenerator, Area)){UnbindDungeon();return false;}
            }
            else {UnbindDungeon();return false;}
        }
        if(HallTheme.IsValid()&&!BindReturnLinks(InGenerator)){UnbindDungeon();return false;}
    }

    BeginProfileRun();InitializeShrine();
    if(World->GetNetMode()==NM_Client)ApplySharedProgress(InGenerator->SharedProgress);
    else PublishSharedProgress();

    int32 CombatCount = 0;
    for (const FDungeonRunNode& N : Nodes) if (N.bCombatRoom) ++CombatCount;
    UE_LOG(LogTemp, Log, TEXT("[DungeonRun] 运行绑定：Seed=%d 节点=%d 战斗房=%d RunId=%s"),
        Seed, Nodes.Num(), CombatCount, *CurrentRunId);
    return true;
}

void UDungeonRunSubsystem::UnbindDungeon()
{
    bActive = false;
    for(auto& Gate:ReturnLinkGates)if(Gate.IsValid())Gate->Destroy();
    ReturnLinkGates.Reset();
    for (auto& Encounter : HallEncounters) if (Encounter.IsValid()) Encounter->Destroy();
    HallEncounters.Reset();
    if (HallTheme.IsValid()) HallTheme->Destroy();
    HallTheme.Reset();
    if (MedicalTheme.IsValid()) MedicalTheme->Destroy();
    MedicalTheme.Reset();
    if (FreightTheme.IsValid()) FreightTheme->Destroy();
    FreightTheme.Reset();
    if (EcologyTheme.IsValid()) EcologyTheme->Destroy();
    EcologyTheme.Reset();
    if (PowerTheme.IsValid()) PowerTheme->Destroy();
    PowerTheme.Reset();
    if (IncinerationTheme.IsValid()) IncinerationTheme->Destroy();
    IncinerationTheme.Reset();
    if(StaffLivingTheme.IsValid())StaffLivingTheme->Destroy();
    StaffLivingTheme.Reset();bNetworkStaffLivingBossDefeated=false;
    if(FinalBossTheme.IsValid())FinalBossTheme->Destroy();
    FinalBossTheme.Reset();bNetworkFinalBossDefeated=false;bFinalTreasureLooted=false;
    bShrineClaimed=false;
    HillsShrineWorldId.Invalidate();
    ShrineConfig.Reset();ShrineActor.Reset();ShrineEffects.Reset();ShrineBlessing=NAME_None;
    ShrineName.Reset();ShrineDescription.Reset();ShrineHealFraction=0;
    if(ShrineRecipient.IsValid())UStatusEffectsComponent::Notify(ShrineRecipient.Get());
    ShrineRecipient.Reset();
    bCompleted = false;
    bNetworkEliteDefeated=false;bNetworkMedicalBossDefeated=false;bNetworkFreightBossDefeated=false;bNetworkEcologyBossDefeated=false;bNetworkPowerBossDefeated=false;bNetworkIncinerationBossDefeated=false;SharedProgressMirror={};RoomsWithDefeats.Reset();
    Generator.Reset();
    Nodes.Reset();
    RoomIds.Reset();
    CurrentRunId.Reset();
    ModuleTrackingAreas.Reset();
    HallTrafficBoxes.Reset();
    TrackingRooms.Reset();
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



void UDungeonRunSubsystem::MarkRoomCleared(int32 NodeId)
{
    if(!GetWorld()||GetWorld()->GetNetMode()==NM_Client)return;
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
    if(!GetWorld()||GetWorld()->GetNetMode()==NM_Client)return;
    const FDungeonRunNode* Node = NodeById(NodeId);
    if (!bActive || !Node || Node->bConnector) return;
    const FName Key = RoomKey(NodeId);
    if (Explored.Contains(Key)) return;
    Explored.Add(Key);
    CommitProfileRunState();
}

void UDungeonRunSubsystem::MarkRunCompleted()
{
    if(!GetWorld()||GetWorld()->GetNetMode()==NM_Client)return;
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

bool UDungeonRunSubsystem::IsWelcomeEliteDefeated() const
{
    if (!bActive || !Generator.IsValid()) return false;
    if(GetWorld()->GetNetMode()==NM_Client)return bNetworkEliteDefeated;
    for (const auto& Encounter : HallEncounters)
        if (Encounter.IsValid() && Encounter->IsObjectiveEliteDefeated()) return true;
    return false;
}

bool UDungeonRunSubsystem::IsMedicalBossDefeated() const
{
    if (!bActive || !Generator.IsValid()) return false;
    if (GetWorld()->GetNetMode()==NM_Client) return bNetworkMedicalBossDefeated;
    for (const auto& Encounter:HallEncounters)
        if (Encounter.IsValid() && Encounter->IsMedicalBossDefeated()) return true;
    return false;
}

void UDungeonRunSubsystem::AppendTrackedTasks(const APawn* Viewer, TArray<FTrackedTaskView>& Out)
{
    for (auto It = TrackingRooms.CreateIterator(); It; ++It) if (!It.Key().IsValid()) It.RemoveCurrent();
    if (!Viewer || !bActive || (UDungeonRoomSubsystem::Supports(GetWorld())&&!UDungeonRoomSubsystem::IsDungeonPawn(Viewer))) return;
    const TWeakObjectPtr<const APawn> Key(Viewer);
    if (!TrackingRooms.Contains(Key)) TrackingRooms.Add(Key, INDEX_NONE);
    FTrackedTaskView View;
    if (GetTrackingView(Viewer->GetActorLocation(), TrackingRooms[Key], View)) Out.Add(MoveTemp(View));
}

void UDungeonRunSubsystem::AppendJournalTasks(const APawn* Viewer, TArray<FTrackedTaskView>& Out)
{
    const int32 Before = Out.Num();
    AppendTrackedTasks(Viewer, Out);
    if (Out.Num() > Before)
    {
        auto& Task = Out.Last();
        Task.Area = FText::Format(INVTEXT("全队共享 · {0}"), Task.Area);
        if (IsRunCompleted()) Task.Stage = INVTEXT("探索完成");
        return;
    }

    auto& Task = Out.AddDefaulted_GetRef();
    Task.Id = TEXT("dungeon.exploration");
    Task.InstanceId = TEXT("outside-run");
    Task.Title = INVTEXT("地牢探险");
    Task.Area = INVTEXT("全队共享");
    if (Viewer && !UDungeonRoomSubsystem::IsDungeonPawn(Viewer))
    {
        if (const auto* Model = ColdSteelAuthority::ForPawn(Viewer))
        {
            const auto& LastRun = Model->ProfileView().DungeonRun;
            if (LastRun.bCompleted && !LastRun.RunId.IsEmpty())
            {
                Task.InstanceId = LastRun.RunId;
                Task.State = ETrackedTaskState::Completed;
                Task.Stage = INVTEXT("探索完成");
                return;
            }
        }
    }
    Task.State = ETrackedTaskState::NotStarted;
    Task.Stage = INVTEXT("等待地牢目标");
    Task.Hint = INVTEXT("进入地牢后查看本局的区域、目标和队伍进度。");
}

bool UDungeonRunSubsystem::ReadJournalDetails(const APawn* Viewer, const FTrackedTaskView& Task, FTaskJournalDetails& Out) const
{
    if (!Viewer || Task.Id != TEXT("dungeon.exploration")) return false;
    Out.Introduction = INVTEXT("从分流大厅进入废弃设施，沿开启的闸门探索各区，最终抵达终末泵机大厅。队伍共享本局的首领和通路进度。");
    Out.Reward = INVTEXT("终点奖励室宝箱。击败最终首领后可在撤离前搜刮，具体物品以宝箱内容为准。");
    const bool InRun = bActive && Task.InstanceId == CurrentRunId &&
        (!UDungeonRoomSubsystem::Supports(GetWorld()) || UDungeonRoomSubsystem::IsDungeonPawn(Viewer));
    const bool Finished = Task.State == ETrackedTaskState::Completed;
    const bool BossDown = Finished || (InRun && IsFinalBossDefeated());
    auto Add = [&](FName Id, const FText& Text, bool Done, bool Active)
    {
        auto& Row = Out.Steps.AddDefaulted_GetRef();
        Row.Id = Id; Row.Text = Text;
        Row.State = Done ? ETrackedObjectiveState::Completed : Active ? ETrackedObjectiveState::Active : ETrackedObjectiveState::Pending;
        if (const auto* Live = Task.Objectives.FindByPredicate([&](const auto& Goal) { return Goal.Id == Id; }))
            Row = *Live;
    };
    Add(TEXT("enter"), INVTEXT("进入地牢"), InRun || Finished, !InRun && !Finished);
    Add(TEXT("welcome.elite"), INVTEXT("击败分流大厅精英，开启三处闸门"), Finished || (InRun && IsWelcomeEliteDefeated()), false);
    bool HasRegionGoal = false;
    for (const auto& Goal : Task.Objectives)
    {
        if (Goal.Id == TEXT("welcome.elite") || Goal.Id == TEXT("run.completed") ||
            Goal.Id.ToString().StartsWith(TEXT("final."))) continue;
        Out.Steps.Add(Goal);
        HasRegionGoal = true;
    }
    if (!HasRegionGoal)
    {
        const bool AtFinal = BossDown || (InRun && Task.Objectives.ContainsByPredicate([](const auto& Goal) { return Goal.Id == TEXT("final.heque"); }));
        Add(TEXT("regions"), INVTEXT("沿已开启的通路探索各区，前往终末泵机大厅"),
            AtFinal, InRun && IsWelcomeEliteDefeated() && !AtFinal);
    }
    Add(TEXT("final.heque"), INVTEXT("击败最终首领：合阙 M-36"), BossDown, false);
    bool Looted = InRun && IsFinalTreasureLooted();
    if (Finished && !InRun)
        if (const auto* Model = ColdSteelAuthority::ForPawn(Viewer))
        {
            const auto& LastRun = Model->ProfileView().DungeonRun;
            Looted = LastRun.RunId == Task.InstanceId && LastRun.Claimed.Contains(TEXT("FinalTreasure.Taken"));
        }
    if (InRun || !Finished || Looted)
    {
        Add(TEXT("final.treasure"), INVTEXT("搜刮终点奖励室的宝箱（可选）"), Looted, BossDown && !Finished);
        if (Finished && !Looted) Out.Steps.Last().State = ETrackedObjectiveState::Skipped;
    }
    Add(TEXT("final.return"), INVTEXT("通过返程传送门撤离"), Finished, BossDown && !Finished);
    return true;
}

FString UDungeonRunSubsystem::MapAreaName(const FDungeonRunNode& Node) const
{
    if (AFacilityHallEncounter::IsHall(Node.Module) || Node.Module==TEXT("FacilityEntrancePassage")) return TEXT("迎宾大厅");
    if (const FString* Name=ModuleTrackingAreas.Find(Node.Module); Name && !Name->IsEmpty()) return *Name;
    if (Node.bBossArea) return TEXT("地牢终点");
    if (Node.Route==TEXT("Archive")) return TEXT("档案区");
    return {};
}

bool UDungeonRunSubsystem::GetTrackingView(const FVector& PlayerPosition, int32& InOutLastRoom, FTrackedTaskView& Out) const
{
    Out = {};
    if (!bActive || !Generator.IsValid()) return false;
    // Retain the last entered room through sleeves and stairs. Never jump to a
    // nearby region on the other side of a wall just because it is closer.
    const int32 Entered = NodeNearPosition(PlayerPosition, 20.);
    if (NodeById(Entered)) InOutLastRoom = Entered;
    const auto* Room = NodeById(InOutLastRoom);
    if (!Room) Room = NodeById(EntryNodeId);
    if (!Room) return false;
    Out.Id = TEXT("dungeon.exploration");
    Out.InstanceId = CurrentRunId;
    Out.State = IsRunCompleted() ? ETrackedTaskState::Completed : ETrackedTaskState::InProgress;
    Out.Title = FText::FromString(TEXT("地牢探险"));
    Out.Priority = 100;
    const bool Welcome = AFacilityHallEncounter::IsHall(Room->Module) || Room->Module == TEXT("FacilityEntrancePassage");
    const FString Area=MapAreaName(*Room);
    Out.Area=FText::FromString(Area.IsEmpty()?FString(TEXT("过渡区域")):Area);
    if(Room->bBossArea){AppendFinalBossObjectives(Out);return true;}
    auto& Objective = Out.Objectives.AddDefaulted_GetRef();
    if (bCompleted)
    {
        Out.Stage = FText::FromString(TEXT("探索完成"));
        Objective.Id = TEXT("run.completed");
        Objective.Text = FText::FromString(TEXT("地牢探险已完成"));
        Objective.State = ETrackedObjectiveState::Completed;
        return true;
    }
    if (Welcome)
    {
        Out.Stage = FText::FromString(Room->Module == TEXT("FacilityTransit") ? TEXT("第一阶段 · 分流大厅") : TEXT("第一阶段"));
        Objective.Id = TEXT("welcome.elite");
        Objective.Text = FText::FromString(TEXT("击杀一只精英怪物"));
        Objective.Current = IsWelcomeEliteDefeated() ? 1 : 0;
        Objective.Target = 1;
        Objective.State = Objective.Current == 1 ? ETrackedObjectiveState::Completed : ETrackedObjectiveState::Active;
        Out.Hint = FText::FromString(Objective.Current == 1 ? TEXT("目标完成 · 前往下一片区域")
            : TEXT("精英位于分流大厅 · 击败后开启三处闸门"));
    }
    else if (AFacilityHallEncounter::IsMedical(Room->Module))
    {
        Out.Stage=FText::FromString(TEXT("区域首领"));
        Objective.Id=TEXT("medical.bound_congregate");
        Objective.Text=FText::FromString(TEXT("击杀医疗区首领：缚群"));
        Objective.Current=IsMedicalBossDefeated() ? 1 : 0;
        Objective.Target=1;
        Objective.State=Objective.Current==1 ? ETrackedObjectiveState::Completed : ETrackedObjectiveState::Active;
        Out.Hint=FText::FromString(Objective.Current==1 ? TEXT("医疗区已通过 · 前往下一片区域")
            : TEXT("缚群位于第三间大厅 · 击败后开启区域出口"));
    }
    else if (AFacilityHallEncounter::IsFreight(Room->Module))
    {
        Out.Stage=FText::FromString(TEXT("区域首领"));
        Objective.Id=TEXT("freight.mawcrawler");
        Objective.Text=FText::FromString(TEXT("击杀货运区首领：沉匣"));
        Objective.Current=IsFreightBossDefeated() ? 1 : 0;
        Objective.Target=1;
        Objective.State=Objective.Current==1 ? ETrackedObjectiveState::Completed : ETrackedObjectiveState::Active;
        Out.Hint=FText::FromString(Objective.Current==1 ? TEXT("货运区已通过 · 来路与下一地区出口已开放")
            : TEXT("沉匣位于第三间车站一楼 · 击败后开启区域两端闸门"));
    }
    else if (AFacilityHallEncounter::IsEcology(Room->Module))
    {
        Out.Stage=FText::FromString(TEXT("区域首领"));
        Objective.Id=TEXT("ecology.root_crown");
        Objective.Text=FText::FromString(TEXT("击杀生态区首领：根冠 M-34"));
        Objective.Current=IsEcologyBossDefeated() ? 1 : 0;
        Objective.Target=1;
        Objective.State=Objective.Current==1 ? ETrackedObjectiveState::Completed : ETrackedObjectiveState::Active;
        Out.Hint=FText::FromString(Objective.Current==1 ? TEXT("生态区已通过 · 来路与出口已开放")
            : TEXT("根冠 M-34 位于第三间失控生态舱 · 击败后开启区域两端闸门"));
    }
    else if (AFacilityHallEncounter::IsPower(Room->Module))
    {
        Out.Stage=FText::FromString(TEXT("区域首领"));
        Objective.Id=TEXT("power.vortex_coffer");
        Objective.Text=FText::FromString(TEXT("击杀发电区首领：涡电匣 M-30"));
        Objective.Current=IsPowerBossDefeated() ? 1 : 0;
        Objective.Target=1;
        Objective.State=Objective.Current==1 ? ETrackedObjectiveState::Completed : ETrackedObjectiveState::Active;
        Out.Hint=FText::FromString(Objective.Current==1 ? TEXT("发电区已通过 · 来路与下一地区出口已开放")
            : TEXT("涡电匣位于第三间蓄能总控大厅 · 击败后开启区域两端闸门"));
    }
    else if (AFacilityHallEncounter::IsIncineration(Room->Module))
    {
        Out.Stage=FText::FromString(TEXT("区域首领"));
        Objective.Id=TEXT("treatment.incinerator_m66");
        Objective.Text=FText::FromString(TEXT("击杀焚化区首领：焚骸 M-35"));
        Objective.Current=IsIncinerationBossDefeated() ? 1 : 0;
        Objective.Target=1;
        Objective.State=Objective.Current==1 ? ETrackedObjectiveState::Completed : ETrackedObjectiveState::Active;
        Out.Hint=FText::FromString(Objective.Current==1 ? TEXT("焚化区已通过 · 来路与出口已开放")
            : TEXT("焚骸位于第三间烟气净化站 · 处理厅负一层在下楼进入后触发"));
    }
    else if (AFacilityHallEncounter::IsStaffLiving(Room->Module))
    {
        Out.Stage=FText::FromString(TEXT("区域首领"));
        Objective.Id=TEXT("staff_living.blind_supplicant");
        Objective.Text=FText::FromString(TEXT("击杀生活区首领：盲祷者 M-31"));
        Objective.Current=IsStaffLivingBossDefeated() ? 1 : 0;
        Objective.Target=1;
        Objective.State=Objective.Current==1 ? ETrackedObjectiveState::Completed : ETrackedObjectiveState::Active;
        Out.Hint=FText::FromString(Objective.Current==1 ? TEXT("生活区已通过 · 来路与出口已开放")
            : TEXT("盲祷者位于第三间休闲厅 · 击败后开启区域两端闸门"));
    }
    else
    {
        // Later regions already have names and geography; their combat goals
        // will be authored separately. Do not invent kill counts for them.
        Out.Stage = FText::FromString(TEXT("探索中"));
        Objective.Id = FName(*(TEXT("explore.") + Room->Module));
        Objective.Text = FText::FromString(TEXT("探索当前区域"));
        Out.Hint = FText::FromString(TEXT("继续深入地牢"));
    }
    return true;
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
    // Guest profiles are synchronized by their server-owned shadow model.
    if(!GetWorld()||GetWorld()->GetNetMode()==NM_Client||GetWorld()->GetNetMode()==NM_DedicatedServer)return;
    if(UDungeonRoomSubsystem::Supports(GetWorld()))return;
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

void UDungeonRunSubsystem::RecordRoomDefeat(int32 NodeId)
{
    if(bActive&&GetWorld()->GetNetMode()!=NM_Client&&NodeById(NodeId))RoomsWithDefeats.Add(RoomKey(NodeId));
}

void UDungeonRunSubsystem::CommitProfileRunState()
{
    if(!GetWorld()||GetWorld()->GetNetMode()==NM_Client||CurrentRunId.IsEmpty())return;
    PublishSharedProgress();
    if(UDungeonRoomSubsystem::Supports(GetWorld()))
    {
        for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
            if(auto* PC=It->Get();PC&&UDungeonRoomSubsystem::IsDungeonPawn(PC->GetPawn()))EnsurePlayerRun(ColdSteelAuthority::ForPawn(PC->GetPawn()));
        return;
    }
    if(GetWorld()->GetNetMode()!=NM_DedicatedServer)EnsurePlayerRun(StatusModel());
    for(auto It=GetWorld()->GetPlayerControllerIterator();It;++It)
        if(auto* PC=It->Get();PC&&!PC->IsLocalController())
            if(auto* PS=PC->GetPlayerState<AColdSteelPlayerState>())EnsurePlayerRun(PS->GetShadowModel());
}

void UDungeonRunSubsystem::SyncPlayerRun(UColdSteelStatusModel* Model)
{
    if (!Model || CurrentRunId.IsEmpty()) return;
    Model->SyncRuntime();
    auto P = Model->Snapshot();
    // Guard against cross-run contamination when another dungeon bound meanwhile.
    if (P.DungeonRun.RunId != CurrentRunId) return;
    const bool Completed=UDungeonRoomSubsystem::Supports(GetWorld())?P.DungeonRun.bCompleted:bCompleted;
    bool Changed=P.DungeonRun.Cleared.Num()!=Cleared.Num()||P.DungeonRun.Explored.Num()!=Explored.Num()||P.DungeonRun.bCompleted!=Completed;
    P.DungeonRun.Cleared = Cleared;
    P.DungeonRun.Explored = Explored;
    P.DungeonRun.bCompleted = Completed;
    for(const auto& Node:Nodes)if(Node.EncounterRole.StartsWith(TEXT("risk"))&&Cleared.Contains(RoomKey(Node.Id)))
    {
        const FString Key=RoomKey(Node.Id).ToString();
        if(!RoomsWithDefeats.Contains(RoomKey(Node.Id)))continue;
        const FName Claim(*(Key+TEXT(".clear_reward")));
        if(P.DungeonRun.Claimed.Contains(Claim))continue;
        const int64 Gold=FMath::Max<int64>(1,FMath::RoundToInt64((8+Node.ProgressionDepth*2)*(Node.RewardMultiplier-1.)));
        if(!Model->AppendDungeonReward(P,Claim,{{TEXT("souls"),Gold}},Node.Origin))return;
        Changed=true;
    }
    if(Changed)Model->CommitState(MoveTemp(P));
}

UColdSteelStatusModel* UDungeonRunSubsystem::StatusModel() const
{
    UWorld* World = GetWorld();
    const UGameInstance* GI = World ? World->GetGameInstance() : nullptr;
    return GI ? GI->GetSubsystem<UColdSteelStatusModel>() : nullptr;
}
