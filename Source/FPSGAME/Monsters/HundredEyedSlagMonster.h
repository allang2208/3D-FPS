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

UENUM(BlueprintType)
enum class ESlagState : uint8
{
    Idle, Chase, Returning, Sweep, Slam, AshBurst, Charge, Stagger, Recovery, Dying, Corpse
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
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|AI") float ChaseSpeed = 91.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Attack") float MeleeRange = 210.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Attack") float AshRadius = 300.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Attack") float ChargeRange = 400.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Attack") float ChargeSpeed = 210.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Slag|Death") float CorpseSeconds = 15.f;
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
    float AttackCooldown = 0.f;
    float AshCooldown = 0.f;
    float ChargeCooldown = 0.f;
    float ReactionSeconds = 0.f;
    bool bAshReleased = false;
    bool bChargeBlocked = false;
    bool bStunPresentation = false;
    bool bRewarded = false;
    bool bCorpseSleeping = false;
    int32 MeleeCounter = 0;
};
