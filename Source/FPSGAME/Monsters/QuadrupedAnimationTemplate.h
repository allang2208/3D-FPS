#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/PoseSnapshot.h"
#include "Engine/DataAsset.h"
#include "GameFramework/Actor.h"
#include "QuadrupedAnimationTemplate.generated.h"

class UAnimSequence;
class USkeletalMesh;
class USkeletalMeshComponent;

USTRUCT(BlueprintType)
struct FPSGAME_API FQuadrupedTemplateAction
{
    GENERATED_BODY()

    UPROPERTY(EditAnywhere, BlueprintReadOnly) TObjectPtr<UAnimSequence> Sequence;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bLoop = false;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bHoldLastPose = false;
    /** Terminal actions can interrupt anything and cannot be cancelled. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly) bool bTerminal = false;
    /** Optional follow-up for authored transitions such as RestEnter -> RestLoop. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly) FName NextAction;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0")) float BlendSeconds = 0.15f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, meta=(ClampMin="0.01")) float PlayRate = 1.f;
    /** -1 means not authored. The template never applies damage itself. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float ContactStartSeconds = -1.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly) float ContactEndSeconds = -1.f;
};

/** One compatible skeleton per set. Retarget before assigning another skeleton. */
UCLASS(BlueprintType)
class FPSGAME_API UQuadrupedAnimationSet : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Quadruped") TObjectPtr<USkeletalMesh> ReferenceMesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Quadruped") TMap<FName, FQuadrupedTemplateAction> Actions;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Locomotion", meta=(ClampMin="1", Units="cm/s")) float WalkSpeed = 140.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Locomotion", meta=(ClampMin="1", Units="cm/s")) float RunSpeed = 450.f;
    /** Gait selection is separate from the source speed used to calculate stride length. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Locomotion", meta=(ClampMin="0", ClampMax="1")) float RunBlendStartRatio = .35f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Locomotion", meta=(ClampMin="0", ClampMax="1")) float RunBlendFullRatio = .65f;
    /** Authored turn clips reach full weight at this owner yaw speed; optional slots fall back to straight. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Locomotion", meta=(ClampMin="1", Units="deg/s")) float FullTurnYawRate = 120.f;
    /** Normalized phase offsets, to be fitted to the target animal's foot contacts. */
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Locomotion", meta=(ClampMin="0", ClampMax="1")) float WalkPhaseOffset = 0.f;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Locomotion", meta=(ClampMin="0", ClampMax="1")) float RunPhaseOffset = 0.f;

    const FQuadrupedTemplateAction* FindAction(FName Name) const { return Actions.Find(Name); }
    UAnimSequence* FindSequence(FName Name) const;
};

/** Native pose graph, presentation only. No AI, damage, root motion or notifies. */
UCLASS(Transient, BlueprintType)
class FPSGAME_API UQuadrupedTemplateAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable, Category="Quadruped") bool SetAnimationSet(UQuadrupedAnimationSet* NewSet);
    /** External clock uses source seconds via SetActionTime; otherwise time advances locally. */
    UFUNCTION(BlueprintCallable, Category="Quadruped") bool PlayTemplateAction(FName ActionName, bool bExternalClock = false);
    UFUNCTION(BlueprintCallable, Category="Quadruped") void SetActionTime(float SourceSeconds);
    /** Synchronize externally sampled contact poses after a skipped blend interval. */
    void FinishPoseTransition();
    UFUNCTION(BlueprintCallable, Category="Quadruped") bool ResumeLocomotion(float BlendSeconds = 0.15f);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Quadruped") bool bUseOwnerVelocity = true;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Quadruped", meta=(ClampMin="0", Units="cm/s")) float ManualSpeed = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Quadruped") float Speed = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Quadruped") FName ActiveAction;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Quadruped") float ActionTime = 0.f;
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Quadruped") TObjectPtr<UQuadrupedAnimationSet> AnimationSet;

    virtual void NativeInitializeAnimation() override;
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;

    UPROPERTY(Transient) FQuadrupedTemplateAction ActiveDefinition;
    UPROPERTY(Transient) FPoseSnapshot PreviousPose;
    float IdleTime = 0.f;
    float GaitPhase = 0.f;
    float WalkRunAlpha = 0.f;
    float TurnAlpha = 0.f;
    float MoveAlpha = 0.f;
    float TransitionAlpha = 1.f;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
private:
    void BeginPoseTransition(float Seconds);
    float TransitionTime = 0.f;
    float TransitionDuration = 0.f;
    bool bUseExternalClock = false;
    bool bTerminalPose = false;
    bool bHasOwnerYaw = false;
    float PreviousOwnerYaw = 0.f;
};

/** Placeable animation template only; attach the anim instance/set to a real monster later. */
UCLASS(Blueprintable)
class FPSGAME_API AQuadrupedAnimationTemplate : public AActor
{
    GENERATED_BODY()
public:
    AQuadrupedAnimationTemplate();
    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Quadruped") TObjectPtr<USkeletalMeshComponent> Mesh;
    UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Quadruped") TObjectPtr<UQuadrupedAnimationSet> AnimationSet;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Quadruped") bool bUseOwnerVelocity = false;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Quadruped", meta=(ClampMin="0", Units="cm/s")) float ManualSpeed = 0.f;
    /** Empty means locomotion. Applied once on BeginPlay, not in the editor. */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Quadruped") FName InitialAction;
    UFUNCTION(BlueprintCallable, Category="Quadruped") bool PlayTemplateAction(FName ActionName, bool bExternalClock = false);
    UFUNCTION(BlueprintCallable, Category="Quadruped") void SetActionTime(float SourceSeconds);
    UFUNCTION(BlueprintCallable, Category="Quadruped") bool ResumeLocomotion();
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void Tick(float DeltaSeconds) override;
protected:
    virtual void BeginPlay() override;
};
