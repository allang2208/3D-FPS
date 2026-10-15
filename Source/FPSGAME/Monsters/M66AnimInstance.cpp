#include "M66AnimInstance.h"
#include "M66IncineratorMonster.h"
#include "MonsterSurfaceGroundingNode.h"
#include "M66LifeMotionNode.h"
#include "M66DrapeMotionNode.h"
#include "M66RecoveryGroundNode.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/GameStateBase.h"
#include "Engine/World.h"

// This graph is owned by a native proxy, without UAnimBlueprint NodeData.
// FAnimNode_Inertialization evaluates GetNodeIndex() even during initial pose
// evaluation. Keep the transition local to this graph instead of fabricating
// blueprint metadata or disabling engine assertions/tracing.
struct FM66PoseTransition : FAnimNode_Base
{
    FPoseLink Source;
    TArray<FTransform> LastPose,OutgoingPose;
    float BlendAge=.14f;
    bool bTransition=false,bSnap=false;
    bool bHold=false;
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
        if(bHold&&LastPose.Num()==Count)
        {
            // Reaction and corpse packets can arrive on different frames.
            // Keep the last pre-grounding live pose until the server body takes
            // over instead of briefly blending back to standing death frame 0.
            for(int32 I=0;I<Count;++I)Output.Pose[FCompactPoseBoneIndex(I)]=LastPose[I];
            OutgoingPose.Reset();BlendAge=.14f;bTransition=bSnap=false;
            return;
        }
        if(bSnap)
        {
            // Death hands the exact authored pose to the corpse, including
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
struct FM66AnimProxy : FAnimInstanceProxy
{
    FAnimNode_SequenceEvaluator_Standalone Idle,Move,Left,Right,React;
    FAnimNode_TwoWayBlend Turn,Travel,Rest,Action;
    FM66PoseTransition Transition;
    FM66LifeMotionNode Life;
    uint32 ReactionVersion=0;
    uint32 AttackVersion=0;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FMonsterSurfaceGroundingNode Ground;
    FM66RecoveryGroundNode RecoveryGround;
    FM66DrapeMotionNode Drape;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;
    explicit FM66AnimProxy(UAnimInstance* Instance):FAnimInstanceProxy(Instance),Ground(Instance)
    {
        Turn.A.SetLinkNode(&Left);Turn.B.SetLinkNode(&Right);
        Travel.A.SetLinkNode(&Move);Travel.B.SetLinkNode(&Turn);
        Rest.A.SetLinkNode(&Idle);Rest.B.SetLinkNode(&Travel);
        Action.A.SetLinkNode(&Rest);Action.B.SetLinkNode(&React);
        Transition.Source.SetLinkNode(&Action);Life.Source.SetLinkNode(&Transition);
        ToComponent.LocalPose.SetLinkNode(&Life);RecoveryGround.ComponentPose.SetLinkNode(&ToComponent);
        Ground.ComponentPose.SetLinkNode(&RecoveryGround);
        Drape.ComponentPose.SetLinkNode(&Ground);ToLocal.ComponentPose.SetLinkNode(&Drape);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override{return &ToLocal;}
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& Nodes) override
    {Nodes.Append({&Idle,&Move,&Left,&Right,&React,&Turn,&Travel,&Rest,&Action,&Transition,&Life,&ToComponent,&RecoveryGround,&Ground,&Drape,&ToLocal});}
    virtual void PreUpdate(UAnimInstance* Instance,float Dt) override
    {
        FAnimInstanceProxy::PreUpdate(Instance,Dt);const auto* Anim=CastChecked<UM66AnimInstance>(Instance);
        auto Sample=[](FAnimNode_SequenceEvaluator_Standalone& Node,UAnimSequence* Clip,float Seconds)
        {Node.SetSequence(Clip);Node.SetShouldLoop(true);Node.SetTeleportToExplicitTime(true);Node.SetExplicitTime(Seconds);};
        Sample(Idle,Anim->Idle,Anim->IdleTime);
        Sample(Move,Anim->Move,Anim->Move?Anim->Phase*Anim->Move->GetPlayLength():0);
        Sample(Left,Anim->Left,Anim->Left?Anim->Phase*Anim->Left->GetPlayLength():0);
        Sample(Right,Anim->Right,Anim->Right?Anim->Phase*Anim->Right->GetPlayLength():0);
        Turn.Alpha=Anim->RightWeight;Travel.Alpha=Anim->TurnWeight;Rest.Alpha=Anim->Activity;
        Life.Seconds=Anim->LifeSeconds;Life.Alpha=Anim->LifeWeight;Life.Movement=Anim->Activity;
        Sample(React,Anim->Reaction,Anim->ReactionTime);React.SetShouldLoop(Anim->bLoopReaction);
        Action.Alpha=Anim->bReaction?1.f:0.f;
        Transition.bHold=Anim->bHoldKnockdownDeath;
        if(ReactionVersion!=Anim->ReactionVersion||AttackVersion!=Anim->AttackVersion)
        {ReactionVersion=Anim->ReactionVersion;AttackVersion=Anim->AttackVersion;Transition.bTransition=true;}
        Ground.Prepare(Cast<ACharacter>(Instance->TryGetPawnOwner()),Dt);
        RecoveryGround.Prepare(Cast<AM66IncineratorMonster>(Instance->TryGetPawnOwner()),Dt);
        Drape.Prepare(Cast<AM66IncineratorMonster>(Instance->TryGetPawnOwner()),Dt);
    }
};
void UM66AnimInstance::NativeInitializeAnimation()
{
    Super::NativeInitializeAnimation();bHaveTransform=false;Phase=IdleTime=Activity=TurnWeight=0;RightWeight=.5f;
    SupportCentreLocal=FVector::ZeroVector;
    LifeWeight=0.f;
    if(const auto* Mesh=GetSkelMeshComponent();Mesh&&Mesh->GetSkeletalMeshAsset())
    {
        const auto& Ref=Mesh->GetSkeletalMeshAsset()->GetRefSkeleton();auto Bind=Ref.GetRefBonePose();int32 Found=0;
        for(int32 I=0;I<Bind.Num();++I)if(Ref.GetParentIndex(I)!=INDEX_NONE)Bind[I]*=Bind[Ref.GetParentIndex(I)];
        for(FName Name:{FName(TEXT("Bone_010")),FName(TEXT("Bone_015"))})
            if(const int32 I=Ref.FindBoneIndex(Name);I!=INDEX_NONE){SupportCentreLocal+=Bind[I].GetLocation();++Found;}
        if(Found)SupportCentreLocal/=Found;
    }
}
void UM66AnimInstance::NativeUpdateAnimation(float Dt)
{
    Super::NativeUpdateAnimation(Dt);const auto* Owner=Cast<AM66IncineratorMonster>(TryGetPawnOwner());
    if(!Owner)return;
    Reaction=Owner->ReactionClip(ReactionTime,bLoopReaction);
    if(!Reaction&&Owner->IsSweeping())
    {Reaction=Owner->ActiveAttackClip();ReactionTime=Owner->SweepAge();bLoopReaction=false;}
    bReaction=Reaction!=nullptr;AttackVersion=Owner->SweepSerial();
    ReactionVersion=Owner->ReactionSerial();
    bHoldKnockdownDeath=Owner->HoldKnockdownDeathPose();
    if(const auto* World=Owner->GetWorld())
    {const auto* State=World->GetGameState();LifeSeconds=State?State->GetServerWorldTimeSeconds():World->GetTimeSeconds();}
    if(Owner->Dead()||Owner->IsKnockedDown())LifeWeight=0.f;
    else LifeWeight=FMath::FInterpConstantTo(LifeWeight,Owner->Busy()?0.f:1.f,FMath::Max(0.f,Dt),7.f);
    if(Dt<=SMALL_NUMBER)return;
    Idle=Owner->IdleClip;Move=Owner->MoveClip;Left=Owner->TurnLeftClip;Right=Owner->TurnRightClip;
    const auto* Mesh=GetSkelMeshComponent();
    // The imported origin is off-centre. Measure the support centre so a pivot
    // does not count the mesh-origin orbit as forward travel; retain net smoothing.
    const FVector Position=Mesh->GetComponentTransform().TransformPosition(SupportCentreLocal);
    const float Yaw=Mesh->GetComponentRotation().Yaw;float Distance=0,Angle=0;
    if(bHaveTransform&&FVector::DistSquared(Position,PreviousLocation)<FMath::Square(250.f))
    {Distance=FVector::Dist2D(Position,PreviousLocation);Angle=FMath::FindDeltaAngleDegrees(PreviousYaw,Yaw);}
    PreviousLocation=Position;PreviousYaw=Yaw;bHaveTransform=true;
    if(Owner->Busy()||!Owner->GetCharacterMovement()->IsMovingOnGround())Distance=Angle=0;
    const float Linear=Distance/FMath::Max(1.f,Owner->StrideDistance),Angular=FMath::Abs(Angle)/FMath::Max(1.f,Owner->TurnStrideDegrees);
    Phase=FMath::Fmod(Phase+Linear+Angular,1.f);
    const bool Active=Distance/Dt>1.f||FMath::Abs(Angle)/Dt>1.f;
    Activity=FMath::FInterpConstantTo(Activity,Active?1.f:0.f,Dt,5.f);
    if(Linear+Angular>SMALL_NUMBER)
    {
        TurnWeight=Angular/(Linear+Angular);
        if(FMath::Abs(Angle)>.001f)RightWeight=FMath::FInterpConstantTo(RightWeight,Angle>0?1.f:0.f,Dt,8.f);
    }
    if(Idle&&Idle->GetPlayLength()>0)IdleTime=FMath::Fmod(IdleTime+Dt,Idle->GetPlayLength());
}
FAnimInstanceProxy* UM66AnimInstance::CreateAnimInstanceProxy(){return new FM66AnimProxy(this);}
void UM66AnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy){delete Proxy;}
