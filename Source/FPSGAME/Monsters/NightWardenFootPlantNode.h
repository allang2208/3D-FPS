#pragma once
#include "CoreMinimal.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
class ANightWardenMonster;

/** Two stance contacts, driven by the saved walk's plant curves. */
struct FNightWardenFootPlantNode : FAnimNode_SkeletalControlBase
{
    FNightWardenFootPlantNode();
    void Prepare(const ANightWardenMonster* Monster,float Time,float Weight,float DeltaSeconds);
protected:
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override;
    virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer& Bones) override;
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out) override;
private:
    struct FLeg
    {
        FBoneReference Hip,Knee,Foot;
        FVector Sole=FVector::ZeroVector,Point=FVector::ZeroVector,Normal=FVector::UpVector;
        FVector Anchor=FVector::ZeroVector;
        FQuat Rotation=FQuat::Identity;
        float Weight=0.f;
        bool Ground=false,Locked=false,Released=false;
    };
    FLeg Legs[2];
    FTransform Frame=FTransform::Identity,PreviousFrame=FTransform::Identity;
    float TraceAge=1.f;
    bool Enabled=false,WasEnabled=false;
};
