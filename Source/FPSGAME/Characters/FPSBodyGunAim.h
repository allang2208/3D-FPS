#pragma once
#include "FPSBodyGunAimTypes.h"
#include "FPSBodySpineBlend.h"
#include "Animation/AnimInstanceProxy.h"

// Final cosmetic alignment, after source motion/contact solving and its history
// capture. Transport complete chains so twist bones, fingers and grips stay native.
struct FFPSBodyGunAimNode : FAnimNode_Base
{
    FPoseLink Source;
    FFPSBodyGunAimFrame Guns[2];
    FBoneReference Hands[2]={FBoneReference(TEXT("hand_r")),FBoneReference(TEXT("hand_l"))};
    FFPSBodySpineBlend Spine;
    FVector Direction=FVector::RightVector,Target=FVector::ZeroVector;
    bool bUseTarget=false,bPaired=false,Enabled[2]={false,false};
    float Recoil[2]={0.f,0.f},Weight[2]={0.f,0.f},Delta=0.f;
    FQuat LastCorrection[2]={FQuat::Identity,FQuat::Identity};
    // Unknowns reuse body donors; players already solve their native contacts.
    FTransform SupportFromRight=FTransform::Identity;
    bool bFitSupport=false;
    float SupportWeight=0.f;

    void Reset();
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override;
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override;
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override;
    virtual void Evaluate_AnyThread(FPoseContext& Output) override;
    virtual void GatherDebugData(FNodeDebugData& DebugData) override { Source.GatherDebugData(DebugData); }
    virtual bool NeedsDynamicReset() const override { return true; }
    virtual void ResetDynamics(ETeleportType) override { Reset(); }
};
