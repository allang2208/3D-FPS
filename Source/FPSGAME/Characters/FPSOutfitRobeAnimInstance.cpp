#include "FPSOutfitRobeAnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "AnimNodes/AnimNode_CopyPoseFromMesh.h"
#include "Components/SkeletalMeshComponent.h"

namespace FPSRobeAnimation
{
struct FProxy : FAnimInstanceProxy
{
    FAnimNode_CopyPoseFromMesh Copy;
    explicit FProxy(UAnimInstance* Instance):FAnimInstanceProxy(Instance)
    {Copy.bUseAttachedParent=false;Copy.bUseMeshPose=false;}
    virtual void PreUpdate(UAnimInstance* Instance,float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance,DeltaSeconds);
        auto* Part=Instance->GetSkelMeshComponent();
        auto* Parent=Part?Cast<USkeletalMeshComponent>(Part->GetAttachParent()):nullptr;
        // The owner-only body is an anchor. Its leader already contains the
        // final world pose, including the existing IK and pelvis adjustment.
        Copy.SourceMeshComponent=Parent&&Parent->LeaderPoseComponent.IsValid()
            ?Cast<USkeletalMeshComponent>(Parent->LeaderPoseComponent.Get()):Parent;
    }
    virtual FAnimNode_Base* GetCustomRootNode() override {return &Copy;}
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override {Nodes.Add(&Copy);}
};
}
FAnimInstanceProxy* UFPSOutfitRobeAnimInstance::CreateAnimInstanceProxy(){return new FPSRobeAnimation::FProxy(this);}
void UFPSOutfitRobeAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy){delete Proxy;}
