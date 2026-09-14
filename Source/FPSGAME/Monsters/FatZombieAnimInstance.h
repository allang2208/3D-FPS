#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/PoseSnapshot.h"
#include "FatZombieAnimInstance.generated.h"

class UAnimSequence;

/** Presentation only: combat retains its existing authoritative attack clock. */
UCLASS(Transient)
class FPSGAME_API UFatZombieAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    void TransitionTo(UAnimSequence* Clip, bool bLoop, bool bCombatClock, float BlendSeconds);
    void SetCombatTime(float Seconds);
    void FinishClip();
    void BeginHitReaction(const FVector& WorldDirection);
    void SetHitReactionTime(float Elapsed, float Remaining);
    void SetLocomotionRate(float Rate) { TargetPlayRate = FMath::Max(0.f, Rate); }
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;

    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ActiveClip;
    UPROPERTY(Transient) FPoseSnapshot PreviousPose;
    float ClipTime = 0.f;
    float BlendAlpha = 1.f;
    bool bLooping = true;
    FVector HitRotationVector = FVector::ZeroVector;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
private:
    TMap<TWeakObjectPtr<UAnimSequence>, float> LoopTimes;
    float BlendDuration = 0.f;
    float BlendElapsed = 0.f;
    float PlayRate = 1.f;
    float TargetPlayRate = 1.f;
    bool bUseCombatClock = false;
    FVector HitStartRotation = FVector::ZeroVector;
    FVector HitPeakRotation = FVector::ZeroVector;
};
