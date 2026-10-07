#pragma once

#include "NurseZombie.h"
#include "Engine/NetSerialization.h"
#include "MantisM27Monster.generated.h"

class UFatZombieAnimInstance;
class UMaterialInstanceDynamic;
class AMonsterAIController;

UENUM()
enum class EM27PouncePhase : uint8 { None, Windup, Flight, Landing, Recovery };

/** Dual-scythe experiment. Shared AI/health/poise, authored blade contact. */
UCLASS(Blueprintable, Placeable)
class FPSGAME_API AMantisM27Monster : public ANurseZombie
{
    GENERATED_BODY()
public:
    AMantisM27Monster(const FObjectInitializer& Initializer = FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void Landed(const FHitResult& Hit) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Identity") FText MonsterDisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Animation") TObjectPtr<UAnimSequence> LeftSlashClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Animation") TObjectPtr<UAnimSequence> RightSlashClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Animation") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Animation", meta=(ClampMin="1")) float SourceMoveSpeed = 145.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Combat", meta=(ClampMin="1")) float BladeHitRadius = 35.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Stats") int32 PhysicalDefense = 20;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Stats") int32 MagicalDefense = 12;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Stats") int32 CriticalResistance = 14;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Stats") float CombatAttributeWeight = 7.f;
    UFUNCTION(BlueprintCallable, Category="M27|Authoring") static bool PreparePhysics(USkeletalMesh* InMesh);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Cloak") TObjectPtr<UMaterialInterface> CloakMaterial;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Cloak", meta=(ClampMin="0", ClampMax="1")) float CloakHealFractionPerSecond = .05f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Cloak", meta=(ClampMin="0", ClampMax="1")) float CloakInjuryThreshold = .5f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Cloak", meta=(ClampMin="0", ClampMax="0.99")) float CloakRecoveryThreshold = .8f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Cloak", meta=(ClampMin="0")) float CloakMinimumSeconds = 3.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Cloak", meta=(ClampMin="0.01")) float CloakFadeSeconds = .45f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Cloak", meta=(ClampMin="100")) float CloakOrbitRadius = 700.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Cloak", meta=(ClampMin="1")) float CloakMoveSpeed = 190.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, ReplicatedUsing=OnRep_Cloaked, Category="M27|Cloak") bool bCloaked = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="M27|Cloak") bool bEncounterCloakUsed = false;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Transient, Category="M27|Cloak") bool bInjuryCloakUsed = false;
    void NotifyCloakEncounter(APawn* Victim);
    void NavigateWhileCloaked(AMonsterAIController* AI, const FVector& TargetFeet);
    bool IsCloakRecoveryReady() const;
    float MeleeStartDistance(const APawn* Victim = nullptr) const;
    bool HasAttackSight(const APawn* Victim) const;
    bool IsMeleeRecoveryPose() const;
    bool CanMeleeFrom(const APawn* Victim, const FVector& From, float Range) const;
    bool CanStartMantisAttack(APawn* Victim) const;
    bool WantsPounce(APawn* Victim) const;
    bool StartPounce(APawn* Victim);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Pounce") TObjectPtr<UAnimSequence> PounceWindupClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Pounce") TObjectPtr<UAnimSequence> PounceFlightClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Pounce") TObjectPtr<UAnimSequence> PounceLandClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Pounce") float PounceMinRange = 280.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Pounce") float PounceMaxRange = 1125.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Pounce") float PounceFlightSeconds = .65f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Pounce") float PounceCooldownSeconds = 5.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Pounce") float PounceImpactRadius = 330.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Pounce") float PounceImpactAngle = 160.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Pounce") float PounceDamageScale = 1.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="M27|Cloak") float ShadowStrikeMultiplier = 2.f;
protected:
    virtual void StartStateAnimation(UAnimSequence* Clip, bool bLoop) override;
    virtual void SetAttackAnimationTime(float Seconds) override;
    virtual void ProcessAttackContact(float Previous, float Current) override;
    virtual void SetWalkAnimationRate(float Rate) override;
    virtual void StartHitPresentation(UAnimSequence* Clip, float Duration) override;
    virtual void SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining) override;
    virtual void StartDeathPresentation() override;
    virtual float ApplyMeleeDamage(APawn* Victim) override;
private:
    friend class UMantisM27AIReviewCommandlet;
    void AlignVisual();
    UFatZombieAnimInstance* PosePlayer();
    void PresentAttack();
    double ServerClock() const;
    void SampleBlade(float Time, FVector (&Points)[3]);
    void SweepBlade(const FVector (&From)[3], const FVector (&To)[3]);
    bool TryScytheHit(APawn* Victim);
    void SweepMeleeEnvelope();
    bool bContactConsumed = true;
    bool bMovingPresentation = false;
    FVector LockedFacing = FVector::ForwardVector;
    UPROPERTY(ReplicatedUsing=OnRep_AttackSequence) int32 AttackSequence = 0;
    UPROPERTY(Replicated) double AttackStartedAt = 0.;
    UFUNCTION() void OnRep_AttackSequence();
    void TickCloak(float DeltaSeconds);
    void SetCloaked(bool Enabled);
    void PrepareCloakVisuals();
    void RestoreCloakVisuals();
    UFUNCTION() void OnRep_Cloaked();
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> CloakInstance;
    UPROPERTY(Transient) TObjectPtr<USkeletalMeshComponent> CloakShadow;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInterface>> UncloakedMaterials;
    float CloakBlend = 0.f;
    float UncloakedMoveSpeed = 0.f;
    double CloakStartedAt = 0.;
    double NextCloakGoalAt = 0.;
    FVector CloakGoal = FVector::ZeroVector;
    float CloakOrbitDirection = 1.f;
    bool bCloakVisualsApplied = false;
    bool bUncloakedCastsShadow = true;
    // Latched for this cloak charge: damage after recovery cannot send an
    // already committed ambush back into endless regeneration/orbiting.
    bool bCloakAttackCommitted = false;
    void BeginShadowStrike();
    bool BuildPounceVelocity(APawn* Victim, FVector& Velocity) const;
    void TickPounce(float DeltaSeconds);
    void BeginPouncePhase(EM27PouncePhase Phase);
    void PresentPounce();
    void CancelPounce();
    void RestorePounceMovement();
    void PounceImpact(const FVector& LandingPoint);
    UFUNCTION() void OnRep_PouncePhase();
    UPROPERTY(Replicated) double PouncePhaseStartedAt = 0.;
    UPROPERTY(ReplicatedUsing=OnRep_PouncePhase) EM27PouncePhase PouncePhase = EM27PouncePhase::None;
    TWeakObjectPtr<APawn> PounceTarget;
    double NextPounceAt = 0., NextMantisAttackAt = 0.;
    mutable double NextPouncePlanAt = 0.;
    mutable TWeakObjectPtr<APawn> PlannedPounceTarget;
    mutable bool bPouncePlanReady = false;
    float ActiveAttackDamageScale = 1.f;
    float SavedPounceAirControl = 0.f;
    bool bSavedPounceOrient = true, bPounceMovementSaved = false;
    bool bPounceImpactConsumed = true;
public:
    // Append audio data: preserve the offsets of the established combat state.
    UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category="M27|Audio") TMap<FName,TObjectPtr<class USoundBase>> MantisSounds;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
    void InitializeMantisAudio();
    void UpdateMantisAudio();
    void StopMantisAudio();
    void PlayMantisVoice(class UAudioComponent* Voice, FName CueRole, float Volume = 1.f, float StartTime = 0.f);
    UFUNCTION(NetMulticast, Unreliable) void MulticastMantisAccent(FName CueRole, double StartedAt);
    UFUNCTION(NetMulticast, Unreliable) void MulticastMantisContact(FVector_NetQuantize Location, double StartedAt, bool Alternate);
    UPROPERTY(Transient) TObjectPtr<class UAudioComponent> MantisActionVoice;
    UPROPERTY(Transient) TObjectPtr<class UAudioComponent> MantisAccentVoice;
    UPROPERTY(Transient) TObjectPtr<class UAudioComponent> MantisAmbientVoice;
    UPROPERTY(Transient) TObjectPtr<class UAudioComponent> MantisContactVoice;
    ENurseState LastMantisAudioState = ENurseState::Idle;
    EM27PouncePhase LastMantisAudioPounce = EM27PouncePhase::None;
    double LastMantisAudioPhaseAt = -1.;
    double LastMantisHurtAudioAt = -1.;
    int32 LastMantisAudioAttack = 0;
    int32 MantisContactAudioIndex = 0;
    FName MantisAmbientRole;
};
