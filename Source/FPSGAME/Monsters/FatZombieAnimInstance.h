#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "Animation/PoseSnapshot.h"
#include "FatZombieAnimInstance.generated.h"

class UAnimSequence;

/** Optional transition presentation; existing monsters retain snapshot blending. */
struct FMonsterClipTransition
{
    float StartTime = -1.f;
    float InitialPlayRate = 1.f;
    bool bContinueOutgoingLoop = false;
    // Mutant3's Spine02 is the first spine above Hips. Keep Hips and legs in
    // the grounded destination pose, while blending its upper-body branch.
    bool bGroundLowerBody = false;
};

/** Presentation only: combat retains its existing authoritative attack clock. */
UCLASS(Transient)
class FPSGAME_API UFatZombieAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    void TransitionTo(UAnimSequence* Clip, bool bLoop, bool bCombatClock, float BlendSeconds,
        const FMonsterClipTransition& Settings = FMonsterClipTransition());
    void SetCombatTime(float Seconds);
    void FinishClip();
    void HoldClipAtTime(float Seconds);
    void BeginHitReaction(UAnimSequence* ReactionClip, const FVector& WorldDirection, bool bParried, float BlendSeconds = 0.f);
    void BeginHitReaction(const FVector& WorldDirection) { BeginHitReaction(nullptr, WorldDirection, false); }
    void SetHitReactionTime(float Elapsed, float Remaining);
    void SetLocomotionRate(float Rate) { TargetPlayRate = FMath::Max(0.f, Rate); }
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;

    UPROPERTY(Transient) TObjectPtr<UAnimSequence> ActiveClip;
    UPROPERTY(Transient) FPoseSnapshot PreviousPose;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> OutgoingLoop;
    float OutgoingLoopTime = 0.f;
    bool bGroundLowerBody = false;
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
    float OutgoingLoopRate = 1.f;
    bool bUseCombatClock = false;
    bool bPlayingHitClip = false;
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> PendingHitClip;
    bool bRewindingParry = false;
    float ParryRewindStartTime = 0.f;
    float HitClipTimeOffset = 0.f;
    FVector HitStartRotation = FVector::ZeroVector;
    FVector HitPeakRotation = FVector::ZeroVector;
};
