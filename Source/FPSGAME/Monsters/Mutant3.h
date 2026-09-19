#pragma once
#include "NurseZombie.h"
#include "Mutant3.generated.h"

/** Forsaken Brute: original Meshy locomotion and adapted zombie combat poses. */
UCLASS(Blueprintable)
class FPSGAME_API AMutant3 : public ANurseZombie
{
    GENERATED_BODY()
public:
    AMutant3(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    virtual void BeginPlay() override;
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation") TObjectPtr<UAnimSequence> RunningClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation") TObjectPtr<UAnimSequence> FastRunClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation", meta=(ClampMin="1", Units="cm/s")) float AnimationWalkSpeed = 115.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation", meta=(ClampMin="1", Units="cm/s")) float AnimationRunSpeed = 240.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation", meta=(ClampMin="1", Units="cm/s")) float AnimationFastRunSpeed = 360.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Animation", meta=(ClampMin="0", ClampMax="0.5", Units="s")) float AnimationBlendSeconds = .16f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Mutant3|Death") bool bDeathRagdoll = true;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Mutant3|Death") bool bRagdollActive = false;
    UFUNCTION(BlueprintCallable, Category="Mutant3|Authoring") static bool PrepareCombatPhysics(USkeletalMesh* InMesh);
protected:
    virtual void StartDeathPresentation() override;
    virtual void StartHitPresentation(UAnimSequence* Clip, float Duration) override;
    virtual void SetHitPresentationTime(UAnimSequence* Clip, float Elapsed, float Remaining) override;
    virtual void StartStateAnimation(UAnimSequence* Clip, bool bLoop) override;
    virtual void SetAttackAnimationTime(float Seconds) override;
    virtual void SetWalkAnimationRate(float Rate) override;
private:
    class UFatZombieAnimInstance* GetBlendedAnimation();
    void AlignVisual();
    void StartDeathRagdoll();
    FVector IncomingHitDirection = FVector::ZeroVector;
    FTimerHandle DeathRagdollTimer;
};
