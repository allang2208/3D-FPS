#pragma once

#include "Animation/AnimNodeBase.h"
#include "Animation/BoneReference.h"

class UAnimSequence;
class UFPSGunplayAnimInstance;
class UFPSModularOutfitComponent;
struct FSteelGauntletClip;

// Local presentation only. Six authored rotations follow the existing action
// clock; inventory and gameplay authority remain with their existing owners.
struct FSteelGauntletPoseNode : FAnimNode_Base
{
    FPoseLink Source;
    FSteelGauntletPoseNode();
    void Configure(const UFPSGunplayAnimInstance& Instance);
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override;
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override;
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override;
    virtual void Evaluate_AnyThread(FPoseContext& Output) override;

private:
    FBoneReference Fingers[6];
    FBoneReference SupportHand;
    FQuat Corrections[6];
    FVector SupportClearance=FVector::ZeroVector;
    TWeakObjectPtr<UFPSModularOutfitComponent> Outfit;
    TWeakObjectPtr<UAnimSequence> Sequences[3];
    const FSteelGauntletClip* Clips[3] = {};
    bool bEnabled = false;
    bool bOwnerResolved = false;
    const FSteelGauntletClip* ResolveClip(int32 Slot, UAnimSequence* Sequence);
};
