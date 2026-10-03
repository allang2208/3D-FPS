#pragma once
#include "CoreMinimal.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"

/** Bounded six-leaf FK clearance before the low-density secondary cloth. */
struct FM07GillContactNode : FAnimNode_SkeletalControlBase
{
    FM07GillContactNode();
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override;
    virtual bool IsValidToEvaluate(const USkeleton*, const FBoneContainer& Bones) override;
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,
        TArray<FBoneTransform>& Out) override;
    float MaxOpeningDegrees = 18.f;
private:
    FBoneReference Gill[6][3];
    FBoneReference Arm[2][4];
    FBoneReference Chest;
};
