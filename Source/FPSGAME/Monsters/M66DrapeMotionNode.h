#pragma once
#include "CoreMinimal.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"

class AM66IncineratorMonster;

/** Four cosmetic flesh chains: world-space inertia, gravity and constrained links. */
struct FM66DrapeMotionNode : FAnimNode_SkeletalControlBase
{
    FM66DrapeMotionNode();
    void Prepare(const AM66IncineratorMonster* Owner,float DeltaSeconds);
    virtual bool NeedsDynamicReset() const override {return true;}
    virtual void ResetDynamics(ETeleportType) override;
protected:
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override;
    virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer& Bones) override;
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out) override;
private:
    static constexpr int32 Chains=4,Joints=4,Count=Chains*Joints;
    FBoneReference Flesh[Count],Pelvis,Leg[6];
    FTransform Local[Count],Result[Count],Frame=FTransform::Identity;
    FVector Position[Count]{},Velocity[Count]{},PreviousTarget[Count]{};
    float Dt=0.f,WorldScale=1.f;
    uint64 Serial=0,Solved=MAX_uint64;
    bool Enabled=false,Initialized=false,ResetRequested=true;
};
