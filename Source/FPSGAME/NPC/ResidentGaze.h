#pragma once

#include "Animation/AnimInstanceProxy.h"

class APlayerController;

// Animation-proxy state. Only UpdateTarget reads the game world.
struct FResidentGaze
{
    void UpdateTarget(const USkeletalMeshComponent& Mesh,const APlayerController* Viewer,float Delta);
    void Apply(FPoseContext& Output,bool EyesOnly=false);
    bool IsActive() const { return Weight>KINDA_SMALL_NUMBER; }
    static bool HasEyePair(const USkeletalMeshComponent& Mesh);

private:
    struct FAimBone
    {
        FCompactPoseBoneIndex Index{INDEX_NONE};
        FTransform Reference=FTransform::Identity;
    };
    void CacheBones(const FBoneContainer& Bones);
    FAimBone Neck,Head,LeftEye,RightEye;
    TOptional<uint16> Serial;
    FVector SmoothedWorldTarget=FVector::ZeroVector;
    FVector ComponentTarget=FVector::ZeroVector;
    float Weight=0.f;
};
