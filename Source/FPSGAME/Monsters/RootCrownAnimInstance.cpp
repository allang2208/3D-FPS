#include "RootCrownAnimInstance.h"
#include "RootCrownRigPreview.h"
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
struct FRootCrownPoseTransition : FAnimNode_Base
{
    FPoseLink Source;
    TArray<FTransform> LastPose,OutgoingPose;
    float BlendAge=.14f;
    bool bTransition=false,bSnap=false;
    void ClearHistory()
    {
        LastPose.Reset();OutgoingPose.Reset();BlendAge=.14f;bTransition=bSnap=false;
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
        if(!bTransition)BlendAge=FMath::Min(.14f,BlendAge+FMath::Max(0.f,Context.GetDeltaTime()));
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
            OutgoingPose.Reset();BlendAge=.14f;
        }
        else if(bTransition)
        {
            OutgoingPose=LastPose;
            BlendAge=OutgoingPose.Num()==Count?0.f:.14f;
        }
        bTransition=bSnap=false;
        if(BlendAge<.14f&&OutgoingPose.Num()==Count)
        {
            const float Weight=FMath::SmoothStep(0.f,.14f,BlendAge);
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
struct FRootCrownAnimProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Idle,Move,Left,Right,Strike,React;
    FAnimNode_TwoWayBlend Turn,Travel,Rest,Action,Reaction;
    FRootCrownPoseTransition Transition;
    uint32 ReactionVersion=0;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FMonsterSurfaceGroundingNode Ground;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;
    explicit FRootCrownAnimProxy(UAnimInstance* Instance) : FAnimInstanceProxy(Instance),Ground(Instance)
    {
        Turn.A.SetLinkNode(&Left);Turn.B.SetLinkNode(&Right);
        Travel.A.SetLinkNode(&Move);Travel.B.SetLinkNode(&Turn);
        Rest.A.SetLinkNode(&Idle);Rest.B.SetLinkNode(&Travel);
        Action.A.SetLinkNode(&Rest);Action.B.SetLinkNode(&Strike);
        Reaction.A.SetLinkNode(&Action);Reaction.B.SetLinkNode(&React);
        Transition.Source.SetLinkNode(&Reaction);ToComponent.LocalPose.SetLinkNode(&Transition);
        Ground.ComponentPose.SetLinkNode(&ToComponent);ToLocal.ComponentPose.SetLinkNode(&Ground);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override {return &ToLocal;}
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {Nodes.Append({&Idle,&Move,&Left,&Right,&Strike,&React,&Turn,&Travel,&Rest,&Action,&Reaction,&Transition,&ToComponent,&Ground,&ToLocal});}
    virtual void PreUpdate(UAnimInstance* Instance,float Dt) override
    {
        FAnimInstanceProxy::PreUpdate(Instance,Dt);
        const auto* A=CastChecked<URootCrownAnimInstance>(Instance);
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
        Sample(Strike,A->Slash,A->SlashTime);Strike.SetShouldLoop(false);Action.Alpha=A->SlashBlend;
        Sample(React,A->Reaction,A->ReactionTime);React.SetShouldLoop(A->bLoopReaction);
        Reaction.Alpha=A->bReaction?1.f:0.f;
        if(ReactionVersion!=A->ReactionVersion)
        {
            ReactionVersion=A->ReactionVersion;
            Transition.bTransition=true;
        }
        if(A->bDeathHandoffSample)Transition.bSnap=true;
        Ground.Prepare(Cast<ACharacter>(Instance->TryGetPawnOwner()),Dt);
    }
};
void URootCrownAnimInstance::NativeInitializeAnimation()
{
    Super::NativeInitializeAnimation();bHaveTransform=false;
    Phase=IdleTime=Activity=TurnWeight=0.f;RightWeight=.5f;
    SlashTime=SlashBlend=0.f;PreviousSlashSerial=0;
    ReactionTime=0.f;ReactionVersion=0;bReaction=bLoopReaction=bDeathHandoffSample=false;
}
void URootCrownAnimInstance::NativeUpdateAnimation(float Dt)
{
    Super::NativeUpdateAnimation(Dt);
    const auto* Crown=Cast<ARootCrownRigPreview>(TryGetPawnOwner());
    if (!Crown) return;
    Idle=Crown->IdleClip;Move=Crown->MoveClip;Left=Crown->TurnLeftClip;Right=Crown->TurnRightClip;
    Slash=Crown->CurrentAttackClip();
    Reaction=Crown->ReactionClip(ReactionTime,bLoopReaction);
    bReaction=Crown->ReactionPhase()!=ERootCrownReaction::None&&Reaction;
    ReactionVersion=Crown->ReactionSerial();
    bDeathHandoffSample=Crown->SamplingDeathHandoff();
    if(Crown->SlashSerial()!=PreviousSlashSerial){PreviousSlashSerial=Crown->SlashSerial();SlashTime=0.f;}
    if(Crown->IsAttacking() && Slash)SlashTime=FMath::Min(Crown->SlashAge(),Slash->GetPlayLength());
    // Zero-delta evaluation is used to capture the exact soft-corpse handoff pose.
    if(Dt<=SMALL_NUMBER)return;
    // Interrupted attacks hold the sampled pose during the short fade.
    SlashBlend=FMath::FInterpConstantTo(SlashBlend,Crown->IsAttacking()&&Slash?1.f:0.f,Dt,8.f);
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
    Activity=FMath::FInterpConstantTo(Activity,Active?1.f:0.f,Dt,6.f);
    if (Cycles>SMALL_NUMBER)
    {
        TurnWeight=AngularCycles/Cycles;
        // UE positive yaw is a right turn; source Blender positive Z is left.
        if (FMath::Abs(Angle)>.001f) RightWeight=FMath::FInterpConstantTo(RightWeight,Angle>0?1.f:0.f,Dt,10.f);
    }
    // Idle breathing pauses while walking/turning; the locomotion phase never resets.
    if (!Active && !Crown->Busy() && Idle) IdleTime=FMath::Fmod(IdleTime+Dt,Idle->GetPlayLength());
}
FAnimInstanceProxy* URootCrownAnimInstance::CreateAnimInstanceProxy(){return new FRootCrownAnimProxy(this);}
void URootCrownAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy){delete Proxy;}
