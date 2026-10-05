#pragma once

#include "CoreMinimal.h"
#include "WolfMonster.h"
#include "LurkerSurfaceRoute.h"
#include "Engine/NetSerialization.h"
#include "LurkerM08Monster.generated.h"

USTRUCT()
struct FLurkerM08RimInfluence
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) FName Bone;
    UPROPERTY(EditAnywhere) FVector BoneLocalPosition = FVector::ZeroVector;
    UPROPERTY(EditAnywhere) float Weight = 0.f;
};

USTRUCT()
struct FLurkerM08RimVertex
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere) TArray<FLurkerM08RimInfluence> Influences;
};

USTRUCT()
struct FLurkerAirCannonState
{
    GENERATED_BODY()
    UPROPERTY() bool bActive = false;
    UPROPERTY() double StartedAt = 0.;
    UPROPERTY() bool bAimLocked = false;
    UPROPERTY() FVector_NetQuantize10 AimPoint = FVector::ZeroVector;
};

/** M-08 surface ambusher: physical ground/wall/roof pursuit and swept leaps. */
UCLASS(Blueprintable)
class FPSGAME_API ALurkerM08Monster : public AWolfMonster
{
    GENERATED_BODY()
public:
    ALurkerM08Monster(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual FVector GetNavAgentLocation() const override;
    virtual bool Busy() const override;
    virtual bool CanBiteFrom(const APawn* Victim, const FVector& From, float Range) const override;
    void NavigateSurface(FVector Destination, bool bReturning, APawn* VisibleTarget);
    void StopSurfaceNavigation();
    FVector HomeSupportLocation() const { return InitialHomeSupport; }
    float LeapPitchCorrection(bool Traversal, float SourceSeconds) const;
    virtual bool CanAttack(APawn* Victim) const override;
    virtual bool StartAttack(APawn* Victim) override;
    FVector AirCannonOrigin() const;
    bool AirCannonFrame(FTransform& Frame) const;
    bool HasHuntingSight(const APawn* Victim) const;

    /** Author the M08-owned physics asset from its fitted anatomical bone segments. */
    UFUNCTION(BlueprintCallable, Category="M08|Authoring")
    static int32 AuthorLurkerPhysics(USkeletalMesh* AuthoredMesh);
protected:
    virtual bool HasAttackSupport() const override;
    virtual void FaceAttackDirection(const FVector& Direction, float TurnSeconds = -1.f) override;
    virtual bool BuildHuntingPounce(APawn* Victim, FVector& Landing) const override;
    virtual bool HuntingContact(const APawn* Victim, bool bPounce) const override;
    virtual FVector PouncePathPoint(const FVector& Start, const FVector& End, float Alpha) const override;
    virtual float PounceFlightDuration(const FVector& Start, const FVector& End) const override;
    virtual void FinishPounceMovement() override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M08|Traversal") float ClimbSpeed = 270.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M08|Traversal") float JumpRange = 700.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M08|Traversal") float JumpHeight = 500.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M08|Traversal") float SurfaceTurnSpeed = 240.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category="M08|Traversal") FVector SurfaceNormal = FVector::UpVector;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category="M08|Traversal") bool bSurfaceAttached = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Replicated, Category="M08|Traversal") bool bTraversalJump = false;
    UPROPERTY(Replicated) float TraversalClock = 0.f;
    UPROPERTY(Replicated) float TraversalFlightSeconds = .6f;
private:
    bool AttachNear(FVector Normal, float Reach = 120.f);
    void DetachSurface();
    void TickSurface(float DeltaSeconds);
    bool BeginTraversalJump();
    void TickTraversalJump(float DeltaSeconds);
    void UpdateJumpPose();
    void OrientToSurface(FVector Direction, FVector Normal, float DeltaSeconds);
    bool PlanHuntingPounce(APawn* Victim, FVector& Landing) const;
    float BodyRadius() const;
    bool bWantsSurfaceMove = false, bSurfaceReturning = false;
    FVector SurfaceGoal = FVector::ZeroVector, InitialHomeSupport = FVector::ZeroVector;
    TArray<FLurkerSurfacePoint> SurfacePath;
    TArray<FVector> RecentSupports;
    TWeakObjectPtr<APawn> SurfaceVictim;
    float RouteAge = 10.f, SupportAge = 0.f, StuckSeconds = 0.f, JumpCooldown = 0.f;
    FVector JumpStart = FVector::ZeroVector, JumpEnd = FVector::ZeroVector, JumpOutward = FVector::ZeroVector;
    FVector JumpLandingNormal = FVector::UpVector;
    float JumpArcHeight = 150.f;
    mutable float PlannedAttackArc = 100.f;
    mutable FVector PlannedAttackOutward = FVector::ZeroVector;
    mutable double AttackPlanTime = -10.;
    mutable FVector AttackPlanStart = FVector::ZeroVector, AttackPlanTargetPosition = FVector::ZeroVector, AttackPlanLanding = FVector::ZeroVector;
    mutable TWeakObjectPtr<APawn> AttackPlanTarget;
    mutable bool bAttackPlanValid = false;
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M08|Air Cannon") float AirCannonDamage = 48.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M08|Air Cannon", meta=(Units="s", ClampMin="0")) float AirCannonStunSeconds = 3.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M08|Air Cannon", meta=(Units="s", ClampMin="0")) float AirCannonCooldown = 20.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M08|Air Cannon", meta=(Units="cm")) float AirCannonMinRange = 280.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M08|Air Cannon", meta=(Units="cm")) float AirCannonRange = 1800.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M08|Air Cannon", meta=(Units="cm/s", ClampMin="1")) float AirCannonSpeed = 1600.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="M08|Air Cannon") TObjectPtr<class UStaticMesh> AirRingMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="M08|Air Cannon") TObjectPtr<class UMaterialInterface> AirRingMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="M08|Air Cannon") TObjectPtr<class USoundBase> AirChargeSound;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="M08|Air Cannon") TObjectPtr<class USoundBase> AirReleaseSound;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="M08|Air Cannon") TObjectPtr<class USoundAttenuation> AirSoundAttenuation;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="M08|Air Cannon") TObjectPtr<class UStaticMeshComponent> AirChargeRing;
    UPROPERTY(ReplicatedUsing=OnRep_AirCannon) FLurkerAirCannonState AirCannon;
private:
    bool CanAirCannon(APawn* Victim) const;
    void TickAirCannon(float Dt);
    void EndAirCannon();
    void UpdateAirCannonPose(float SourceTime);
    void UpdateAirCannonVisual(float SourceTime);
    FVector PredictAirCannonTarget(APawn* Victim, float ReleaseDelay) const;
    void FireAirCannon();
    UFUNCTION() void OnRep_AirCannon();
    UPROPERTY(Transient) TObjectPtr<class UAudioComponent> AirChargeAudio;
    TWeakObjectPtr<APawn> AirCannonTarget;
    double AirCannonReadyAt = 0.;
    bool bAirCannonFired = false;
public:
    /** Actual front bore boundary, in order, with the original mesh skin weights. */
    UPROPERTY(EditAnywhere, Category="M08|Air Cannon") TArray<FLurkerM08RimVertex> AirCannonRim;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M08|Traversal", meta=(ClampMin="0.1")) float PounceFlightSpeedMultiplier = 3.f;
private:
    void UpdateAirChargeAttachment();
    FDelegateHandle AirChargePoseHandle;
    float AirChargeFraction = 0.f;
public:
    /** Lower oral surface samples, with actual skin weights, for supported crouches. */
    UPROPERTY(EditAnywhere, Category="M08|Animation") TArray<FLurkerM08RimVertex> MouthSupportSamples;
    /** Distinct, readable wind-up cue fitted to the same skinned bore as the projectile. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="M08|Air Cannon") TObjectPtr<class UStaticMesh> AirChargeMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="M08|Air Cannon") TObjectPtr<class UMaterialInterface> AirChargeMaterial;
private:
    // Compare moving goals with the last committed plan, not the previous BT tick.
    FVector PlannedSurfaceGoal = FVector::ZeroVector;
    bool bHasSurfacePlan = false;
};
