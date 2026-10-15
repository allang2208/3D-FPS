#include "HeQueAnimInstance.h"
#include "HeQueMonster.h"
#include "MonsterSurfaceGroundingNode.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/CharacterMovementComponent.h"

// This graph is owned by a native proxy, without UAnimBlueprint NodeData.
// FAnimNode_Inertialization evaluates GetNodeIndex() even during initial pose
// evaluation. Keep the transition local to this graph instead of fabricating
// blueprint metadata or disabling engine assertions/tracing.
struct FHeQuePoseTransition : FAnimNode_Base
{
    FPoseLink Source;
    TArray<FTransform> LastPose,OutgoingPose;
    float BlendAge=.14f;
    float BlendDuration=.14f,NextBlendDuration=.14f;
    bool bTransition=false,bSnap=false;
    void ClearHistory()
    {
        LastPose.Reset();OutgoingPose.Reset();BlendAge=BlendDuration=NextBlendDuration=.14f;bTransition=bSnap=false;
    }
    virtual void Initialize_AnyThread(const FAnimationInitializeContext& Context) override
    {
        FAnimNode_Base::Initialize_AnyThread(Context);ClearHistory();Source.Initialize(Context);
    }
    virtual void CacheBones_AnyThread(const FAnimationCacheBonesContext& Context) override
    {
        // Compact bone indices can change at a LOD/skeleton boundary.
        ClearHistory();Source.CacheBones(Context);
    }
    virtual void Update_AnyThread(const FAnimationUpdateContext& Context) override
    {
        if(!bTransition)BlendAge=FMath::Min(BlendDuration,BlendAge+FMath::Max(0.f,Context.GetDeltaTime()));
        Source.Update(Context);
    }
    virtual void Evaluate_AnyThread(FPoseContext& Output) override
    {
        Source.Evaluate(Output);
        const int32 Count=Output.Pose.GetNumBones();
        if(bSnap)
        {
            // Death hands the exact authored pose to the soft corpse, including
            // zero-delta evaluation and late replicated death records.
            OutgoingPose.Reset();BlendAge=BlendDuration;
        }
        else if(bTransition)
        {
            OutgoingPose=LastPose;
            BlendDuration=NextBlendDuration;
            BlendAge=OutgoingPose.Num()==Count?0.f:BlendDuration;
        }
        bTransition=bSnap=false;
        if(BlendAge<BlendDuration&&OutgoingPose.Num()==Count)
        {
            const float Weight=FMath::SmoothStep(0.f,BlendDuration,BlendAge);
            for(int32 I=0;I<Count;++I)
            {
                const FCompactPoseBoneIndex Bone(I);
                const FTransform Target=Output.Pose[Bone];
                Output.Pose[Bone].Blend(OutgoingPose[I],Target,Weight);
            }
            Output.Pose.NormalizeRotations();
        }
        // Capture before grounding so terrain corrections are applied only once.
        LastPose.SetNum(Count);
        for(int32 I=0;I<Count;++I)LastPose[I]=Output.Pose[FCompactPoseBoneIndex(I)];
    }
    virtual bool NeedsDynamicReset() const override {return true;}
    virtual void ResetDynamics(ETeleportType) override {ClearHistory();}
    virtual void GatherDebugData(FNodeDebugData& DebugData) override {Source.GatherDebugData(DebugData);}
};
struct FHeQueAnimProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Idle,Move,Left,Right,React;
    FAnimNode_TwoWayBlend Turn,Travel,Rest,Reaction;
    FHeQuePoseTransition Transition;
    uint32 ReactionVersion=0,AttackVersion=0;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FMonsterSurfaceGroundingNode Ground;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;
    explicit FHeQueAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance),Ground(Instance)
    {
        Turn.A.SetLinkNode(&Left);Turn.B.SetLinkNode(&Right);
        Travel.A.SetLinkNode(&Move);Travel.B.SetLinkNode(&Turn);
        Rest.A.SetLinkNode(&Idle);Rest.B.SetLinkNode(&Travel);
        Reaction.A.SetLinkNode(&Rest);Reaction.B.SetLinkNode(&React);
        Transition.Source.SetLinkNode(&Reaction);ToComponent.LocalPose.SetLinkNode(&Transition);
        Ground.ComponentPose.SetLinkNode(&ToComponent);ToLocal.ComponentPose.SetLinkNode(&Ground);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override {return &ToLocal;}
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {Nodes.Append({&Idle,&Move,&Left,&Right,&React,&Turn,&Travel,&Rest,&Reaction,&Transition,&ToComponent,&Ground,&ToLocal});}
    virtual void PreUpdate(UAnimInstance* Instance,float Dt) override
    {
        FAnimInstanceProxy::PreUpdate(Instance,Dt);
        const auto* A=CastChecked<UHeQueAnimInstance>(Instance);
        auto Sample=[](FAnimNode_SequenceEvaluator_Standalone& Node,UAnimSequence* Clip,float Seconds)
        {
            Node.SetSequence(Clip);Node.SetShouldLoop(true);
            Node.SetTeleportToExplicitTime(true);Node.SetExplicitTime(Seconds);
        };
        Sample(Idle,A->Idle,A->IdleTime);
        Sample(Move,A->Move,A->Move?A->Phase*A->Move->GetPlayLength():0.f);
        Sample(Left,A->Left,A->Left?A->Phase*A->Left->GetPlayLength():0.f);
        Sample(Right,A->Right,A->Right?A->Phase*A->Right->GetPlayLength():0.f);
        Turn.Alpha=A->RightWeight;Travel.Alpha=A->TurnWeight;Rest.Alpha=A->Activity;
        Sample(React,A->Reaction,A->ReactionTime);React.SetShouldLoop(A->bLoopReaction);
        Reaction.Alpha=A->bReaction?1.f:0.f;
        if(ReactionVersion!=A->ReactionVersion||AttackVersion!=A->AttackVersion)
        {
            ReactionVersion=A->ReactionVersion;
            AttackVersion=A->AttackVersion;
            Transition.NextBlendDuration=A->TransitionSeconds;
            Transition.bTransition=true;
        }
        if(A->bDeathHandoffSample)Transition.bSnap=true;
        Ground.Prepare(Cast<ACharacter>(Instance->TryGetPawnOwner()),Dt);
    }
};
void UHeQueAnimInstance::NativeInitializeAnimation()
{
    Super::NativeInitializeAnimation();bHaveTransform=bWasGettingUp=false;
    Phase=IdleTime=Activity=TurnWeight=0.f;RightWeight=.5f;
    ReactionTime=0.f;ReactionVersion=AttackVersion=0;bReaction=bLoopReaction=bDeathHandoffSample=false;
    TransitionSeconds=.14f;
}
void UHeQueAnimInstance::NativeUpdateAnimation(float Dt)
{
    Super::NativeUpdateAnimation(Dt);
    const auto* Crown=Cast<AHeQueMonster>(TryGetPawnOwner());
    if (!Crown) return;
    Idle=Crown->IdleClip;Move=Crown->MoveClip;Left=Crown->TurnLeftClip;Right=Crown->TurnRightClip;
    Reaction=Crown->ReactionClip(ReactionTime,bLoopReaction);
    if(!Reaction&&Crown->IsJumpSlamming())
    {Reaction=Crown->JumpClip(ReactionTime);bLoopReaction=false;}
    if(!Reaction&&Crown->IsPsychic())
    {Reaction=Crown->PsychicClip;ReactionTime=Crown->PsychicAge();bLoopReaction=false;}
    if(!Reaction&&Crown->IsClamping())
    {Reaction=Crown->ClampClip;ReactionTime=Crown->ClampAge();bLoopReaction=false;}
    if(!Reaction&&Crown->IsRifting())
    {Reaction=Crown->RiftClip;ReactionTime=Crown->RiftAge();bLoopReaction=false;}
    if(!Reaction&&Crown->IsSweeping())
    {Reaction=Crown->SweepClip;ReactionTime=Crown->SweepAge();bLoopReaction=false;}
    bReaction=Reaction!=nullptr;
    AttackVersion=Crown->SweepSerial()+Crown->RiftSerial()+Crown->ClampSerial()+Crown->PsychicSerial()+Crown->JumpSerial();
    ReactionVersion=Crown->ReactionSerial();
    // Preserve sharp contact while allowing the heavy recovery to settle into
    // the live locomotion phase without a standing-pose pop.
    switch(Crown->ReactionPhase())
    {
    case EHeQueReaction::Airborne:TransitionSeconds=.10f;break;
    case EHeQueReaction::Landing:TransitionSeconds=.065f;break;
    case EHeQueReaction::Down:case EHeQueReaction::GetUp:TransitionSeconds=.10f;break;
    default:TransitionSeconds=.14f;break;
    }
    if(Crown->IsJumpSlamming())
    {
        // The dive and impact are shorter than the old 90/55 ms blends.
        // Keep the fast extension and first compression visible on contact.
        const EHeQueJumpPhase Jump=Crown->JumpPhase();
        TransitionSeconds=Jump==EHeQueJumpPhase::Recovery?.018f:Jump==EHeQueJumpPhase::Falling?.02f:.09f;
    }
    if(Crown->ReactionPhase()==EHeQueReaction::None&&bWasGettingUp)TransitionSeconds=.24f;
    bWasGettingUp=Crown->ReactionPhase()==EHeQueReaction::GetUp;
    bDeathHandoffSample=Crown->SamplingDeathHandoff();
    // Zero-delta evaluation is used to capture the exact soft-corpse handoff pose.
    if(Dt<=SMALL_NUMBER)return;
    // Interrupted attacks hold the sampled pose during the short fade.
    // Mesh world motion includes network smoothing and avoids stepping while
    // the capsule is blocked. Vertical stair correction never advances gait.
    const auto* Mesh=GetSkelMeshComponent();
    const FVector Location=Mesh->GetComponentLocation();const float Yaw=Mesh->GetComponentRotation().Yaw;
    float Distance=0.f,Angle=0.f;
    if (bHaveTransform && FVector::DistSquared(Location,PreviousLocation)<FMath::Square(250.f))
    {
        Distance=FVector::Dist2D(Location,PreviousLocation);
        Angle=FMath::FindDeltaAngleDegrees(PreviousYaw,Yaw);
    }
    PreviousLocation=Location;PreviousYaw=Yaw;bHaveTransform=true;
    if (Crown->Busy() || !Crown->GetCharacterMovement()->IsMovingOnGround()) Distance=Angle=0.f;
    const float LinearCycles=Distance/FMath::Max(1.f,Crown->StrideDistance);
    const float AngularCycles=FMath::Abs(Angle)/FMath::Max(1.f,Crown->TurnStrideDegrees);
    const float Cycles=LinearCycles+AngularCycles;
    Phase=FMath::Fmod(Phase+Cycles,1.f);
    const bool Active=Distance/Dt>1.f || FMath::Abs(Angle)/Dt>1.f;
    Activity=FMath::FInterpConstantTo(Activity,Active?1.f:0.f,Dt,3.2f);
    if (Cycles>SMALL_NUMBER)
    {
        TurnWeight=AngularCycles/Cycles;
        // UE positive yaw is a right turn; source Blender positive Z is left.
        if (FMath::Abs(Angle)>.001f) RightWeight=FMath::FInterpConstantTo(RightWeight,Angle>0?1.f:0.f,Dt,10.f);
    }
    // Idle breathing pauses while walking/turning; the locomotion phase never resets.
    if (!Active && !Crown->Busy() && Idle) IdleTime=FMath::Fmod(IdleTime+Dt,Idle->GetPlayLength());
}
FAnimInstanceProxy* UHeQueAnimInstance::CreateAnimInstanceProxy(){return new FHeQueAnimProxy(this);}
void UHeQueAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy){delete Proxy;}
