#pragma once
#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Animation/PoseSnapshot.h"
#include "MonsterObstacleCollision.h"
#include "MonsterRagdollPhysics.h"
#include "HumanoidKnockdownComponent.generated.h"
class ANurseZombie;
class APawn;
class UAnimSequence;
class USkeletalMeshComponent;
class UFatZombieAnimInstance;

UENUM(BlueprintType)
enum class EHumanoidKnockdownPhase : uint8 { None, Physics, AnimatedFall, Downed, GettingUp, FrozenCorpse };

/** Reversible control for the existing humanoid family, plus bounded corpse physics. */
UCLASS(ClassGroup=AI, meta=(BlueprintSpawnableComponent))
class FPSGAME_API UHumanoidKnockdownComponent : public UActorComponent
{
    GENERATED_BODY()
public:
    UHumanoidKnockdownComponent();
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void TickComponent(float Dt, ELevelTick Type, FActorComponentTickFunction* Tick) override;
    UFUNCTION(BlueprintCallable, Category="Monster|Knockdown")
    bool Launch(APawn* InstigatorPawn, FVector Velocity, float DownSeconds = .7f, bool bForced = false);
    void ExtendControl(float Seconds);
    bool OnDeath();
    void StartDeath(UAnimSequence* DeathClip = nullptr, float ClipTime = 0.f);
    bool IsControlling() const;
    bool IsCorpse() const { return bCorpse; }
    bool IsFrozen() const { return Phase == EHumanoidKnockdownPhase::FrozenCorpse; }
    bool GetRecoverySupport(FVector& Point, FVector& Normal) const;
    bool CanReleaseCorpseBudget() const;
    void FreezeForBudget();
    int32 SimulatedBodyCount() const { return PhysicsBodyCount; }

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Knockdown") bool bEnabled = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Knockdown", meta=(ClampMin="0.1",ClampMax="1")) float LaunchScale = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Knockdown", meta=(ClampMin=".1",Units="s")) float GroundHoldSeconds = .7f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Knockdown", meta=(ClampMin=".1",Units="s")) float RecoveryBlendSeconds = .3f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Knockdown", meta=(ClampMin=".5",Units="s")) float CorpseSettleDeadline = 4.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Knockdown") TObjectPtr<UAnimSequence> FallClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Knockdown") TObjectPtr<UAnimSequence> GetUpClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Knockdown") TObjectPtr<UAnimSequence> ProneGetUpClip;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Knockdown") EHumanoidKnockdownPhase Phase = EHumanoidKnockdownPhase::None;
private:
    ANurseZombie* Humanoid() const;
    USkeletalMeshComponent* BodyMesh() const;
    UFatZombieAnimInstance* PosePlayer();
    void RememberStandingState();
    bool AcquirePhysicsBudget();
    bool StartPhysics(const FVector& Velocity);
    void TunePhysics();
    void StopPhysicsWithPose();
    void StartAnimatedFall(UAnimSequence* Clip, float StartTime);
    void FreezeCorpse();
    bool TryGetUp();
    void FinishGetUp();
    bool FindGround(FHitResult& Ground) const;
    FTransform ClipBone(UAnimSequence* Clip, FName Bone, float Time) const;
    void RestoreCollision();
    const TArray<FMonsterObstaclePose>& ClipObstaclePoses(UAnimSequence* Clip);
    bool PrepareAnimatedCapsule();
    void ApplyAnimatedCapsule();
    void RestoreAnimatedCapsule();
    bool RecoveryPathFits(UAnimSequence* Clip, const FTransform& ActorTransform, float FloorZ);
    bool FindRecoverySpace(UAnimSequence* Clip, FHitResult& Floor, FRotator& Facing, FVector& Candidate);
    UPROPERTY(Transient) FPoseSnapshot FrozenPose;
    UPROPERTY(Transient) TObjectPtr<UClass> StandingAnimClass;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> PlayingClip;
    FTransform StandingMeshRelative;
    FCollisionResponseContainer StandingResponses;
    TArray<FMonsterObstacleProbe> ObstacleProbes;
    TMap<TWeakObjectPtr<UAnimSequence>, TArray<FMonsterObstaclePose>> ClipObstacleCache;
    ECollisionEnabled::Type StandingMeshCollision = ECollisionEnabled::QueryOnly;
    ECollisionChannel StandingObjectType = ECC_Pawn;
    ECollisionEnabled::Type StandingCapsuleCollision = ECollisionEnabled::QueryAndPhysics;
    FName PelvisBone, HeadBone;
    FVector PelvisLocalFront = FVector::ForwardVector;
    FVector RecoveryFloorPoint = FVector::ZeroVector, RecoveryFloorNormal = FVector::UpVector;
    int32 StandingLOD = 0;
    int32 PhysicsBodyCount = 0;
    bool bSavedStanding = false, bCorpse = false, bGrounded = false, bBudgetOwned = false;
    bool bStandingUpdateJointsFromAnimation = false;
    float PhaseAge = 0.f, ProbeAge = 0.f, StableAge = 0.f, ClipStartTime = 0.f, FallStopTime = 0.f;
    float GetUpBlend = .3f, GetUpRate = 1.f;
    float FinishBlendAge = -1.f;
    double ControlUntil = 0;
    double NextRecoveryProbe = 0;
    int32 RecoveryFacingIndex = 0;
    float StandingRadius = 0, StandingHalfHeight = 0, AnimatedRadius = 0, AddedHalfHeight = 0;
    float StandingAirControl = 0;
    bool bAnimatedCapsule = false, bStandingNavUpdate = true, bStandingOrientToMovement = false;
    ECollisionResponse StandingPawnResponse = ECR_Block;
    FMonsterRagdollHandoff PhysicsHandoff;
    bool bGroundCorpseFeet = false;
};
