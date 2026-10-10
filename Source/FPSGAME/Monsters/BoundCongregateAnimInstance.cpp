#include "BoundCongregateAnimInstance.h"
#include "BoundCongregate.h"
#include "BoundCongregateGait.h"
#include "BoundCongregateTentacleControl.h"
#include "BoundCongregateSecondaryMotion.h"
#include "BoundCongregateWhipDrive.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Animation/AnimNodeSpaceConversions.h"
#include "AnimNodes/AnimNode_PoseSnapshot.h"
#include "AnimNodes/AnimNode_SequenceEvaluator.h"
#include "AnimNodes/AnimNode_TwoWayBlend.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "TwoBoneIK.h"

namespace
{
struct FCongregateFeet : FAnimNode_SkeletalControlBase
{
    struct FLeg
    {
        FBoneReference Upper,Lower,Foot,Body;
        FVector Pole=FVector::UpVector,Lock=FVector::ZeroVector,Correction=FVector::ZeroVector;
        float Ground=0,Offset=0,LastPhase=1,Sole=12;
        bool bGround=false,bLocked=false,bReleased=false;
    };
    FLeg Legs[10];FTransform Frame;FPoseSnapshot UncorrectedPose;
    FCongregateWhipBody* BodyDrive=nullptr;
    float Phase=0,TraceAge=1,Dt=0;
    bool Enabled=false,Walking=false,Attack=false,AuthoredMelee=false,GroundSlap=false;
    uint64 Serial=0,Evaluated=0;
    FCongregateFeet()
    {
        Alpha=1;
        for(int32 I=0;I<10;++I)
        {
            auto& L=Legs[I];const FString Stem=FString::Printf(TEXT("leg_%s%d_"),I<5?TEXT("L"):TEXT("R"),I%5+1);
            L.Upper.BoneName=FName(Stem+TEXT("upper"));L.Lower.BoneName=FName(Stem+TEXT("lower"));L.Foot.BoneName=FName(Stem+TEXT("foot"));
            L.Body.BoneName=I%5<2?TEXT("body_front"):TEXT("body_rear");L.Offset=BoundCongregateGait::PhaseOffsets[I];
        }
    }
    virtual void InitializeBoneReferences(const FBoneContainer& Bones) override
    {
        const auto& Reference=Bones.GetReferenceSkeleton();
        UncorrectedPose.LocalTransforms=Reference.GetRefBonePose();
        UncorrectedPose.BoneNames.SetNum(Reference.GetNum());
        for(int32 I=0;I<Reference.GetNum();++I)UncorrectedPose.BoneNames[I]=Reference.GetBoneName(I);
        UncorrectedPose.bIsValid=false;
        auto Ref=[&](FCompactPoseBoneIndex I)
        {FTransform T=Bones.GetRefPoseTransform(I);for(auto P=Bones.GetParentBoneIndex(I);P!=INDEX_NONE;P=Bones.GetParentBoneIndex(P))T*=Bones.GetRefPoseTransform(P);return T;};
        for(auto& L:Legs)
        {
            L.Upper.Initialize(Bones);L.Lower.Initialize(Bones);L.Foot.Initialize(Bones);L.Body.Initialize(Bones);L.bLocked=false;L.bReleased=false;L.Correction=FVector::ZeroVector;
            if(!L.Foot.IsValidToEvaluate(Bones)||!L.Upper.IsValidToEvaluate(Bones)||!L.Lower.IsValidToEvaluate(Bones)||!L.Body.IsValidToEvaluate(Bones))continue;
            const FVector U=Ref(L.Upper.GetCompactPoseIndex(Bones)).GetLocation(),K=Ref(L.Lower.GetCompactPoseIndex(Bones)).GetLocation();
            const FVector F=Ref(L.Foot.GetCompactPoseIndex(Bones)).GetLocation(),D=(F-U).GetSafeNormal();
            L.Pole=Ref(L.Body.GetCompactPoseIndex(Bones)).InverseTransformVectorNoScale(((K-U)-D*FVector::DotProduct(K-U,D)).GetSafeNormal());
            L.Sole=FMath::Max(1.f,float(F.Z));
        }
    }
    virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer& B) override
    {for(const auto& L:Legs)if(!L.Upper.IsValidToEvaluate(B)||!L.Lower.IsValidToEvaluate(B)||!L.Foot.IsValidToEvaluate(B)||!L.Body.IsValidToEvaluate(B))return false;return true;}
    void Prepare(const ABoundCongregate* M,float P,bool W,float Delta)
    {
        Dt=FMath::Clamp(Delta,0.f,.1f);Serial=GFrameCounter;Phase=P;Walking=W;Attack=M->Busy();
        GroundSlap=M->NetState.State==EBoundCongregateState::Flurry;
        AuthoredMelee=M->NetState.State==EBoundCongregateState::Bite||GroundSlap;
        Enabled=!M->Dead()&&M->GetCharacterMovement()->IsMovingOnGround();Frame=M->GetMesh()->GetComponentTransform();
        if(!Enabled||Dt<=0)return;
        TraceAge+=Dt;if(TraceAge<1.f/15.f)return;TraceAge=0;
        FCollisionQueryParams Q(SCENE_QUERY_STAT(CongregateFeet),false,M);
        FCollisionObjectQueryParams Objects;Objects.AddObjectTypesToQuery(ECC_WorldStatic);Objects.AddObjectTypesToQuery(ECC_WorldDynamic);
        const float Base=Frame.GetLocation().Z;
        for(auto& L:Legs)
        {
            const FVector At=M->GetMesh()->GetSocketLocation(L.Foot.BoneName);FHitResult Hit;
            L.bGround=M->GetWorld()->LineTraceSingleByObjectType(Hit,FVector(At.X,At.Y,Base+100),FVector(At.X,At.Y,Base-140),Objects,Q)&&
                Hit.ImpactNormal.Z>=M->GetCharacterMovement()->GetWalkableFloorZ()&&Hit.GetComponent()&&Hit.GetComponent()->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block;
            if(L.bGround)L.Ground=Hit.ImpactPoint.Z;
        }
    }
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out) override
    {
        // An interrupted blend must resume before this control. The component
        // snapshot already contains IK and applying it again produces a pop.
        const auto& B=Output.Pose.GetPose().GetBoneContainer();
        for(const FCompactPoseBoneIndex I:Output.Pose.GetPose().ForEachBoneIndex())
            UncorrectedPose.LocalTransforms[B.MakeMeshPoseIndex(I).GetInt()]=Output.Pose.GetLocalSpaceTransform(I);
        UncorrectedPose.bIsValid=true;
        const bool NewFrame=Evaluated!=Serial;Evaluated=Serial;
        if(!Enabled){for(auto& L:Legs){L.bLocked=false;L.bReleased=false;L.Correction=FVector::ZeroVector;}return;}
        for(auto& L:Legs)
        {
            const auto U=L.Upper.GetCompactPoseIndex(B),K=L.Lower.GetCompactPoseIndex(B),F=L.Foot.GetCompactPoseIndex(B);
            FTransform Upper=Output.Pose.GetComponentSpaceTransform(U),Lower=Output.Pose.GetComponentSpaceTransform(K),Foot=Output.Pose.GetComponentSpaceTransform(F);
            const auto Body=Output.Pose.GetComponentSpaceTransform(L.Body.GetCompactPoseIndex(B));
            const FTransform FootGoal=BodyDrive&&BodyDrive->Drive&&BodyDrive->Drive->Active&&BodyDrive->RawComponentPose.IsValidIndex(F.GetInt())?
                BodyDrive->RawComponentPose[F.GetInt()]:Foot;
            FVector Goal=Frame.TransformPosition(FootGoal.GetLocation());const float P=FMath::Frac(Phase+L.Offset);
            const bool Stance=!Walking||P<BoundCongregateGait::Stance;
            const float Reach=FVector::Distance(Upper.GetLocation(),Lower.GetLocation())+FVector::Distance(Lower.GetLocation(),Foot.GetLocation());
            const bool Wrapped=NewFrame&&P<L.LastPhase;
            if(!Stance||Wrapped){L.bLocked=false;L.bReleased=false;}
            if(Attack||!L.bGround){L.bLocked=false;L.bReleased=true;}
            if(Stance&&!Attack&&L.bGround&&!L.bLocked&&!L.bReleased)
            {
                L.bLocked=true;L.Lock=Goal;
            }
            FVector DesiredCorrection=FVector::ZeroVector;
            if(L.bGround)
            {
                const float Lift=FMath::Max(0.f,float(Goal.Z-Frame.GetLocation().Z)-L.Sole);
                // The ground-slap clip includes the palm thickness and lift.
                // Preserve it while translating to terrain; clamping to the
                // standing wrist height would undo the ground-slap contact.
                DesiredCorrection.Z=GroundSlap?L.Ground-Frame.GetLocation().Z:L.Ground+L.Sole+Lift-Goal.Z;
            }
            if(L.bLocked)
            {
                const float LockDistance=FVector::Distance(Upper.GetLocation(),Frame.InverseTransformPosition(L.Lock));
                // Release once per support interval. Never reacquire every
                // frame at the reach limit or jump from Lock to the raw clip.
                if(LockDistance>Reach*.955f||FVector::DistSquared2D(Goal,L.Lock)>FMath::Square(18.f))
                {L.bLocked=false;L.bReleased=true;}
                else
                {
                    const float Fade=Walking?FMath::Clamp((BoundCongregateGait::Stance-P)/.10f,0.f,1.f):1.f;
                    const float Weight=Fade*Fade*(3.f-2.f*Fade);
                    const FVector Horizontal=FVector(L.Lock.X-Goal.X,L.Lock.Y-Goal.Y,0).GetClampedToMaxSize(16.f)*Weight;
                    DesiredCorrection.X=Horizontal.X;DesiredCorrection.Y=Horizontal.Y;
                }
            }
            // Bound correction speed in world space, including 15 Hz ground
            // sample changes and stance/turn transitions. No artificial 7 cm pop.
            if(NewFrame)
            {
                FVector Horizontal=FMath::VInterpConstantTo(FVector(L.Correction.X,L.Correction.Y,0),FVector(DesiredCorrection.X,DesiredCorrection.Y,0),Dt,90.f);
                L.Correction.X=Horizontal.X;L.Correction.Y=Horizontal.Y;
                L.Correction.Z=FMath::FInterpConstantTo(L.Correction.Z,DesiredCorrection.Z,Dt,140.f);
            }
            // Preserve the complete authored joint frames on level ground.
            // Re-solving an unchanged melee chain can only disturb its root
            // orientation; terrain correction still uses the existing solver.
            if(AuthoredMelee&&L.Correction.IsNearlyZero(.01f))continue;
            Goal+=L.Correction;
            FVector End=Frame.InverseTransformPosition(Goal),D=End-Upper.GetLocation();
            End=Upper.GetLocation()+D.GetSafeNormal()*FMath::Min(float(D.Size()),Reach*.98f);
            FVector Bend=Body.TransformVectorNoScale(L.Pole);
            if(AuthoredMelee)
            {
                // Preserve the baked attack elbow/knee plane. The standing
                // pole folds raised forelimbs back into the body, even with a
                // correct source clip. Terrain IK only adjusts their endpoint.
                const FVector Axis=(Foot.GetLocation()-Upper.GetLocation()).GetSafeNormal();
                const FVector Knee=Lower.GetLocation()-Upper.GetLocation();
                const FVector AuthoredBend=(Knee-Axis*FVector::DotProduct(Knee,Axis)).GetSafeNormal();
                if(!AuthoredBend.IsNearlyZero())Bend=AuthoredBend;
            }
            const FVector Pole=Upper.GetLocation()+Bend*Reach;
            const FQuat R=FootGoal.GetRotation();AnimationCore::SolveTwoBoneIK(Upper,Lower,Foot,Pole,End,false,1.,1.);Foot.SetRotation(R);
            Out.Emplace(U,Upper);Out.Emplace(K,Lower);Out.Emplace(F,Foot);L.LastPhase=P;
        }
        Out.Sort([](const FBoneTransform& A,const FBoneTransform& B){return A.BoneIndex.GetInt()<B.BoneIndex.GetInt();});
    }
};
struct FCongregateProxy : FAnimInstanceProxy
{
    FAnimNode_PoseSnapshot Previous;
    FAnimNode_SequenceEvaluator_Standalone Outgoing;
    FAnimNode_TwoWayBlend Source;
    FAnimNode_SequenceEvaluator_Standalone Current;
    FAnimNode_TwoWayBlend Blend;
    FAnimNode_ConvertLocalToComponentSpace ToComponent;
    FCongregateWhipDriveState DriveState;
    FCongregateWhipBody BodyDrive;
    FCongregateFeet Feet;
    FCongregateTentacleGround Ground;
    FCongregateSecondaryMotion Secondary;
    FCongregateWhipStem StemDrive;
    FCongregateTentacle Tentacle;
    FAnimNode_ConvertComponentToLocalSpace ToLocal;
    const UAnimSequence* LastClip=nullptr;
    float LastBlendAlpha=1.f;
    explicit FCongregateProxy(UAnimInstance* I):FAnimInstanceProxy(I)
    {
        Previous.Mode=ESnapshotSourceMode::SnapshotPin;
        Secondary.Ground=&Ground;Tentacle.Ground=&Ground;
        BodyDrive.Drive=&DriveState;StemDrive.Drive=&DriveState;Feet.BodyDrive=&BodyDrive;
        Source.A.SetLinkNode(&Previous);Source.B.SetLinkNode(&Outgoing);
        Blend.A.SetLinkNode(&Source);Blend.B.SetLinkNode(&Current);
        ToComponent.LocalPose.SetLinkNode(&Blend);BodyDrive.ComponentPose.SetLinkNode(&ToComponent);Feet.ComponentPose.SetLinkNode(&BodyDrive);
        Secondary.ComponentPose.SetLinkNode(&Feet);StemDrive.ComponentPose.SetLinkNode(&Secondary);Tentacle.ComponentPose.SetLinkNode(&StemDrive);ToLocal.ComponentPose.SetLinkNode(&Tentacle);
    }
    virtual FAnimNode_Base* GetCustomRootNode() override {return &ToLocal;}
    virtual void GetCustomNodes(TArray<FAnimNode_Base*>& N) override {N.Append({&Previous,&Outgoing,&Source,&Current,&Blend,&ToComponent,&BodyDrive,&Feet,&Secondary,&StemDrive,&Tentacle,&ToLocal});}
    virtual void PreUpdate(UAnimInstance* I,float Dt) override
    {
        FAnimInstanceProxy::PreUpdate(I,Dt);const auto* A=CastChecked<UBoundCongregateAnimInstance>(I);
        const auto* M=Cast<ABoundCongregate>(A->TryGetPawnOwner());if(!M)return;
        if(A->ActiveClip!=LastClip||A->BlendAlpha<LastBlendAlpha||!Previous.Snapshot.bIsValid)
        {
            Previous.Snapshot=!M->Dead()&&BodyDrive.UncorrectedPose.bIsValid?BodyDrive.UncorrectedPose:A->PreviousPose;
            // Keep the last visible grasp when a hit interrupts it. Only feet
            // need the pre-IK snapshot; the tentacle control follows that cache.
            if(!M->Dead()&&A->PreviousPose.bIsValid)
                for(int32 Bone=0;Bone<Previous.Snapshot.BoneNames.Num();++Bone)
                {
                    const FString Name=Previous.Snapshot.BoneNames[Bone].ToString();
                    if(!Name.StartsWith(TEXT("attack_tentacle_")))continue;
                    const int32 Index=A->PreviousPose.BoneNames.Find(Previous.Snapshot.BoneNames[Bone]);
                    if(A->PreviousPose.LocalTransforms.IsValidIndex(Index))Previous.Snapshot.LocalTransforms[Bone]=A->PreviousPose.LocalTransforms[Index];
                }
        }
        LastClip=A->ActiveClip;LastBlendAlpha=A->BlendAlpha;
        Feet.UncorrectedPose.SkeletalMeshName=M->GetMesh()->GetSkeletalMeshAsset()->GetFName();
        BodyDrive.UncorrectedPose.SkeletalMeshName=Feet.UncorrectedPose.SkeletalMeshName;
        Blend.Alpha=A->PreviousPose.bIsValid?A->BlendAlpha:1;
        Outgoing.SetSequence(A->OutgoingLoop);Outgoing.SetShouldLoop(true);
        Outgoing.SetTeleportToExplicitTime(true);Outgoing.SetExplicitTime(A->OutgoingLoopTime);
        Source.Alpha=A->OutgoingLoop?1.f:0.f;
        Current.SetSequence(A->ActiveClip);Current.SetShouldLoop(A->bLooping);Current.SetTeleportToExplicitTime(true);Current.SetExplicitTime(A->ClipTime);
        DriveState.Prepare(M);
        Feet.Prepare(M,A->GaitPhase,A->bGait,Dt);
        Ground.Prepare(M,Dt);
        Secondary.Prepare(M,A->GaitPhase,A->bGait,Dt);
        Tentacle.Prepare(M,Dt);
    }
};
}
void UBoundCongregateAnimInstance::NativeInitializeAnimation()
{
    Super::NativeInitializeAnimation();
    bHaveYaw=false;bGait=false;GaitPhase=0.f;
    // The proxy reads the active sequence before the first positive-delta
    // update. Seed it now so a spawned/reinitialized mesh never shows one
    // reference-pose frame before its authored idle support pose.
    if(const auto* M=Cast<ABoundCongregate>(TryGetPawnOwner());M&&M->IdleClip)
    {
        FMonsterClipTransition Settings;Settings.StartTime=0.f;
        TransitionTo(M->IdleClip,true,false,0.f,Settings);
        PreviousPose.Reset();OutgoingLoop=nullptr;
    }
}
void UBoundCongregateAnimInstance::NativeUpdateAnimation(float Dt)
{
    const auto* M=Cast<ABoundCongregate>(TryGetPawnOwner());
    if(M&&Dt>0)
    {
        const float Yaw=M->GetActorRotation().Yaw;
        const float YawRate=bHaveYaw?FMath::FindDeltaAngleDegrees(PreviousYaw,Yaw)/Dt:0;
        PreviousYaw=Yaw;bHaveYaw=true;
        if(!M->Busy())
        {
            const float Speed=M->GetVelocity().Size2D();
            const bool WasGait=ActiveClip&&(ActiveClip==M->MoveClip||ActiveClip==M->TurnLeftClip||ActiveClip==M->TurnRightClip);
            // Hysteresis prevents tiny navigation corrections from repeatedly
            // resetting the gait. Walk and turning clips share a contact phase.
            const bool Moving=Speed>(ActiveClip==M->MoveClip?1.f:3.f);
            const float TurnThreshold=WasGait?1.5f:3.f;
            const bool Turning=!Moving&&FMath::Abs(YawRate)>TurnThreshold;
            bGait=Moving||Turning;
            UAnimSequence* Clip=Moving?M->MoveClip.Get():Turning?(YawRate>0?M->TurnRightClip.Get():M->TurnLeftClip.Get()):M->IdleClip.Get();
            // Keep the authored 14 deg/s reference; allow the doubled yaw speed
            // to advance the same foot-contact phase without clipping its rate.
            const float Rate=Moving?Speed/FMath::Max(1.f,M->AnimationWalkSpeed):Turning?FMath::Clamp(FMath::Abs(YawRate)/BoundCongregateGait::TurnSpeed,.1f,10.f):1.f;
            if(Clip!=ActiveClip)
            {
                FMonsterClipTransition Settings;
                Settings.InitialPlayRate=Rate;
                Settings.bContinueOutgoingLoop=true;
                if(bGait&&Clip)Settings.StartTime=WasGait?GaitPhase*Clip->GetPlayLength():0.f;
                TransitionTo(Clip,true,false,.22f,Settings);
            }
            SetLocomotionRate(Rate);
        }
        else bGait=false;
    }
    Super::NativeUpdateAnimation(Dt);
    GaitPhase=ActiveClip?FMath::Frac(ClipTime/FMath::Max(.01f,ActiveClip->GetPlayLength())):0;
}
FAnimInstanceProxy* UBoundCongregateAnimInstance::CreateAnimInstanceProxy(){return new FCongregateProxy(this);}
void UBoundCongregateAnimInstance::DestroyAnimInstanceProxy(FAnimInstanceProxy* P){delete P;}
