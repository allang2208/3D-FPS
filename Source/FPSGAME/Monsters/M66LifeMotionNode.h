#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimNodeBase.h"
#include "BoneContainer.h"

/** Cosmetic local detail on the existing pose, enabled only for live locomotion. */
struct FM66LifeMotionNode : FAnimNode_Base
{
    FPoseLink Source;
    double Seconds=0.;
    float Alpha=0.f,Movement=0.f;
    FM66LifeMotionNode();
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override;
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override;
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override;
    virtual void Evaluate_AnyThread(FPoseContext& Output) override;
    virtual void GatherDebugData(FNodeDebugData& DebugData) override;
private:
    TArray<FBoneReference> Eyes,Sacs;
    TArray<float> InverseSacScale;
};
