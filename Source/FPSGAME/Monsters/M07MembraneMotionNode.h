#pragma once
#include "CoreMinimal.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"

/** Whole-leaf skinning with a small, damped bend; no particle/display capture. */
struct FM07MembraneMotionNode : FAnimNode_SkeletalControlBase
{
    FM07MembraneMotionNode();
    void Prepare(float DeltaSeconds, bool bEnabled, const FVector& MeshAcceleration, const FVector& MeshRear);
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override;
    virtual bool IsValidToEvaluate(const USkeleton*, const FBoneContainer& Bones) override;
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,
        TArray<FBoneTransform>& Out) override;
private:
    FBoneReference Gill[6][3];
    FQuat ReferenceRoot[6];
    FQuat PreviousRoot[6];
    double Bend[6]={};
    double BendSpeed[6]={};
    FVector Acceleration=FVector::ZeroVector;
    FVector Rear=FVector(0.,-1.,0.);
    double StepSeconds=0.;
    double MotionTime=0.;
    bool bHasPreviousPose=false;
};
