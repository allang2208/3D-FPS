#include "FPSPlayerHeadAnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "AnimNodes/AnimNode_CopyPoseFromMesh.h"

namespace FPSHeadAnimation
{
struct FProxy : FAnimInstanceProxy
{
    FAnimNode_CopyPoseFromMesh Copy;
    explicit FProxy(UAnimInstance* Instance):FAnimInstanceProxy(Instance)
    {Copy.bUseAttachedParent=true;Copy.bUseMeshPose=true;}
    virtual FAnimNode_Base* GetCustomRootNode() override {return &Copy;}
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override {Nodes.Add(&Copy);}
};
}
FAnimInstanceProxy* UFPSPlayerHeadAnimInstance::CreateAnimInstanceProxy(){return new FPSHeadAnimation::FProxy(this);}
void UFPSPlayerHeadAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy){delete Proxy;}
