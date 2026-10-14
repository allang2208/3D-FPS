#include "FPSPlayerHeadAnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "AnimNodes/AnimNode_CopyPoseFromMesh.h"

namespace FPSHeadAnimation
{
struct FProxy : FAnimInstanceProxy
{
    FAnimNode_CopyPoseFromMesh Copy;
    explicit FProxy(UAnimInstance* Instance):FAnimInstanceProxy(Instance)
    {
        // Body and face share the same spine/neck/head hierarchy and bind pose.
        // Copy their local transforms; face-only descendants keep their own bind
        // offsets instead of mixing absolute mesh poses with facial branches.
        Copy.bUseAttachedParent=true;Copy.bUseMeshPose=false;
    }
    virtual FAnimNode_Base* GetCustomRootNode() override {return &Copy;}
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override {Nodes.Add(&Copy);}
};
}
FAnimInstanceProxy* UFPSPlayerHeadAnimInstance::CreateAnimInstanceProxy(){return new FPSHeadAnimation::FProxy(this);}
void UFPSPlayerHeadAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy){delete Proxy;}
