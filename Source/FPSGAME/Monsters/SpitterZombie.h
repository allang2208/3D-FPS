#pragma once

#include "NurseZombie.h"
#include "SpitterZombie.generated.h"

class UFatZombieAnimInstance;
class UPhysicsAsset;

/** One complete melee animation and its contact window on the same combat clock. */
USTRUCT(BlueprintType)
struct FSpitterAttackVariant
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Attack") TObjectPtr<UAnimSequence> Clip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Attack", meta=(ClampMin="0")) float ContactTime = .47f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Attack", meta=(ClampMin="0")) float ContactEnd = .67f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Attack", meta=(ClampMin="0")) float RecoveryTime = .35f;
};

/** Green Meshy zombie with a lifetime locomotion choice and library melee attack. */
UCLASS(Blueprintable)
class FPSGAME_API ASpitterZombie : public ANurseZombie
{
    GENERATED_BODY()
public:
    ASpitterZombie(const FObjectInitializer& Initializer = FObjectInitializer::Get());
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Spitter|Animation") TObjectPtr<UAnimSequence> DeathClip;
    /** Draw once in BeginPlay; the selected clip stays with this actor for life. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Spitter|Animation") TArray<TObjectPtr<UAnimSequence>> MovementClips;
    /** Authored stride speeds in cm/s; the chosen entry also sets this actor's WalkSpeed at spawn. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Spitter|Animation") TArray<float> MovementReferenceSpeeds;
    UPROPERTY(Transient, VisibleAnywhere, BlueprintReadOnly, Category="Spitter|Runtime") int32 SelectedMovementIndex = INDEX_NONE;
    UFUNCTION(BlueprintCallable, Category="Spitter|Authoring") static bool PreparePhysics(USkeletalMesh* InMesh);
protected:
    virtual void StartStateAnimation(UAnimSequence* Clip, bool bLoop) override;
    virtual void SetAttackAnimationTime(float Seconds) override;
    virtual void SetWalkAnimationRate(float Rate) override;
    virtual void StartHitPresentation(UAnimSequence* Clip, float Duration) override;
    virtual void SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining) override;
    virtual void StartDeathPresentation() override;
    virtual float ApplyMeleeDamage(APawn* Victim) override;
private:
    UFatZombieAnimInstance* PosePlayer();
    void AlignVisual();
    void StartRagdoll();
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> SelectedMovementClip;
    float MovementReferenceSpeed = 130.f;
    FTimerHandle RagdollTimer;

public:
    /** Choose on attack entry; keep that clip and its timing until interrupted or finished. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Spitter|Animation") TArray<FSpitterAttackVariant> AttackVariants;
    UPROPERTY(Transient, VisibleAnywhere, BlueprintReadOnly, Category="Spitter|Runtime") int32 SelectedAttackIndex = INDEX_NONE;
private:
    void SelectAttackVariant();
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> PreviousAttackClip;
    FVector DeathTravelVelocity = FVector::ZeroVector;
    FVector DeathHitDirection = FVector::ZeroVector;
    FVector DeathHitLocation = FVector::ZeroVector;
};
