#pragma once
#include "CoreMinimal.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"

/** Baked surface-patch clearance before low-density secondary cloth. */
struct FM07GillContactNode : FAnimNode_SkeletalControlBase
{
    FM07GillContactNode();
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override;
    virtual bool IsValidToEvaluate(const USkeleton*, const FBoneContainer& Bones) override;
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,
        TArray<FBoneTransform>& Out) override;
    float MaxOpeningDegrees = 18.f;
    FVector RearDirection = FVector(0., -1., 0.);
    int32 SampleStride = 1;
    int32 SolverPasses = 2;
private:
    FBoneReference Gill[6][3];
    FBoneReference Arm[2][7];
    FBoneReference Chest;
    FVector SampleLocal[6][9][3];
};
