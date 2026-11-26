#include "FPSPlayerHeadAnimInstance.h"
#include "../NPC/ResidentGaze.h"
#include "../NPC/ResidentTurnAnimInstance.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/PlayerController.h"
#include "AnimNodes/AnimNode_CopyPoseFromMesh.h"

namespace FPSHeadAnimation
{
struct FProxy : FAnimInstanceProxy
{
    FAnimNode_CopyPoseFromMesh Copy;
    FResidentGaze EyeGaze;
    TWeakObjectPtr<USkeletalMesh> FaceRig,BodyRig;
    bool bFaceOwnsEyes=false;

    explicit FProxy(UAnimInstance* Instance):FAnimInstanceProxy(Instance)
    {
        // Body and face share the same spine/neck/head hierarchy and bind pose.
        // Copy their local transforms; face-only descendants keep their own bind
        // offsets instead of mixing absolute mesh poses with facial branches.
        Copy.bUseAttachedParent=true;Copy.bUseMeshPose=false;
    }
    virtual void PreUpdate(UAnimInstance* Instance,float Delta) override
    {
        FAnimInstanceProxy::PreUpdate(Instance,Delta);
        auto* Face=Instance->GetSkelMeshComponent();
        auto* Body=Face?Cast<USkeletalMeshComponent>(Face->GetAttachParent()):nullptr;
        const auto* Turn=Body?Cast<UResidentTurnAnimInstance>(Body->GetAnimInstance()):nullptr;
        const auto* Viewer=Turn?Turn->ConversationPlayer.Get():nullptr;
        if (!Face || (!Viewer && !EyeGaze.IsActive())) return;
        if (Viewer && (FaceRig.Get()!=Face->GetSkeletalMeshAsset() || BodyRig.Get()!=Body->GetSkeletalMeshAsset()))
        {
            FaceRig=Face->GetSkeletalMeshAsset();
            BodyRig=Body->GetSkeletalMeshAsset();
            bFaceOwnsEyes=FResidentGaze::HasEyePair(*Face) && !FResidentGaze::HasEyePair(*Body);
        }
        EyeGaze.UpdateTarget(*Face,bFaceOwnsEyes?Viewer:nullptr,Delta);
    }
    virtual bool Evaluate(FPoseContext& Output) override
    {
        if (!EyeGaze.IsActive()) return false; // Use the normal copy-pose root.
        Copy.Evaluate_AnyThread(Output);
        EyeGaze.Apply(Output,true);
        return true;
    }
    virtual FAnimNode_Base* GetCustomRootNode() override {return &Copy;}
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override {Nodes.Add(&Copy);}
};
}
FAnimInstanceProxy* UFPSPlayerHeadAnimInstance::CreateAnimInstanceProxy(){return new FPSHeadAnimation::FProxy(this);}
void UFPSPlayerHeadAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy){delete Proxy;}
