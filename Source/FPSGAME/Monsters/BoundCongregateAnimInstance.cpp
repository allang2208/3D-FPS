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
#include "MonsterGroundSupport.h"

namespace
{
struct FCongregateFeet : FAnimNode_SkeletalControlBase
{
    struct FLeg
    {
        FBoneReference Upper,Lower,Foot,Body;
        FVector Pole=FVector::UpVector,Lock=FVector::ZeroVector,Correction=FVector::ZeroVector;
        FVector GroundPoint=FVector::ZeroVector,GroundNormal=FVector::UpVector,Normal=FVector::UpVector,SoleLocal=FVector::ZeroVector;
        float Ground=0,Offset=0,LastPhase=1,Sole=12;
        bool bGround=false,bLocked=false,bReleased=false;
    };
    FLeg Legs[10];FTransform Frame;FPoseSnapshot UncorrectedPose;
    FCongregateWhipBody* BodyDrive=nullptr;
    float Phase=0,TraceAge=1,Dt=0;
    float BodyHeight=0,WantedHeight=0,MinimumHeight=-70,Compression=0;
    FQuat BodyTilt=FQuat::Identity,WantedTilt=FQuat::Identity;
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
            L.SoleLocal=Ref(L.Foot.GetCompactPoseIndex(Bones)).InverseTransformPosition(FVector(F.X,F.Y,0));
        }
    }
    virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer& B) override
    {for(const auto& L:Legs)if(!L.Upper.IsValidToEvaluate(B)||!L.Lower.IsValidToEvaluate(B)||!L.Foot.IsValidToEvaluate(B)||!L.Body.IsValidToEvaluate(B))return false;return true;}
    void Prepare(const ABoundCongregate* M,float P,bool W,float Delta)
    {
        Dt=FMath::Clamp(Delta,0.f,.1f);Serial=GFrameCounter;Phase=P;Walking=W;Attack=M->Busy();
        GroundSlap=M->NetState.State==EBoundCongregateState::Flurry;
        AuthoredMelee=M->NetState.State==EBoundCongregateState::Bite||GroundSlap;
        const bool WasEnabled=Enabled;
        Enabled=!M->Dead()&&M->GetCharacterMovement()->IsMovingOnGround()&&!M->GetMesh()->IsSimulatingPhysics();
        const FTransform Next=M->GetMesh()->GetComponentTransform();
        const bool Reset=!WasEnabled||FVector::DistSquared(Next.GetLocation(),Frame.GetLocation())>FMath::Square(120.);
        Frame=Next;
        if(!Enabled||Dt<=0)return;
        if(Reset){TraceAge=1;Compression=0;for(auto& L:Legs){L.bLocked=false;L.bReleased=false;L.Correction=FVector::ZeroVector;}}
        TraceAge+=Dt;
        if(TraceAge>=MonsterGroundSupport::QueryInterval(M->GetMesh(),1.f/15.f))
        {
            TraceAge=0;
            FMonsterGroundProbe Probe(M);
            const float Base=Frame.GetLocation().Z;
            auto Trace=[&](FVector At,FHitResult& Hit)
            {return Probe.Trace(M->GetWorld(),FVector(At.X,At.Y,Base+110),FVector(At.X,At.Y,Base-160),FVector::UpVector,M->GetCharacterMovement()->GetWalkableFloorZ(),Hit);};
            TArray<FVector,TInlineAllocator<10>> Points;
            for(auto& L:Legs)
            {
                const FVector At=M->GetMesh()->GetSocketLocation(L.Foot.BoneName);FHitResult Hit;
                L.bGround=false;double Best=-TNumericLimits<double>::Max();
                for(float Offset:{-6.f,6.f})
                {
                    FHitResult Candidate;if(!Trace(At+M->GetActorForwardVector()*Offset,Candidate))continue;
                    const FVector N=Candidate.ImpactNormal,D=At-Candidate.ImpactPoint;
                    const double Height=Candidate.ImpactPoint.Z-(N.X*D.X+N.Y*D.Y)/N.Z;
                    if(Height>Best){Best=Height;Hit=Candidate;L.bGround=true;}
                }
                if(L.bGround){L.Ground=Best;L.GroundPoint=Hit.ImpactPoint;L.GroundNormal=Hit.ImpactNormal;Points.Add(FVector(At.X,At.Y,Best));}
            }
            MonsterGroundSupport::FitPlane(Points,Frame.GetLocation(),22.f,WantedHeight,WantedTilt);
            MinimumHeight=-70.f;
            for(FName Name:{FName(TEXT("body_front")),FName(TEXT("body")),FName(TEXT("body_rear"))})
            {
                const FVector Body=M->GetMesh()->GetSocketLocation(Name),At(Body.X,Body.Y,Base);FHitResult Hit;
                if(Trace(At,Hit))
                {
                    const FVector Rotated=Frame.GetLocation()+WantedTilt.RotateVector(At-Frame.GetLocation());
                    MinimumHeight=FMath::Max(MinimumHeight,float(Hit.ImpactPoint.Z-Rotated.Z-18.f));
                }
            }
            WantedHeight=FMath::Clamp(FMath::Max(WantedHeight,MinimumHeight),-70.f,60.f);
        }
        const float Blend=Reset?1.f:1.f-FMath::Exp(-10.f*Dt);
        BodyHeight=FMath::Lerp(BodyHeight,WantedHeight,Blend);BodyTilt=FQuat::Slerp(BodyTilt,WantedTilt,Blend).GetNormalized();
    }
    FTransform Grounded(const FTransform& T,float Drop=0.f) const
    {
        FTransform R=T;
        R.SetLocation(Frame.InverseTransformPosition(Frame.GetLocation()+BodyTilt.RotateVector(Frame.TransformPosition(T.GetLocation())-Frame.GetLocation())+FVector(0,0,BodyHeight+Drop)));
        R.SetRotation((Frame.GetRotation().Inverse()*BodyTilt*Frame.GetRotation()*T.GetRotation()).GetNormalized());
        return R;
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
        float WantedCompression=0.f;
        for(const auto& L:Legs)if(L.bGround)
        {
            const auto F=L.Foot.GetCompactPoseIndex(B);
            const FTransform Raw=BodyDrive&&BodyDrive->Drive&&BodyDrive->Drive->Active&&BodyDrive->RawComponentPose.IsValidIndex(F.GetInt())?
                BodyDrive->RawComponentPose[F.GetInt()]:Output.Pose.GetComponentSpaceTransform(F);
            const FVector Goal=Frame.TransformPosition(Raw.GetLocation());
            if(Goal.Z-Frame.GetLocation().Z-L.Sole*Frame.GetScale3D().Z>5.f)continue;
            const FVector U=Frame.TransformPosition(Grounded(Output.Pose.GetComponentSpaceTransform(L.Upper.GetCompactPoseIndex(B))).GetLocation());
            const FVector K=Frame.TransformPosition(Grounded(Output.Pose.GetComponentSpaceTransform(L.Lower.GetCompactPoseIndex(B))).GetLocation());
            const FVector E=Frame.TransformPosition(Grounded(Output.Pose.GetComponentSpaceTransform(F)).GetLocation());
            const double Reach=(FVector::Distance(U,K)+FVector::Distance(K,E))*.98;
            const double Vertical=Reach*Reach-FVector::DistSquared2D(U,Goal);
            if(Vertical>0.)WantedCompression=FMath::Min(WantedCompression,float(L.Ground+L.Sole*Frame.GetScale3D().Z+FMath::Sqrt(Vertical)-U.Z));
        }
        WantedCompression=FMath::Max(FMath::Clamp(WantedCompression,-25.f,0.f),FMath::Min(0.f,MinimumHeight-BodyHeight));
        if(NewFrame)Compression=FMath::FInterpConstantTo(Compression,WantedCompression,Dt,120.f);
        Out.Emplace(FCompactPoseBoneIndex(0),Grounded(Output.Pose.GetComponentSpaceTransform(FCompactPoseBoneIndex(0)),Compression));
        for(auto& L:Legs)
        {
            const auto U=L.Upper.GetCompactPoseIndex(B),K=L.Lower.GetCompactPoseIndex(B),F=L.Foot.GetCompactPoseIndex(B);
            const FTransform RawFoot=Output.Pose.GetComponentSpaceTransform(F);
            FTransform Upper=Grounded(Output.Pose.GetComponentSpaceTransform(U),Compression),Lower=Grounded(Output.Pose.GetComponentSpaceTransform(K),Compression),Foot=Grounded(RawFoot,Compression);
            const auto Body=Grounded(Output.Pose.GetComponentSpaceTransform(L.Body.GetCompactPoseIndex(B)),Compression);
            const FTransform FootGoal=BodyDrive&&BodyDrive->Drive&&BodyDrive->Drive->Active&&BodyDrive->RawComponentPose.IsValidIndex(F.GetInt())?
                BodyDrive->RawComponentPose[F.GetInt()]:RawFoot;
            if(NewFrame)L.Normal=FMath::Lerp(L.Normal,L.bGround?L.GroundNormal:FVector::UpVector,1.f-FMath::Exp(-12.f*Dt)).GetSafeNormal();
            const FQuat FootRotation=(Frame.GetRotation().Inverse()*FQuat::FindBetweenNormals(FVector::UpVector,L.Normal)*Frame.GetRotation()*FootGoal.GetRotation()).GetNormalized();
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
                const float Lift=FMath::Max(0.f,float(Goal.Z-Frame.GetLocation().Z)-L.Sole*float(Frame.GetScale3D().Z));
                // The ground-slap clip includes the palm thickness and lift.
                // Preserve it while translating to terrain; clamping to the
                // standing wrist height would undo the ground-slap contact.
                const FTransform WorldFoot(Frame.GetRotation()*FootRotation,Goal,FootGoal.GetScale3D()*Frame.GetScale3D());
                const float Gap=FVector::DotProduct(WorldFoot.TransformPosition(L.SoleLocal)-L.GroundPoint,L.Normal);
                DesiredCorrection.Z=GroundSlap?L.Ground-Frame.GetLocation().Z:(.5f-Gap)/FMath::Max(.1f,float(L.Normal.Z))+Lift;
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
            if(AuthoredMelee&&L.Correction.IsNearlyZero(.01f)&&FMath::Abs(BodyHeight+Compression)<.01f&&BodyTilt.IsIdentity(.0001f))continue;
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
            AnimationCore::SolveTwoBoneIK(Upper,Lower,Foot,Pole,End,false,1.,1.);Foot.SetRotation(FootRotation);
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
