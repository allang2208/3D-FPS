#pragma once
#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "Math/RandomStream.h"
#include "Dom/JsonObject.h"
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
    int32 Id = INDEX_NONE;
    FString Module;
    FString Route;
    FString MissionId,EncounterRole;
    int32 ThreatBonus=0;
    double RewardMultiplier=1.;
    int32 Floor = 0;
    FVector Origin = FVector::ZeroVector;
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
class FPSGAME_API UDungeonRunSubsystem : public UWorldSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;

    static UDungeonRunSubsystem* Get(const UWorld* World);

    /** Generator entry: parse manifest+catalog, build the graph, begin a fresh profile run. */
    void BindCompletedDungeon(AAuthoredDungeonGenerator* InGenerator);
    void UnbindDungeon();

    bool IsRunActive() const { return bActive; }
    int32 RunSeed() const { return Seed; }
    const FString& RunId() const { return CurrentRunId; }
    const FVector& EntryPosition() const { return StartPosition; }
    /** Independent per-domain stream; same seed + domain always replays identically. */
    FRandomStream GameplayStream(uint32 Domain) const;

    int32 NumNodes() const { return Nodes.Num(); }
    const FDungeonRunNode* NodeById(int32 Id) const;
    uint32 NodeRandomSalt(int32 Id)const {const auto* N=NodeById(Id);return N&&!N->MissionId.IsEmpty()?GetTypeHash(N->MissionId):uint32(Id)*0x9E3779B9u;}
    const TArray<FDungeonRunNode>& AllNodes() const { return Nodes; }
    /** Catalog room_ids: the ordinary combat-room pool (base rooms plus structural variants). */
    const TArray<FString>& CombatRoomIds() const { return RoomIds; }

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

    /** Per-module catalog `spawn` section (nullptr when the module has no spawn config). */
    const TSharedPtr<FJsonObject>* SpawnConfigForModule(const FString& ModuleId) const;

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
    bool CanClaimShrine() const { return bActive && !bShrineClaimed && ShrineActor.IsValid(); }
    FString ShrinePrompt() const;
    bool ClaimShrine(class APlayerController* Controller,AActor* Target);
    double ShrineEffect(FName Key) const;
    FName ActiveShrineBlessing() const { return bActive && bShrineClaimed ? ShrineBlessing : NAME_None; }

private:
    FName RoomKey(int32 NodeId)const;
    bool ParseLayoutManifest(const FString& Json);
    void ParseCatalog(const FString& Json);
    void ComputeDepth();
    void BeginProfileRun();
    void CommitProfileRunState();
    UColdSteelStatusModel* StatusModel() const;

    TWeakObjectPtr<AAuthoredDungeonGenerator> Generator;
    TArray<FDungeonRunNode> Nodes;
    TArray<FString> RoomIds;
    TMap<FString, TSharedPtr<FJsonObject>> SpawnConfigs;
    FVector StartPosition = FVector::ZeroVector;
    FVector StartNormal = FVector::ForwardVector;
    int32 Seed = 0;
    FString CurrentRunId;
    TSet<FName> Cleared;
    TSet<FName> Explored;
    bool bActive = false;
    bool bCompleted = false;
    int32 EntryNodeId=INDEX_NONE;
    void InitializeShrine();
    TSharedPtr<FJsonObject> ShrineConfig;
    TWeakObjectPtr<AActor> ShrineActor;
    TWeakObjectPtr<class APawn> ShrineRecipient;
    FName ShrineBlessing;
    FString ShrineName,ShrineDescription;
    TMap<FName,double> ShrineEffects;
    double ShrineHealFraction=0;
    bool bShrineClaimed=false;
};
