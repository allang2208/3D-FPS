#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimNodeBase.h"
#include "Animation/BoneReference.h"

class UWeaponGripProfile;
class UAnimSequence;
struct FWeaponGripClip;

// Applied to each unblended sequence, including both sprint transition and loop.
// Source time comes from the same sequence evaluator; no independent clock/state.
struct FWeaponGripProfileNode : FAnimNode_Base
{
    FPoseLink Source;
    const UWeaponGripProfile* Profile=nullptr;
    const UAnimSequence* Clip=nullptr;
    float Time=0.f;
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override {Source.Initialize(Context);}
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override;
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override {Source.Update(Context);}
    virtual void Evaluate_AnyThread(FPoseContext& Output) override;
private:
    const UWeaponGripProfile* CachedProfile=nullptr;
    const UAnimSequence* CachedClip=nullptr;
    const FWeaponGripClip* Layer=nullptr;
    TArray<FBoneReference> Bones;
};
