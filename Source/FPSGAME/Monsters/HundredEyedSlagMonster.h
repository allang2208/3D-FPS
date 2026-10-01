#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "MonsterCoreStats.h"
#include "HundredEyedSlagMonster.generated.h"

class UAnimSequence;
class USkeletalMesh;
class UMonsterCombatComponent;
class UCombatStatusFormula;
class UFatZombieAnimInstance;
class UPhysicsAsset;
class UStaticMeshComponent;
class UNiagaraComponent;
class UMaterialInstanceDynamic;
class ASlagBlackMist;

UENUM(BlueprintType)
enum class ESlagState : uint8
{
    Idle, Chase, Returning, Sweep, Slam, AshBurst, Charge, Stagger, Recovery, Dying, Corpse,
    ChargeRush, ChargeImpact, ChargeRecover,
    EyeLaserWindup, EyeLaserFire, EyeLaserRecover,
    JumpWindup, JumpAir, JumpImpact, JumpRecover
};

/** Four-limbed incinerator elite. The shared BT decides; this character owns attack time. */
UCLASS(Blueprintable)
class FPSGAME_API AHundredEyedSlagMonster : public ACharacter
{
    GENERATED_BODY()
public:
    AHundredEyedSlagMonster(const FObjectInitializer& Initializer = FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void MoveBlockedBy(const FHitResult& Impact) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event,
        AController* Instigator, AActor* Causer) override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Slag") TObjectPtr<UMonsterCombatComponent> Combat;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Slag") TObjectPtr<UCombatStatusFormula> Status;
    UPROPERTY(EditDefaultsOnly, Category="Slag|Assets") TObjectPtr<USkeletalMesh> VisualMesh;
    UPROPERTY(EditDefaultsOnly, Category="Slag|Assets") TMap<FName, TObjectPtr<UAnimSequence>> Clips;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Stats") float MaxHealth = 1800.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Stats") float PhysicalAttack = 42.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Stats") float MagicAttack = 35.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Stats") int32 Level = 8;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Stats") EMonsterRank Rank = EMonsterRank::Elite;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Stats") int32 ExperienceReward = 300;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|AI") float AggroRadius = 1500.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|AI") float LeashRadius = 2400.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|AI") float ChaseSpeed = 340.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|AI") float ReturnSpeed = 120.f;
    /** Engagement distance. Sweep closes to 250 cm; slam closes to 215 cm. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Attack") float MeleeRange = 340.f;
    UPROPERTY(EditAnywhere, Category="Slag|Attack", meta=(ClampMin="0")) float SweepDamageMultiplier = 1.25f;
    UPROPERTY(EditAnywhere, Category="Slag|Attack", meta=(ClampMin="0", Units="s")) float SlamStunSeconds = 2.f;
    UPROPERTY(EditAnywhere, Category="Slag|Mist") bool bEnableBlackMist = true;
    UPROPERTY(EditAnywhere, Category="Slag|Mist", meta=(ClampMin="50", Units="cm")) float BlackMistRadius = 260.f;
    /** Fallback body origin relative to the monster's feet, in centimetres. */
    UPROPERTY(EditAnywhere, Category="Slag|Mist") FVector BlackMistOffset = FVector(0, 0, 95);
    UPROPERTY(EditAnywhere, Category="Slag|Mist", meta=(ClampMin="0.1", Units="s")) float BlackMistBlindSeconds = 2.f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float AshRadius = 450.f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeRange = 600.f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeSpeed = 1000.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Death") float CorpseSeconds = 15.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Death", meta=(ClampMin="0.1", ClampMax="1.0")) float RagdollHandoffSeconds = .42f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Slag|Runtime") float Health = 1800.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Slag|Runtime") ESlagState State = ESlagState::Idle;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Slag|Runtime") float StateSeconds = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Slag|Runtime") FVector Home = FVector::ZeroVector;

    bool Dead() const { return State == ESlagState::Dying || State == ESlagState::Corpse; }
    bool Controlled() const { return State == ESlagState::Stagger; }
    bool Busy() const;
    bool CanAttack(APawn* Victim) const;
    UFUNCTION(BlueprintCallable, Category="Slag") bool StartAttack(APawn* Victim);
    void SetTarget(APawn* Victim) { Target = Victim; }
    void SetLocomotion(bool Moving, bool Returning);
    void InterruptAttack(float Seconds);
    void StartHitPresentation();
    void SetHitPresentationTime(float Elapsed, float Remaining);
    void FinishHitReaction();
    /** Offline asset authoring; the caller saves the returned package and mesh. */
    UFUNCTION(BlueprintCallable, Category="Slag|Authoring") static UPhysicsAsset* BuildFittedPhysicsAsset(USkeletalMesh* InMesh);

private:
    UFatZombieAnimInstance* Animation() const;
    UAnimSequence* Clip(FName Name) const;
    void AlignVisual();
    void EnterState(ESlagState Next);
    void PlayClip(FName Name, bool Loop = false);
    void SampleClip(FName Name, float Seconds, bool Loop = false);
    bool CanSee(const APawn* Victim) const;
    void Strike(float PreviousTime, float CurrentTime);
    void SweepVictims(FVector From, FVector To, float Radius, bool Magic);
    void DamageVictim(APawn* Victim, bool Magic);
    void EnterCorpse();
    TWeakObjectPtr<APawn> Target;
    TSet<TWeakObjectPtr<APawn>> HitVictims;
    FName CurrentClip = NAME_None;
    FName ReactionClip = TEXT("Stagger");
    FVector LockedDirection = FVector::ForwardVector;
    FVector PreviousPalm = FVector::ZeroVector;
    FVector DamageDirection = FVector::ZeroVector;
    FVector DeathVelocity = FVector::ZeroVector;
    TMap<FName, FVector> DeathBoneVelocities;
    TMap<FName, FVector> DeathBoneAngularVelocities;
    float AttackCooldown = 0.f;
    float AshCooldown = 0.f;
    float ChargeCooldown = 0.f;
    float ReactionSeconds = 0.f;
    bool bAshReleased = false;
    bool bChargeBlocked = false;
    bool bStunPresentation = false;
    bool bRewarded = false;
    bool bCorpseSleeping = false;
    UPROPERTY(Transient) TObjectPtr<ASlagBlackMist> BackMist;
    int32 MeleeCounter = 0;

    FVector ChargeStart = FVector::ZeroVector;
    FVector ChargePrevious = FVector::ZeroVector;
    FVector ChargePreviousPalm = FVector::ZeroVector;
    uint16 ChargeMotionID = 0;
    float ChargeBlockedSeconds = 0.f;
    float ChargeTrailSeconds = 0.f;
    float ChargePoseSeconds = 0.f;
    bool bChargeConsumed = false;
public:
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeWindupSeconds = .7f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeRushMaxSeconds = .85f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeDistance = 850.f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeLeadStrength = 1.f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeMaxLeadDistance = 260.f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeImpactSeconds = .35f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeRecoverSeconds = .65f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeDamageMultiplier = 1.6f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeStunSeconds = .45f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeKnockbackDistance = 110.f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Replaced by EyeLaser; retired attack")) float ChargeHitRadius = 60.f;
    UPROPERTY(EditAnywhere, Category="Slag|EyeLaser", meta=(ClampMin="100", Units="cm")) float LaserRange = 1200.f;
    UPROPERTY(EditAnywhere, Category="Slag|EyeLaser", meta=(ClampMin="1.5")) float LaserWindupSeconds = 1.5f;
    UPROPERTY(EditAnywhere, Category="Slag|EyeLaser", meta=(ClampMin="0.1")) float LaserFireSeconds = .65f;
    UPROPERTY(EditAnywhere, Category="Slag|EyeLaser", meta=(ClampMin="0.1")) float LaserRecoverSeconds = .5f;
    UPROPERTY(EditAnywhere, Category="Slag|EyeLaser", meta=(ClampMin="1")) float LaserCooldownSeconds = 6.f;
    /** Per-pulse raw magic damage: MagicAttack * multiplier (default 28). */
    UPROPERTY(EditAnywhere, Category="Slag|EyeLaser", meta=(ClampMin="0")) float LaserDamageMultiplier = .8f;
    /** First pulse at release; subsequent pulses are strictly before fire expiry. */
    UPROPERTY(EditAnywhere, Category="Slag|EyeLaser", meta=(ClampMin="0.05", Units="s")) float LaserDamageIntervalSeconds = .13f;
    UPROPERTY(EditAnywhere, Category="Slag|EyeLaser", meta=(ClampMin="1", Units="cm")) float LaserHitRadius = 12.f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Jump attack retired; only Sweep, Slam and EyeLaser are active")) float JumpTriggerRange = 450.f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Jump attack retired; only Sweep, Slam and EyeLaser are active")) float JumpWindupSeconds = .85f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Jump attack retired; only Sweep, Slam and EyeLaser are active")) float JumpHeight = 230.f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Jump attack retired; only Sweep, Slam and EyeLaser are active")) float JumpImpactRadius = 350.f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Jump attack retired; only Sweep, Slam and EyeLaser are active")) float JumpDamageMultiplier = 1.8f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Jump attack retired; only Sweep, Slam and EyeLaser are active")) float JumpImpactSeconds = .5f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Jump attack retired; only Sweep, Slam and EyeLaser are active")) float JumpRecoverSeconds = .75f;
    UPROPERTY(meta=(DeprecatedProperty, DeprecationMessage="Jump attack retired; only Sweep, Slam and EyeLaser are active")) float JumpCooldownSeconds = 7.f;
private:
    bool SpecialAttacking() const;
    void TickSpecialAttack(float DeltaSeconds);
    void UpdateLaserFX(float Energy, bool Firing);
    void ClearLaserFX();
    void ReleaseEyeLaser(bool DamagePulse);
    FVector LaserFocus() const;
    FVector LaserEye(int32 Index) const;
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> EyeLaserRenderers;
    UPROPERTY(Transient) TArray<TObjectPtr<UMaterialInstanceDynamic>> EyeLaserMaterials;
    FVector LaserDirection = FVector::ForwardVector;
    FVector LaserEnd = FVector::ZeroVector;
    float LaserCooldown = 0.f;
    float LaserNextDamageSeconds = 0.f;
    bool bLaserAimLocked = false;
    FVector EyeBindOffsets[2] = {FVector::ZeroVector,FVector::ZeroVector};
public:
    /** Model-space cm: existing front eye clusters, bound to the front plate. */
    UPROPERTY(EditDefaultsOnly, Category="Slag|EyeLaser") FVector LaserPrimaryEyePosition = FVector(34,6,86);
    UPROPERTY(EditDefaultsOnly, Category="Slag|EyeLaser") FVector LaserSecondaryEyePosition = FVector(38,-14,65);
private:
    /** Two reusable eye-local charge systems, active only during the windup. */
    UPROPERTY() TArray<TObjectPtr<UNiagaraComponent>> EyeChargeSystems;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> EyeCoreMaterial;
    UPROPERTY(Transient) TObjectPtr<UMaterialInstanceDynamic> EyeVortexMaterial;
public:
    /** Forward reach from actor origin, excluding the victim's collision radius. */
    UPROPERTY(EditAnywhere, Category="Slag|Attack", meta=(ClampMin="100", Units="cm")) float SweepReach = 320.f;
    UPROPERTY(EditAnywhere, Category="Slag|Attack", meta=(ClampMin="100", Units="cm")) float SlamReach = 300.f;
    UPROPERTY(EditAnywhere, Category="Slag|Attack", meta=(ClampMin="1", Units="cm")) float SweepHitRadius = 90.f;
    UPROPERTY(EditAnywhere, Category="Slag|Attack", meta=(ClampMin="1", Units="cm")) float SlamHitRadius = 95.f;
};
