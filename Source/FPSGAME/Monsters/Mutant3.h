#pragma once
#include "NurseZombie.h"
#include "Mutant3.generated.h"

UENUM(BlueprintType)
enum class EMutant3FeralPhase : uint8 { None, Claw, Windup, Flight, Landing, Recovery };

/** Original Meshy body with Khaimera-derived feral locomotion and combat. */
UCLASS(Blueprintable)
class FPSGAME_API AMutant3 : public ANurseZombie
{
    GENERATED_BODY()
public:
    AMutant3(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void Landed(const FHitResult& Hit) override;
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation") TObjectPtr<UAnimSequence> RunningClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation") TObjectPtr<UAnimSequence> FastRunClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation", meta=(ClampMin="1", Units="cm/s")) float AnimationWalkSpeed = 343.7f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation", meta=(ClampMin="1", Units="cm/s")) float AnimationRunSpeed = 343.7f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation", meta=(ClampMin="1", Units="cm/s")) float AnimationFastRunSpeed = 642.4f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation", meta=(ClampMin="0", ClampMax="0.5", Units="s")) float AnimationBlendSeconds = .18f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Death") bool bDeathRagdoll = true;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Mutant3|Death") bool bRagdollActive = false;
    UFUNCTION(BlueprintCallable, Category="Mutant3|Authoring") static bool PrepareCombatPhysics(USkeletalMesh* InMesh);
    UFUNCTION(BlueprintCallable, Category="Mutant3|Authoring") static bool RepairSurfaceBinding(USkeletalMesh* InMesh);
    UFUNCTION(BlueprintCallable, Category="Mutant3|Authoring") static bool ApplyPounceHandTracks(UAnimSequence* Target, UAnimSequence* Authored);
    bool CanStartFeralAttack(APawn* Victim) const;
    bool StartFeralAttack(APawn* Victim);
    float GetClawStartDistance() const;
    /** Shared by pursuit, attack selection and contact; From is capsule-center height. */
    bool CanClawFrom(const APawn* Victim, const FVector& From, float Range) const;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation") TArray<TObjectPtr<UAnimSequence>> ClawClips;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation") TObjectPtr<UAnimSequence> PounceWindupClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation") TObjectPtr<UAnimSequence> PounceFlightClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation") TObjectPtr<UAnimSequence> PounceLandClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin="1", ClampMax="3")) int32 ClawComboCount = 2;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin="0")) float ClawDamageScale = .8f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin="0")) float ClawRecoverySeconds = .4f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin="0", Units="cm")) float PounceMinRange = 320.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin="1", Units="cm")) float PounceMaxRange = 1125.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin=".2", Units="s")) float PounceFlightSeconds = .65f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin="0", Units="s")) float PounceCooldownSeconds = 5.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin="0")) float PounceDamageScale = 3.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin="0", Units="s")) float PounceStunSeconds = 2.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin="1", Units="cm")) float PounceImpactRadius = 250.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin="1", ClampMax="180", Units="deg")) float PounceImpactAngle = 120.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Mutant3|Feral") EMutant3FeralPhase FeralPhase = EMutant3FeralPhase::None;
protected:
    virtual void StartDeathPresentation() override;
    virtual void StartHitPresentation(UAnimSequence* Clip, float Duration) override;
    virtual void SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining) override;
    virtual void StartStateAnimation(UAnimSequence* Clip, bool bLoop) override;
    virtual void SetAttackAnimationTime(float Seconds) override;
    virtual void SetWalkAnimationRate(float Rate) override;
private:
    class UFatZombieAnimInstance* GetBlendedAnimation();
    void TransitionFeralLocomotion(UAnimSequence* Clip, float PlayRate, float BlendSeconds);
    void AlignVisual();
    void ConfigureFeralNavigation();
    UFUNCTION() void UpdateFeralFloorOffset(float DeltaSeconds, FVector OldLocation, FVector OldVelocity);
    FVector AppliedFeralFloorOffset = FVector::ZeroVector;
    void StartDeathRagdoll();
    void BeginFeralPhase(EMutant3FeralPhase Phase, UAnimSequence* Clip, float BlendSeconds);
    void BeginClaw();
    void BeginFeralRecovery(float Seconds);
    void FinishFeralAction();
    void CancelFeralAction();
    void RestoreFeralMovement();
    void TryClawContact();
    void TryPounceImpact(const FVector& LandingPoint);
    bool HasFeralSight(const APawn* Victim) const;
    bool HasFeralSightFrom(const APawn* Victim, const FVector& From) const;
    bool BuildPounceVelocity(APawn* Victim, FVector& Velocity) const;
    TWeakObjectPtr<APawn> FeralTarget;
    float FeralTime = 0.f;
    float FeralRecoveryDuration = 0.f;
    double NextFeralAttackAt = 0;
    double NextPounceAt = 0;
    int32 ClawsPerformed = 0;
    int32 NextClawIndex = 0;
    bool bFeralHitConsumed = false;
    bool bFeralMovementSaved = false;
    bool bSavedOrientToMovement = false;
    float SavedAirControl = 0.f;
    FVector IncomingHitDirection = FVector::ZeroVector;
    FTimerHandle DeathRagdollTimer;
    void InitializeSurfaceStreaming();
    void RequestNearbySurfaceMips();
    FTimerHandle SurfaceStreamingTimer;
    TArray<TWeakObjectPtr<class UTexture2D>> SurfaceStreamingTextures;
public:
    /** Horizontal velocity prediction over the actual flight time, sampled again at takeoff. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin="0", ClampMax="1.5")) float PounceLeadStrength = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Feral", meta=(ClampMin="0", Units="cm")) float PounceMaxLeadDistance = 450.f;
};
