#pragma once
#include "CoreMinimal.h"
#include "DungeonSharedProgress.h"
#include "Subsystems/WorldSubsystem.h"
#include "Math/RandomStream.h"
#include "Dom/JsonObject.h"
#include "../Tasks/TaskTrackingSubsystem.h"
#include "DungeonRunSubsystem.generated.h"

class AAuthoredDungeonGenerator;
class ATargetPoint;
class UColdSteelStatusModel;

/** Deterministic gameplay streams derived from the layout seed. Never feed layout/dressing/stain streams. */
namespace DungeonRunDomains
{
    constexpr uint32 SpawnComposition = 0x5D0E1A01u;
    constexpr uint32 SpawnPlacement   = 0x5D0E1A02u;
    constexpr uint32 EliteSelection   = 0x5D0E1A03u;
    constexpr uint32 ChestLoot        = 0x5D0E1A04u;
    constexpr uint32 Alarm            = 0x5D0E1A05u;
    constexpr uint32 ShrineSelection  = 0x5D0E1A06u;
    constexpr uint32 ChestMaterials   = 0x5D0E1A07u;
    constexpr uint32 EncounterGroups  = 0x5D0E1A08u;
}

struct FDungeonRunDoor
{
    int32 Neighbor=INDEX_NONE;
    FVector FloorCenter=FVector::ZeroVector;
    FVector OutwardNormal=FVector::ZeroVector;
    double Width=300,Height=280;
};

/** One layout-manifest node. Connectors stay in the graph for adjacency but never count toward room depth. */
struct FDungeonRunNode
{
    static int32 FloorAtElevation(double Z, double EntryZ)
    {
        return FMath::RoundToInt((Z - EntryZ) / 540.);
    }

    int32 Id = INDEX_NONE;
    FString Module;
    FString Route;
    FString MissionId,EncounterRole;
    int32 ThreatBonus=0;
    double RewardMultiplier=1.;
    int32 Floor = 0;
    FVector Origin = FVector::ZeroVector;
    /** Authored module orientation, used for floor-specific local spawn regions. */
    double Yaw = 0.;
    FBox Volume = FBox(ForceInit);
    /** Shortest room depth from the entry; connectors add 0, rooms add 1. */
    int32 Depth = 0;
    bool bConnector = false;
    bool bCombatRoom = false;
    bool bJunction = false;
    bool bTreasure = false;
    bool bBossArea = false;
    TArray<int32> Neighbors;
    TArray<FBox> Cells;
    TArray<FBox> WalkCells;
    TArray<FVector> NavigationAnchors;
    TArray<FDungeonRunDoor> Doors;
    int32 ProgressionDepth=-1;
    double DistanceSquared(const FVector& Position)const
    {
        double Best=TNumericLimits<double>::Max();
        for(const FBox& Cell:Cells)Best=FMath::Min(Best,Cell.ComputeSquaredDistanceToPoint(Position));
        return Cells.IsEmpty()&&Volume.IsValid?Volume.ComputeSquaredDistanceToPoint(Position):Best;
    }
    bool AllowsSpawn(const FVector& Position)const
    {
        if(DistanceSquared(Position)>FMath::Square(20.))return false;
        if(WalkCells.IsEmpty())return true;
        for(const FBox& Cell:WalkCells)if(Cell.ComputeSquaredDistanceToPoint(Position)<=FMath::Square(20.))return true;
        return false;
    }
};

/**
 * Per-run graph and state service for the authored randomized dungeon.
 * The generator binds it once per successful runtime assembly (rebind on regeneration).
 * Persistent run state reuses the existing profile field FColdSteelProfile.DungeonRun, so the
 * DungeonLayout::RecordKill gate (called by all five kill-reward paths) dedupes per-slot rewards
 * for monsters tagged with EnemySlotTag(). All gameplay randomness must be consumed through
 * GameplayStream(); layout determinism stays untouched.
 */
UCLASS()
class FPSGAME_API UDungeonRunSubsystem : public UWorldSubsystem, public ITaskTrackingSource
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    static UDungeonRunSubsystem* Get(const UWorld* World);

    /** Generator entry: parse manifest+catalog, build the graph, begin a fresh profile run. */
    bool BindCompletedDungeon(AAuthoredDungeonGenerator* InGenerator);
    void UnbindDungeon();

    void EnsurePlayerRun(UColdSteelStatusModel* Model);
    void RecordRoomDefeat(int32 NodeId);
    void PublishSharedProgress();
    void ApplySharedProgress(const FDungeonSharedProgress& State);
    void FillNetworkState(class UColdSteelWorldSnapshot* Out) const;
    bool ApplyNetworkState(class UColdSteelWorldSnapshot* State);
    bool IsRunActive() const { return bActive; }
    bool IsRunCompleted() const { return bActive&&bCompleted; }
    bool AreRouteObjectivesDefeated(const FString& Route) const;
    int32 RunSeed() const { return Seed; }
    const FString& RunId() const { return CurrentRunId; }
    bool IsWelcomeEliteDefeated() const;
    bool IsMedicalBossDefeated() const;
    bool IsFreightBossDefeated() const;
    bool IsEcologyBossDefeated() const;
    bool IsPowerBossDefeated() const;
    bool IsIncinerationBossDefeated() const;
    bool IsStaffLivingBossDefeated() const;
    bool IsFinalBossDefeated() const;
    bool IsFinalTreasureLooted() const { return bActive&&bFinalTreasureLooted; }
    bool CanUseFinalReturn() const { return IsFinalBossDefeated(); }
    void MarkFinalTreasureLooted(AActor* Chest,APlayerController* Player=nullptr);
    bool CompletePlayerReturn(UColdSteelStatusModel* Model);
    bool IsBoundTo(const AAuthoredDungeonGenerator* Actor) const { return Generator.Get()==Actor; }
    /** Ready geometry of the currently selected instance, including on a listen host in the hub. */
    ULevel* MapLevel() const;
    void MarkFinalReturnUsed(AActor* Portal);
    void CancelFinalReturn(AActor* Portal);
    virtual void AppendTrackedTasks(const APawn* Viewer, TArray<FTrackedTaskView>& Out) override;
    virtual bool ReadJournalDetails(const APawn* Viewer, const FTrackedTaskView& Task, FTaskJournalDetails& Out) const override;
    virtual void AppendJournalTasks(const APawn* Viewer, TArray<FTrackedTaskView>& Out) override;
    bool GetTrackingView(const FVector& PlayerPosition, int32& InOutLastRoom, FTrackedTaskView& Out) const;
    const FVector& EntryPosition() const { return StartPosition; }
    const FBox& StartRoomBounds() const { return ReservedStartRoom; }
    /** Independent per-domain stream; same seed + domain always replays identically. */
    FRandomStream GameplayStream(uint32 Domain) const;

    int32 NumNodes() const { return Nodes.Num(); }
    const FDungeonRunNode* NodeById(int32 Id) const;
    uint32 NodeRandomSalt(int32 Id)const {const auto* N=NodeById(Id);return N&&!N->MissionId.IsEmpty()?GetTypeHash(N->MissionId):uint32(Id)*0x9E3779B9u;}
    const TArray<FDungeonRunNode>& AllNodes() const { return Nodes; }
    FString MapAreaName(const FDungeonRunNode& Node) const;
    /** Catalog room_ids: the ordinary combat-room pool (base rooms plus structural variants). */
    const TArray<FString>& CombatRoomIds() const { return RoomIds; }
    /** Two welcome halls only; authored local boxes cached during the existing catalog read. */
    const TArray<FBox>* HallTrafficClearance(const FString& Module) const { return HallTrafficBoxes.Find(Module); }

    /** Ordinary room (never a connector) whose volume contains Position, else INDEX_NONE. */
    int32 NodeNearPosition(const FVector& Position, double MaxDistance = 250.0) const;
    /** Occupied rooms and their neighbours, across any length of connector chain. */
    void CollectActiveRooms(const FVector& PlayerPosition, TArray<int32>& OutNodeIds) const;
    /** Anchor TargetPoints of a node whose role tag starts with RolePrefix (nullptr = every anchor). */
    TArray<ATargetPoint*> RoomAnchors(int32 NodeId, const TCHAR* RolePrefix) const;
    /** Connector neighbour on the entrance side (shortest depth - 1). INDEX_NONE when absent. */
    int32 EntryConnectorFor(int32 RoomNodeId) const;
    /** Exact authored socket center and inward normal. False for legacy manifests without sockets. */
    bool EstimateDoorway(int32 RoomNodeId, int32 ConnectorNodeId, FVector& OutCenter, FVector& OutNormal) const;
    /** Follow any finite connector chain, stopping at the next room. */
    void CollectNeighborRooms(int32 NodeId,TArray<int32>& OutNodeIds)const;

    bool IsRoomCleared(int32 NodeId) const { return Cleared.Contains(RoomKey(NodeId)); }
    /** Any one complete themed branch is sufficient; never require the other two. */
    bool AnyThemedRouteCleared() const;
    void MarkRoomCleared(int32 NodeId);
    bool IsRoomExplored(int32 NodeId) const { return Explored.Contains(RoomKey(NodeId)); }
    void MarkRoomExplored(int32 NodeId);
    void MarkRunCompleted();
    /** `DungeonEnemy.<RunId>.<Node>.<Slot>`; consumed by DungeonLayout::RecordKill. */
    FName EnemySlotTag(int32 NodeId, int32 SlotIndex) const;

    bool IsShrine(const AActor* Actor) const;
    bool CanClaimShrine() const { return IsShrine(ShrineActor.Get()) && ShrineAvailable() && !HasShrineBlessing(); }
    bool ShrineAvailable() const;
    bool BindHillsShrine(AActor* Actor,FGuid WorldId,const TSharedPtr<FJsonObject>& Choice);
    void UnbindHillsShrine(const AActor* Actor);
    FString ShrineLifetimeText() const { return HillsShrineWorldId.IsValid()?TEXT("当前丘陵世界"):TEXT("本次地牢"); }
    FString ShrinePrompt() const;
    bool ClaimShrine(class APlayerController* Controller,AActor* Target);
    double ShrineEffect(FName Key,const APawn* Viewer=nullptr) const;
    bool HasShrineBlessing(const APawn* Viewer=nullptr) const;
    FName ActiveShrineBlessing(const APawn* Viewer=nullptr) const { return HasShrineBlessing(Viewer) ? ShrineBlessing : NAME_None; }

private:
    bool IsOptionalSideNode(int32 Id) const;
    void IncludeTreasureSideRooms(TArray<int32>& AreaRooms) const;
    bool BindReturnLinks(AAuthoredDungeonGenerator* InGenerator);
    TArray<TWeakObjectPtr<class ADungeonShortcutGate>> ReturnLinkGates;
    FName RoomKey(int32 NodeId)const;
    bool ParseLayoutManifest(const FString& Json);
    void ParseCatalog(const FString& Json);
    void ComputeDepth();
    void BeginProfileRun();
    void CommitProfileRunState();
    void SyncPlayerRun(UColdSteelStatusModel* Model);
    TSet<FName> RoomsWithDefeats;
    bool bNetworkEliteDefeated=false;
    bool bNetworkMedicalBossDefeated=false;
    bool bNetworkFreightBossDefeated=false;
    bool bNetworkEcologyBossDefeated=false;
    bool bNetworkPowerBossDefeated=false;
    bool bNetworkIncinerationBossDefeated=false;
    bool bNetworkStaffLivingBossDefeated=false;
    bool bNetworkFinalBossDefeated=false;
    bool bFinalTreasureLooted=false;
    FDungeonSharedProgress SharedProgressMirror;
    UColdSteelStatusModel* StatusModel() const;

    TWeakObjectPtr<AAuthoredDungeonGenerator> Generator;
    friend class UColdSteelDungeonFogCheckCommandlet;
    TArray<TWeakObjectPtr<class AFacilityHallEncounter>> HallEncounters;
    TWeakObjectPtr<class ADungeonThemeEncounter> HallTheme;
    TWeakObjectPtr<class ADungeonThemeEncounter> MedicalTheme;
    TWeakObjectPtr<class ADungeonThemeEncounter> FreightTheme;
    void BindFreightTheme(AAuthoredDungeonGenerator* InGenerator);
    TWeakObjectPtr<class ADungeonThemeEncounter> EcologyTheme;
    void BindEcologyTheme(AAuthoredDungeonGenerator* InGenerator);
    TWeakObjectPtr<class ADungeonThemeEncounter> PowerTheme;
    void BindPowerTheme(AAuthoredDungeonGenerator* InGenerator);
    TWeakObjectPtr<class ADungeonThemeEncounter> IncinerationTheme;
    void BindIncinerationTheme(AAuthoredDungeonGenerator* InGenerator);
    TWeakObjectPtr<class ADungeonThemeEncounter> StaffLivingTheme;
    void BindStaffLivingTheme(AAuthoredDungeonGenerator* InGenerator);
    TWeakObjectPtr<class ADungeonThemeEncounter> FinalBossTheme;
    void BindFinalBossTheme(AAuthoredDungeonGenerator* InGenerator);
    void AppendFinalBossObjectives(FTrackedTaskView& Out) const;
    TArray<FDungeonRunNode> Nodes;
    TArray<FString> RoomIds;
    TMap<FString, FString> ModuleTrackingAreas;
    TMap<FString, TArray<FBox>> HallTrafficBoxes;
    TMap<TWeakObjectPtr<const APawn>, int32> TrackingRooms;
    FVector StartPosition = FVector::ZeroVector;
    FBox ReservedStartRoom = FBox(ForceInit);
    FVector StartNormal = FVector::ForwardVector;
    int32 Seed = 0;
    FString CurrentRunId;
    TSet<FName> Cleared;
    TSet<FName> Explored;
    bool bActive = false;
    bool bCompleted = false;
    int32 EntryNodeId=INDEX_NONE;
    void InitializeShrine();
    bool ApplyShrineChoice(const TSharedPtr<FJsonObject>& Choice);
    FString HillsShrineReceipt() const;
    FGuid HillsShrineWorldId;
    TSharedPtr<FJsonObject> ShrineConfig;
    TWeakObjectPtr<AActor> ShrineActor;
    TWeakObjectPtr<class APawn> ShrineRecipient;
    FName ShrineBlessing;
    FString ShrineName,ShrineDescription;
    TMap<FName,double> ShrineEffects;
    double ShrineHealFraction=0;
    bool bShrineClaimed=false;
};
