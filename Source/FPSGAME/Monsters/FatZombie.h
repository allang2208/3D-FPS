#pragma once
#include "NurseZombie.h"
#include "FatZombiePusPool.h"
#include "FatZombie.generated.h"

/** Meshy fat zombie, using the shared melee/BT execution and its own four clips. */
UCLASS(Blueprintable)
class FPSGAME_API AFatZombie : public ANurseZombie
{
    GENERATED_BODY()
public:
    AFatZombie(const FObjectInitializer& ObjectInitializer = FObjectInitializer::Get());
    virtual void BeginPlay() override;
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual float TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="FatZombie|Pus") bool bLeaveDeathPus = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="FatZombie|Pus") FFatZombiePusSettings DeathPus;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="FatZombie|Animation") TObjectPtr<UAnimSequence> DeathClip;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="FatZombie|Animation", meta=(ClampMin="1", Units="cm/s")) float AnimationWalkSpeed = 80.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="FatZombie|Animation", meta=(ClampMin="0", ClampMax="0.5", Units="s")) float AnimationBlendSeconds = .2f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="FatZombie|Death") bool bDeathRagdoll = true;
    // Death clips hand off at 60%; retain the serialized delay for the no-clip fallback.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="FatZombie|Death", meta=(ClampMin="0", Units="s", ToolTip="Fallback delay without a death clip. Death clips hand off to physics at 60%.")) float RagdollDelay = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="FatZombie|Death", meta=(ClampMin="0", ClampMax="300", Units="cm/s")) float RagdollImpulseSpeed = 90.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="FatZombie|Death") bool bRagdollActive = false;
    // Editor authoring entry: report stored query/body settings before changing them.
    UFUNCTION(BlueprintCallable, Category="FatZombie|Authoring") static bool PrepareCombatPhysics(USkeletalMesh* InMesh, bool bApply = true);
    // Author only the dedicated duplicate of the accepted idle animation.
    UFUNCTION(BlueprintCallable, Category="FatZombie|Authoring") static bool AuthorStaggerAnimation(UAnimSequence* Clip);
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
    FVector IncomingHitDirection = FVector::ZeroVector;
    void SpawnDeathPus();
    void StartDeathRagdoll();
    FTimerHandle DeathRagdollTimer;
    FTransform DeathPusAnchor;
};
