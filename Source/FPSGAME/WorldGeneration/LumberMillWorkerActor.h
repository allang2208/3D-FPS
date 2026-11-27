#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LumberjackAnimInstance.h"
#include "LumberMillWorkerActor.generated.h"

class UCapsuleComponent;
class USkeletalMeshComponent;
class UStaticMeshComponent;
class USkeletalMesh;
class UStaticMesh;
class UAnimSequence;
class UParticleSystem;
class USoundBase;
class ALumberMillTimberWagon;
class UInstancedStaticMeshComponent;

UENUM()
enum class ELumberWorkerRole : uint8
{
    FellerAndSplitter = 0, // Role 0: Tree felling & stump firewood splitting (BattleAxe)
    Sawyer = 1,            // Role 1: Crosscut sawing at Tool Room canopy sawbuck (TwoManCrosscutSaw)
    HaulerAndDriver = 2,   // Role 2: Carrying logs to wagon bay & driving 17:00 Timber Wagon
};

UENUM()
enum class ELumberWorkerTool : uint8
{
    None = 0,
    BattleAxe,
    CrosscutSaw,
    CarriedLog,
};

/**
 * Replicated friendly Lumberjack worker NPC active at the restored Lumber Mill (09:00..17:00 shift,
 * plus Role 2 driving the 17:00 Timber Wagon along the golden supply route into the village).
 */
UCLASS()
class FPSGAME_API ALumberMillWorker : public AActor
{
    GENERATED_BODY()

public:
    ALumberMillWorker();

    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void OnRep_ReplicatedMovement() override;

    // Server-side initialization & driving controls (called by ULumberMillOperationsSubsystem).
    void InitializeRole(ELumberWorkerRole InRole);
    void SetServerPresentation(ELumberjackAnimState InAnim, ELumberWorkerTool InTool, float InSpeedCmPerSec,
        bool bInRestingIndoors, const FVector& InImpactPoint, ALumberMillTimberWagon* InMountedWagon);

    ELumberWorkerRole GetWorkerRole() const { return static_cast<ELumberWorkerRole>(WorkerRole); }
    USkeletalMeshComponent* GetBodyMesh() const { return BodyMesh; }

private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UCapsuleComponent> Capsule;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> BodyMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> HeadMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> WorkwearMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<USkeletalMeshComponent> HatMesh;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UStaticMeshComponent> ToolMesh;

    UPROPERTY(ReplicatedUsing=OnRep_WorkerRole) uint8 WorkerRole = 0;
    UPROPERTY(ReplicatedUsing=OnRep_WorkState) uint8 ReplicatedAnimState = 0;
    UPROPERTY(ReplicatedUsing=OnRep_WorkState) uint8 ReplicatedTool = 0;
    UPROPERTY(Replicated) float ReplicatedMoveSpeed = 0.f;
    UPROPERTY(ReplicatedUsing=OnRep_WorkState) bool bRestingIndoors = false;
    UPROPERTY(Replicated) FVector_NetQuantize10 ImpactPoint = FVector::ZeroVector;
    UPROPERTY(ReplicatedUsing=OnRep_WorkState) TWeakObjectPtr<ALumberMillTimberWagon> MountedWagon;

    UFUNCTION() void OnRep_WorkerRole();
    UFUNCTION() void OnRep_WorkState();

    UPROPERTY(Transient) TObjectPtr<UStaticMesh> AxeMeshAsset;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> SawMeshAsset;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> LogMeshAsset;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> SplitHalfLMeshAsset;
    UPROPERTY(Transient) TObjectPtr<UStaticMesh> SplitHalfRMeshAsset;
    UPROPERTY(Transient) TObjectPtr<UParticleSystem> WoodChipVfx;
    UPROPERTY(Transient) TObjectPtr<USoundBase> ChopSfx;

    // Stump upright billet (joined HalfL + HalfR) & pooled tumbling split halves on ground (visual, synced Host + Clients).
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> BilletHalfL;
    UPROPERTY(Transient) TObjectPtr<UStaticMeshComponent> BilletHalfR;
    struct FFallingSplitHalf
    {
        TObjectPtr<UStaticMeshComponent> Comp;
        FVector Pos = FVector::ZeroVector;
        FVector Vel = FVector::ZeroVector;
        FRotator Rot = FRotator::ZeroRotator;
        FVector AngVel = FVector::ZeroVector;
        double GroundZ = 0.0;
        float Age = 0.f;
        bool bActive = false;
        bool bGrounded = false;
    };
    static constexpr int32 MaxSplitHalves = 6;
    FFallingSplitHalf SplitPool[MaxSplitHalves];
    int32 NextSplitPair = 0;
    bool bBilletSplitThisCycle = false;

    // Runtime visual hide of static stump axe (Role 0 SplitLog) or static sawbuck saw (Role 1 SawLog) on LumberMill_Compound.
    TWeakObjectPtr<AActor> CachedCompoundActor;
    double NextCompoundLookupAt = -1.0;
    TWeakObjectPtr<UStaticMeshComponent> HiddenStumpAxe;
    TWeakObjectPtr<UInstancedStaticMeshComponent> HiddenSawHism;
    int32 HiddenSawInstanceIndex = INDEX_NONE;
    FTransform HiddenSawOriginalTransform = FTransform::Identity;

    // Smooth remote-client walking interpolation + tick ordering behind mounted wagon (0.0mm rein/seat lag).
    TWeakObjectPtr<ALumberMillTimberWagon> TickPrereqWagon;
    FVector ClientRepTargetLoc = FVector::ZeroVector;
    FRotator ClientRepTargetRot = FRotator::ZeroRotator;
    bool bHasClientRepTarget = false;

    bool bAppearanceApplied = false;
    uint8 AppliedRole = 255;
    float PrevActionPhase = 0.f;
    float ActionRateScale = 1.f;
    bool bWorkerRTVisible = true;
    double NextWorkerRTCheckAt = -1.;
    void UpdateRayTracingVisibility(bool bForce = false);

    void ApplyAppearanceAndAnims();
    void ApplyToolAndVisibility();
    void UpdateMountedSeatTransform();
    FVector ComputePalmGripCenter(FName HandBone, FName MiddleBone, FName IndexBone, FName PinkyBone, bool bIsRight) const;
    void UpdateDynamicToolTransform();
    void UpdateCompoundWorkPropOverride();
    void RestoreCompoundWorkPropOverride();
    void EnsureSplitLogComponents();
    void SpawnSplitLogHalves(const FVector& StumpTop, const FVector& CleaveRight, float BilletYawDeg);
    void TickSplitLogSimulation(float DeltaSeconds);
    void TickWorkImpactFeedback();
};
