#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "DungeonRunSubsystem.h"
#include "FacilityMonsterGpuWarmup.h"
#include "FacilityHallEncounter.generated.h"
class ACharacter;
class AStaticMeshActor;

/** One stable run/room slot, still before construction and BeginPlay. */
struct FFacilityPreparedMonster
{
    TWeakObjectPtr<ACharacter> Monster;
    TUniquePtr<FFacilityMonsterGpuWarmup> GpuWarmup;
    TArray<FName> Tags;
    TArray<TWeakObjectPtr<UActorComponent>> AutoActivateComponents;
    int32 Slot = INDEX_NONE;
    double PreparedAt = -1.;
    uint64 EstimatedBytes = 0;
    bool bHidden = false, bCollision = true, bDamage = true, bReplicates = false;
};

struct FFacilityHallSlot
{
    TWeakObjectPtr<ACharacter> Monster;
    int32 Member = 0;
    // Short-lived server-side steering reservation; not an attack or reward slot.
    TWeakObjectPtr<APawn> ApproachTarget;
    FVector ApproachGoal = FVector::ZeroVector;
    double NextApproachUpdate = 0., ApproachExpires = 0.;
    int32 ReleaseGroup = 0;
    /** Four fixed first-wave additions: 0/1 ground floor, 2/3 upper floor. */
    int32 BellowPosition = INDEX_NONE;
    bool bDefeated = false;
    bool bObjectiveElite = false;
    bool bMedicalBoss = false;
    bool bFreightBoss = false;
    bool bEcologyBoss = false;
    bool bPowerBoss = false;
    bool bIncinerationBoss = false;
    bool bFinalBoss = false;
    bool bStaffLivingBoss = false;
    bool bIncinerationBasement = false;
    int32 IncinerationPosition = INDEX_NONE;
    int32 FreightPosition = INDEX_NONE;
    int32 FreightDoor = INDEX_NONE;
    int32 RewardSlot = INDEX_NONE;
    TWeakObjectPtr<APawn> FreightTarget;
    bool bCeiling = false;
    int32 MedicalPosition = INDEX_NONE;
    int32 EcologyPosition = INDEX_NONE;
    int32 PowerPosition = INDEX_NONE;
    int32 StaffLivingPosition = INDEX_NONE;
};

struct FFacilityHallDoor
{
    FString Id;
    TWeakObjectPtr<AStaticMeshActor> Left, Right;
    FTransform ClosedLeft, ClosedRight;
    FVector FloorCenter = FVector::ZeroVector;
    FVector Inward = FVector::ForwardVector;
    float OpenAlpha = 0.f;
    bool bWantOpen = false;
    double NextSpawnAt = 0.;
    double HoldOpenUntil = 0.;
};

/** Server-owned poses for the station's generated, locally assembled door leaves. */
USTRUCT()
struct FFreightServiceDoorNetState
{
    GENERATED_BODY()
    UPROPERTY() FName LeftName;
    UPROPERTY() FName RightName;
    UPROPERTY() FTransform ClosedLeft;
    UPROPERTY() FTransform ClosedRight;
    UPROPERTY() float Alpha = 0.f;
    UPROPERTY() float Target = 0.f;
    UPROPERTY() float ServerSeconds = 0.f;
};

struct FFacilityHallEliteCandidate
{
    int32 Member = INDEX_NONE;
    float Footprint = 0.f;
};

/** Two staff waves plus four first-wave Bellow M-09 in one facility hall. */
UCLASS(NotBlueprintable, Transient)
class FPSGAME_API AFacilityHallEncounter : public AActor
{
    GENERATED_BODY()
public:
    AFacilityHallEncounter();
    virtual ~AFacilityHallEncounter();
    virtual void BeginPlay() override;
    static bool IsHall(const FString& Module);
    static bool IsMedical(const FString& Module);
    static TArray<FString> MedicalMonsterClassPaths();
    static bool IsFreight(const FString& Module);
    static TArray<FString> FreightMonsterClassPaths();
    static bool IsEcology(const FString& Module);
    static TArray<FString> EcologyMonsterClassPaths();
    static bool IsPower(const FString& Module);
    static TArray<FString> PowerMonsterClassPaths();
    static bool IsIncineration(const FString& Module);
    static TArray<FString> IncinerationMonsterClassPaths();
    static bool IsStaffLiving(const FString& Module);
    static TArray<FString> StaffLivingMonsterClassPaths();
    static bool IsFinalBossRoom(const FString& Module);
    static TArray<FString> FinalBossClassPaths();
    static bool IsDoorLeaf(const FString& Module, const FString& Mesh);
    static TArray<FString> MonsterClassPaths();
    static TArray<FString> SelectedMonsterClassPaths(int32 RunSeed);
    static TArray<FString> PreparationAssetPaths(int32 RunSeed);
    static FString ObjectiveEliteClassPath(int32 RunSeed);
    bool IsObjectiveEliteDefeated() const;
    bool IsMedicalBossDefeated() const;
    bool IsFreightBossDefeated() const;
    bool IsEcologyBossDefeated() const;
    bool IsPowerBossDefeated() const;
    bool IsIncinerationBossDefeated() const;
    bool IsStaffLivingBossDefeated() const;
    bool IsFinalBossDefeated() const;
    bool Configure(UDungeonRunSubsystem* InRun, int32 InNode, AAuthoredDungeonGenerator* InGenerator, class ADungeonThemeEncounter* InTheme);
    bool GetStaffPursuitGoal(ACharacter* Staff, APawn* Target, float StopRange, FVector& Goal, float& Acceptance);
    bool AllowsStaffIdleGoal(const ACharacter* Staff, const FVector& Feet) const;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;

private:
    friend class UFacilitySpawnRecheckCommandlet;
#if WITH_EDITOR
    // Explicit offline diagnosis only; unset in normal editor/game encounters.
    TFunction<void(const TCHAR*, const FVector&)> SpawnAuditFailure;
#endif
    friend class UFacilityHallSpawnSubsystem;
    friend class ADungeonThemeEncounter;
    void ConfigureRoom(UDungeonRunSubsystem* InRun,int32 InNode,AAuthoredDungeonGenerator* InGenerator,class ADungeonThemeEncounter* InTheme);
    void UpdateEncounter();
    void ConfigurePacing();
    void UpdatePacing();
    int32 SpawnPriority() const;
    bool HasObjectiveSlot() const;
    void CacheSpawnNavigationAnchors();
    void CacheHallTrafficAreas();
    bool IsHallRestPointClear(const FVector& Feet, float Radius) const;
    bool HasHallSpace(const FVector& Feet, float Radius, const ACharacter* Ignore, float Gap, bool Reservations) const;
    bool HasSpawnRoute(const ACharacter* Defaults,const FVector& Floor,const class ANavigationData* Data) const;
    bool TrySpawnPendingSlot();
    bool TrySpawnObjectiveElite();
    bool PrepareNextSlot();
    int32 FindPreparationSlot() const;
    int32 PreparationPriority(int32 SlotIndex, double& DistanceSquared) const;
    uint64 EstimatePreparationBytes(int32 SlotIndex) const;
    void DiscardPreparation(int32 PreparedIndex, const TCHAR* Reason);
    void DiscardPreparedMonster(const TCHAR* Reason = TEXT("end_play"));
    bool SpawnSlot(int32 SlotIndex);
    bool FindSpawn(const ACharacter* Defaults, const FVector& Candidate, FVector& Location, float Footprint = 0.f,
        const FBox* AuthoredSpawnFloor = nullptr) const;
    bool FindInitialSpawn(const FFacilityHallSlot& Slot, const ACharacter* Defaults, FVector& Location, FRotator& Facing);
    void ConfigureMedical();
    bool FindMedicalSpawn(const FFacilityHallSlot& Slot, const ACharacter* Defaults, FVector& Location, FRotator& Facing);
    void ConfigureFreight();
    void RegisterServiceDoors();
    void EnableServiceDoorReplication();
    void ConfigureFreightReinforcements();
    void UpdateFreightReinforcements();
    APawn* FreightTargetNear(const FVector& Location) const;
    void PublishFreightDoors();
    void PresentFreightDoors();
    UFUNCTION() void OnRep_FreightDoors();
    bool FindFreightSpawn(const FFacilityHallSlot& Slot, const ACharacter* Defaults, FVector& Location, FRotator& Facing);
    void ConfigureEcology();
    bool FindEcologySpawn(const FFacilityHallSlot& Slot, const ACharacter* Defaults, FVector& Location, FRotator& Facing);
    void ConfigurePower();
    bool FindPowerSpawn(const FFacilityHallSlot& Slot, const ACharacter* Defaults, FVector& Location, FRotator& Facing);
    void ConfigureIncineration();
    void ConfigureStaffLiving();
    bool FindStaffLivingSpawn(const FFacilityHallSlot& Slot, const ACharacter* Defaults, FVector& Location, FRotator& Facing);
    void ConfigureFinalBoss();
    void SpawnPumpControls(class AHeQueMonster* Boss);
    bool FindFinalBossSpawn(const ACharacter* Defaults, FVector& Location, FRotator& Facing);
    bool FindIncinerationSpawn(const FFacilityHallSlot& Slot, const ACharacter* Defaults, FVector& Location, FRotator& Facing);
    void UpdateIncinerationBasement();
    bool IsSlotReleased(const FFacilityHallSlot& Slot) const;
    void RecordDefeat(AActor* Monster);
    bool DoorOccupied(const FFacilityHallDoor& Door) const;
    void ApplyDoorPose(FFacilityHallDoor& Door);
    APawn* PlayerInHall() const;
    UFUNCTION() void MonsterDamaged(AActor* Actor, float Damage, const UDamageType* DamageType,
        AController* EventInstigator, AActor* Causer);
    UFUNCTION() void MonsterDestroyed(AActor* Actor);
    UFUNCTION() void DungeonDestroyed(AActor* Actor);

    UPROPERTY(Transient) TArray<TSubclassOf<ACharacter>> Members;
    TWeakObjectPtr<UDungeonRunSubsystem> Run;
    TWeakObjectPtr<AAuthoredDungeonGenerator> Generator;
    TWeakObjectPtr<class ADungeonThemeEncounter> Theme;
    FDungeonRunNode Room;
    TArray<FFacilityHallSlot> Slots;
    TArray<FFacilityHallDoor> Doors;
    FRandomStream Placement;
    TArray<FVector> SpawnNavigationAnchors;
    TArray<FBox> HallTrafficAreas;
    mutable int32 SpawnPathQueriesRemaining=0;
    double NextSpawnAttemptAt=0.;
    int32 FailedSpawnAttempts=0;
    bool bConfigured=false;
    FTimerHandle EncounterTimer;
    // Separate from Slot.Monster: never contributes to wave/kill/door state.
    TArray<TUniquePtr<FFacilityPreparedMonster>> PreparedMonsters;
    double PreparationRequestedAt = -1.;
    int32 FirstWaveCount = 0;
    int32 FirstWaveKills = 0;
    int32 CurrentReleaseGroup=0, LastReleaseGroup=0;
    double PacingClock=0., LastPacingUpdate=-1., GroupReleaseAt=-1., LastGroupReleasedAt=0., ReinforcementReleaseAt=0.;
    int32 ObjectiveEliteSlot = INDEX_NONE;
    TArray<FFacilityHallEliteCandidate> ObjectiveEliteCandidates;
    int32 ObjectiveEliteCandidate = 0;
    int32 ObjectiveEliteFailedAttempts = 0;
    bool bYieldObjectiveEliteRetry = false;
    int32 MedicalBossSlot = INDEX_NONE;
    bool bMedical = false;
    int32 FreightBossSlot = INDEX_NONE;
    bool bFreight = false;
    double NextFreightReinforcementsAt = -1.;
    int32 FreightRound = 0;
    int32 NextFreightRewardSlot = 0;
    UPROPERTY(ReplicatedUsing=OnRep_FreightDoors) TArray<FFreightServiceDoorNetState> FreightDoorStates;
    UPROPERTY(ReplicatedUsing=OnRep_FreightDoors) FString FreightDoorRunId;
    int32 EcologyBossSlot = INDEX_NONE;
    bool bEcology = false;
    int32 PowerBossSlot = INDEX_NONE;
    bool bPower = false;
    int32 IncinerationBossSlot = INDEX_NONE;
    bool bIncineration = false, bIncinerationBasementEntered = false;
    int32 StaffLivingBossSlot = INDEX_NONE;
    bool bStaffLiving = false;
    int32 FinalBossSlot = INDEX_NONE;
    TArray<TWeakObjectPtr<class AHeQuePumpControl>> PumpControls;
    bool bFinalBossRoom = false;
    float ObjectiveEliteFootprint = 0.f;
    int32 NextDoor = 0;
    int32 NextSlot = 0;
    bool bSecondWave = false;
    bool bCleared = false;
    bool bStopping = false;
    bool bFirstWaveObserved=false, bSecondWaveObserved=false;
};
