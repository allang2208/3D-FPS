#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Character.h"
#include "WolfMonster.generated.h"

class UQuadrupedAnimationSet;
class UQuadrupedTemplateAnimInstance;
class UMonsterCombatComponent;
class USkeletalMesh;

UENUM(BlueprintType)
enum class EWolfState : uint8 { Idle, Howl, Chase, Returning, Bite, Pounce, Stagger, Recovery, Dying, Ragdoll };

/** Ground predator. The shared behavior tree chooses actions; this owns their execution. */
UCLASS(Blueprintable)
class FPSGAME_API AWolfMonster : public ACharacter
{
    GENERATED_BODY()
public:
    AWolfMonster(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Wolf") TObjectPtr<UMonsterCombatComponent> Combat;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Wolf|Animation") TObjectPtr<UQuadrupedAnimationSet> AnimationSet;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Stats") float MaxHealth = 220.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Stats") float PhysicalDefense = 12.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Stats") float MagicDefense = 8.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Stats") float CriticalResistance = 5.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Stats") int32 ExperienceReward = 180;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Movement", meta=(Units="cm/s")) float WalkSpeed = 100.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Movement", meta=(Units="cm/s")) float ChaseSpeed = 380.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|AI", meta=(Units="cm")) float AggroRadius = 1500.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|AI", meta=(Units="cm")) float LeashRadius = 2200.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|AI") bool bHowlOnEncounter = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|AI", meta=(Units="cm")) float PackAlertRadius = 1100.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|AI", meta=(Units="s")) float PackAlertTime = 1.2f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Bite") float BiteDamage = 22.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Bite", meta=(Units="cm")) float BiteTriggerRange = 155.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Bite", meta=(Units="cm")) float ContactRadius = 30.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Bite", meta=(Units="s")) float BiteWindup = .12f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Bite", meta=(Units="s")) float BiteCooldown = 1.25f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Bite", meta=(Units="s")) float BiteRecovery = .3f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Pounce") float PounceDamage = 36.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Pounce", meta=(Units="cm")) float PounceMinRange = 260.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Pounce", meta=(Units="cm")) float PounceMaxRange = 600.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Pounce", meta=(Units="s")) float PounceWindup = .3f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Pounce", meta=(Units="s")) float PounceCooldown = 4.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Pounce", meta=(Units="s")) float PounceRecovery = .6f;
    /** Source-animation seconds: translation happens during the existing jump. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Pounce", meta=(Units="s")) float PounceTravelStart = .1f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Pounce", meta=(Units="s")) float PounceTravelEnd = .5f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Pounce", meta=(Units="cm")) float PounceArcHeight = 25.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Death", meta=(Units="s")) float CorpseSeconds = 15.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Death", meta=(ClampMin="0", ClampMax="1")) float DeathAnimationFraction = .6f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Wolf|Death") bool bUseRagdoll = true;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Wolf") float Health = 220.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Wolf") EWolfState State = EWolfState::Idle;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Wolf") float StateSeconds = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Wolf") FVector Home;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Wolf") int32 SuccessfulHits = 0;

    bool Dead() const { return State == EWolfState::Dying || State == EWolfState::Ragdoll; }
    bool Busy() const;
    bool CanAttack(APawn* Victim) const;
    bool StartAttack(APawn* Victim);
    void SetTarget(APawn* Victim) { Target = Victim; }
    void SetLocomotion(bool bMoving, bool bReturning);
    void ReachedHome();
    UFUNCTION(BlueprintCallable, Category="Wolf|Combat") void InterruptAttack(float Seconds = .45f);
    void StartHitPresentation();
    void SetHitPresentationTime(float Elapsed, float Remaining);
    void FinishHitReaction();
    /** Author only the gameplay copy's bone hit queries, retaining its existing body shapes. */
    UFUNCTION(BlueprintCallable, Category="Wolf|Authoring") static bool PrepareCombatPhysics(USkeletalMesh* InMesh);
private:
    void AlignVisual();
    UQuadrupedTemplateAnimInstance* Animation() const;
    void EnterState(EWolfState NewState);
    bool CanSee(const AActor* Actor) const;
    FVector Mouth() const;
    void SampleAction(FName Action, float SourceSeconds);
    void AdvanceAttack(float PreviousSeconds);
    void AdvancePounce(float SourceSeconds);
    void FinishPounceMovement();
    void TryContact(float SourceSeconds);
    void AlertPack();
    void Die(AController* Killer);
    void EnterRagdoll();
    float ClipLength(FName Action) const;

    TWeakObjectPtr<APawn> Target;
    FVector IncomingHitDirection = FVector::ZeroVector;
    FVector AttackDirection = FVector::ForwardVector;
    FVector PounceOrigin = FVector::ZeroVector;
    float PounceDistance = 0.f;
    float LastPounceSourceTime = 0.f;
    float BiteCooldownLeft = 0.f;
    float PounceCooldownLeft = 0.f;
    float ReactionSeconds = 0.f;
    float RecoverySeconds = 0.f;
    FName ReactionAction;
    bool bAttackConsumed = false;
    bool bAttackAnimationStarted = false;
    bool bPounceMovement = false;
    bool bPounceBlocked = false;
    bool bHasAlerted = false;
    bool bPackAlertSent = false;
    bool bCorpseSleeping = false;
};
