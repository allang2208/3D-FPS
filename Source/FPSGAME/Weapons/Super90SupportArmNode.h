#pragma once

#include "Animation/AnimNodeBase.h"
#include "Animation/BoneReference.h"

class USkeletalMesh;
class USkeletalMeshComponent;

// One native Super90 correction after channel/grip blending. Keeps the hand
// contact and gun pose; reconstructs the elbow and the actual V7 skin drivers.
struct FSuper90SupportArmNode : FAnimNode_Base
{
    FPoseLink Source;
    FSuper90SupportArmNode();
    void Configure(const USkeletalMeshComponent& Mesh);
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override { Source.Initialize(Context); }
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override;
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override { Source.Update(Context); }
    virtual void Evaluate_AnyThread(FPoseContext& Output) override;
private:
    enum { Clavicle, Upper, Lower, Aux, Twist02, Twist01, Hand, Index, Pinky, Count };
    FBoneReference Bones[Count];
    FTransform Rest[Count];
    FQuat RestForeBasis=FQuat::Identity;
    FVector RestUpper=FVector::ZeroVector, RestFore=FVector::ZeroVector, RestWidth=FVector::ZeroVector;
    float LengthRatio=1.f;
    TWeakObjectPtr<USkeletalMesh> CachedMesh;
    bool bEnabled=false, bReady=false;
};
