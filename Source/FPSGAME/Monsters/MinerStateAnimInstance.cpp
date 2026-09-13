#include "MinerStateAnimInstance.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"

struct FMinerStateAnimProxy : FAnimInstanceProxy
{
    FAnimNode_PoseSnapshot Previous;
    FAnimNode_SequenceEvaluator_Standalone Current;
    FAnimNode_TwoWayBlend Blend;
    explicit FMinerStateAnimProxy(UAnimInstance* Instance):FAnimInstanceProxy(Instance)
    {
        Previous.Mode=ESnapshotSourceMode::SnapshotPin;
        Blend.A.SetLinkNode(&Previous);Blend.B.SetLinkNode(&Current);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override { return &Blend; }
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override { Nodes.Append({&Previous,&Current,&Blend}); }
    virtual void PreUpdate(UAnimInstance* Instance,float DeltaSeconds) override
    {
        FAnimInstanceProxy::PreUpdate(Instance,DeltaSeconds);
        const auto* Data=CastChecked<UMinerStateAnimInstance>(Instance);
        Previous.Snapshot=Data->PreviousPose;
        Current.SetSequence(Data->CurrentClip);
        Current.SetExplicitTime(Data->ClipTime);
        Blend.Alpha=Data->PreviousPose.bIsValid?Data->BlendAlpha:1.f;
    }
};
void UMinerStateAnimInstance::StartClip(UAnimSequence* Clip,bool bLoop,const FPoseSnapshot& FromPose)
{
    CurrentClip=Clip;PreviousPose=FromPose;ClipTime=0;PlayRate=1;
    bLooping=bLoop;BlendElapsed=0;BlendAlpha=FromPose.bIsValid?0.f:1.f;
}
void UMinerStateAnimInstance::NativeUpdateAnimation(float DeltaSeconds)
{
    Super::NativeUpdateAnimation(DeltaSeconds);
    if(bLooping&&CurrentClip&&CurrentClip->GetPlayLength()>SMALL_NUMBER)
        ClipTime=FMath::Fmod(ClipTime+DeltaSeconds*PlayRate,CurrentClip->GetPlayLength());
    BlendElapsed+=DeltaSeconds;
    const float T=FMath::Clamp(BlendElapsed/.16f,0.f,1.f);
    BlendAlpha=T*T*(3.f-2.f*T);
}
FAnimInstanceProxy* UMinerStateAnimInstance::CreateAnimInstanceProxy() { return new FMinerStateAnimProxy(this); }
void UMinerStateAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) { delete Proxy; }
