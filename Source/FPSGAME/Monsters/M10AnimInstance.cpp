#include "M10AnimInstance.h"
#include "M10Mawcrawler.h"
#include "M10MovementComponent.h"
#include "M10FootPlantNode.h"
#include "M10TissueNode.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "Components/SkeletalMeshComponent.h"

struct FM10AnimProxy : FAnimInstanceProxy
{
    FAnimNode_PoseSnapshot Previous;
    FAnimNode_SequenceEvaluator_Standalone Outgoing,Current,Straight,CurveLeft,CurveRight,PivotLeft,PivotRight;
    FAnimNode_TwoWayBlend Source,Transition,CurveSides,PivotSides,CurvedWalk,Gait,Locomotion;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FM10FootPlantNode Feet;
    FM10TissueNode Tissue;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;
    FTransform CapturedRoot=FTransform::Identity,NeutralSnapshotRoot=FTransform::Identity;
    bool HaveSnapshotRoot=false;
    explicit FM10AnimProxy(UAnimInstance* Instance):FAnimInstanceProxy(Instance)
    {
        Previous.Mode=ESnapshotSourceMode::SnapshotPin;
        Source.A.SetLinkNode(&Previous);Source.B.SetLinkNode(&Outgoing);
        Transition.A.SetLinkNode(&Source);Transition.B.SetLinkNode(&Current);
        CurveSides.A.SetLinkNode(&CurveLeft);CurveSides.B.SetLinkNode(&CurveRight);
        PivotSides.A.SetLinkNode(&PivotLeft);PivotSides.B.SetLinkNode(&PivotRight);
        CurvedWalk.A.SetLinkNode(&Straight);CurvedWalk.B.SetLinkNode(&CurveSides);
        Gait.A.SetLinkNode(&CurvedWalk);Gait.B.SetLinkNode(&PivotSides);
        Locomotion.A.SetLinkNode(&Transition);Locomotion.B.SetLinkNode(&Gait);
        ToComponent.LocalPose.SetLinkNode(&Locomotion);Feet.ComponentPose.SetLinkNode(&ToComponent);Tissue.ComponentPose.SetLinkNode(&Feet);ToLocal.ComponentPose.SetLinkNode(&Tissue);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override {return &ToLocal;}
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {
        Nodes.Append({&Previous,&Outgoing,&Current,&Straight,&CurveLeft,&CurveRight,&PivotLeft,&PivotRight,&Source,&Transition,&CurveSides,&PivotSides,&CurvedWalk,&Gait,&Locomotion,&ToComponent,&Feet,&Tissue,&ToLocal});
    }
    static void Sample(FAnimNode_SequenceEvaluator_Standalone& Node,UAnimSequence* Clip,float Seconds,bool Loop)
    {
        Node.SetSequence(Clip);Node.SetShouldLoop(Loop);Node.SetTeleportToExplicitTime(true);Node.SetExplicitTime(Seconds);
    }
    virtual void PreUpdate(UAnimInstance* Instance,float Dt) override
    {
        FAnimInstanceProxy::PreUpdate(Instance,Dt);
        const auto* D=CastChecked<UM10AnimInstance>(Instance);const auto* M=Cast<AM10Mawcrawler>(D->TryGetPawnOwner());
        if(!M)return;
        Previous.Snapshot=D->PreviousPose;Sample(Outgoing,D->OutgoingLoop,D->OutgoingLoopTime,true);Source.Alpha=D->OutgoingLoop?1.f:0.f;
        if(Previous.Snapshot.bIsValid&&!Previous.Snapshot.LocalTransforms.IsEmpty())
        {
            const FTransform Root=Previous.Snapshot.LocalTransforms[0];
            if(!HaveSnapshotRoot||!Root.Equals(CapturedRoot,.0001f))
            {CapturedRoot=Root;NeutralSnapshotRoot=Feet.RemoveGrounding(Root);HaveSnapshotRoot=true;}
            // The visible snapshot includes last frame's terrain correction.
            // Remove it once before applying this frame's support to the blend.
            Previous.Snapshot.LocalTransforms[0]=NeutralSnapshotRoot;
        }
        Sample(Current,D->LocomotionAllowed?M->IdleClip.Get():D->ActiveClip.Get(),D->LocomotionAllowed?D->IdleTime:D->ClipTime,D->LocomotionAllowed||D->bLooping);
        Transition.Alpha=D->PreviousPose.bIsValid?D->BlendAlpha:1.f;
        auto GaitClip=[&](FAnimNode_SequenceEvaluator_Standalone& Node,UAnimSequence* Clip){Sample(Node,Clip,Clip?D->GaitPhase*Clip->GetPlayLength():0.f,true);};
        GaitClip(Straight,M->MoveClip);GaitClip(CurveLeft,M->CurveLeftClip);GaitClip(CurveRight,M->CurveRightClip);GaitClip(PivotLeft,M->PivotLeftClip);GaitClip(PivotRight,M->PivotRightClip);
        CurveSides.Alpha=PivotSides.Alpha=D->RightWeight;CurvedWalk.Alpha=D->CurveWeight;Gait.Alpha=D->PivotWeight;
        Locomotion.Alpha=D->LocomotionAllowed?D->LocomotionWeight:0.f;
        const float Turning=1.f-(1.f-D->CurveWeight)*(1.f-D->PivotWeight);
        Feet.Prepare(M,D->GaitPhase,FMath::Lerp(.65f,.75f,Turning),Locomotion.Alpha,D->GaitRate,Dt,D->LocomotionAllowed&&Locomotion.Alpha>.02f);
    }
};
void UM10AnimInstance::NativeUpdateAnimation(float Dt)
{
    Super::NativeUpdateAnimation(Dt);
    const auto* M=Cast<AM10Mawcrawler>(TryGetPawnOwner());if(!M)return;
    const float Yaw=M->GetActorRotation().Yaw;
    const float MaxYawRate=FMath::Max(M->MovingTurnSpeed,M->PivotTurnSpeed);
    const float ActualYawRate=HaveYaw&&Dt>SMALL_NUMBER?FMath::Clamp(FMath::FindDeltaAngleDegrees(LastYaw,Yaw)/Dt,-MaxYawRate,MaxYawRate):0.f;
    HaveYaw=true;LastYaw=Yaw;
    LocomotionAllowed=!M->Busy()&&M->GetCharacterMovement()->IsMovingOnGround();
    if(!LocomotionAllowed){LocomotionWeight=0.f;SmoothedYawRate=0.f;GaitRate=0.f;return;}
    SmoothedYawRate=FMath::FInterpTo(SmoothedYawRate,ActualYawRate,Dt,14.f);
    // Keep the authored distance and degrees per step. Faster translation and
    // turning advance this same phase without rescaling the source clips.
    const float Speed=M->GetVelocity().Size2D(),WalkRate=Speed/FMath::Max(1.f,M->AnimationWalkSpeed),TurnRate=FMath::Abs(SmoothedYawRate)/10.f;
    const float Rate=FMath::Max(WalkRate,TurnRate);
    GaitRate=Rate;
    GaitPhase=FMath::Frac(GaitPhase+Dt*Rate/1.2f);
    IdleTime=M->IdleClip?FMath::Fmod(IdleTime+Dt,FMath::Max(.01f,M->IdleClip->GetPlayLength())):0.f;
    LocomotionWeight=FMath::FInterpConstantTo(LocomotionWeight,Rate>.035f?1.f:0.f,Dt,4.f);
    CurveWeight=FMath::FInterpTo(CurveWeight,Rate>.001f?FMath::Clamp(TurnRate/Rate,0.f,1.f):0.f,Dt,10.f);
    PivotWeight=FMath::FInterpTo(PivotWeight,Rate>.001f?1.f-FMath::Clamp(WalkRate/Rate,0.f,1.f):0.f,Dt,10.f);
    if(FMath::Abs(SmoothedYawRate)>.2f)RightWeight=FMath::FInterpConstantTo(RightWeight,SmoothedYawRate>0.f?1.f:0.f,Dt,5.f);
    // A return/attack interruption retains one phase, rather than restarting a step.
    if(M->MoveClip&&ActiveClip==M->MoveClip)ClipTime=GaitPhase*M->MoveClip->GetPlayLength();
}
FAnimInstanceProxy* UM10AnimInstance::CreateAnimInstanceProxy(){return new FM10AnimProxy(this);}
void UM10AnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy){delete Proxy;}
