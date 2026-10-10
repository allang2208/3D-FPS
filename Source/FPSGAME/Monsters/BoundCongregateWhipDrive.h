#pragma once
#include "BoundCongregate.h"
#include "BoundCongregateTentacleTiming.h"
#include "Animation/AnimInstanceProxy.h"
#include "Animation/PoseSnapshot.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
#include "Components/SkeletalMeshComponent.h"

/** One attack clock drives the muscular base and the body's counterweight. */
struct FCongregateWhipDriveState
{
    bool Active=false,WasRecovering=false;
    float RootPitch=0,RootYaw=0,BodyPitch=0,BodyShift=0,BodyDrop=0;
    float ReleasedRootPitch=0,ReleasedRootYaw=0,ReleasedBodyPitch=0,ReleasedBodyShift=0,ReleasedBodyDrop=0;
    FVector Forward=FVector::ForwardVector,Right=FVector::RightVector;
    void Prepare(const ABoundCongregate* M)
    {
        Active=M->TentacleActive()&&!M->Dead();
        if(!Active){RootPitch=RootYaw=BodyPitch=BodyShift=BodyDrop=0;WasRecovering=false;return;}
        const auto& Frame=M->GetMesh()->GetComponentTransform();
        Forward=Frame.InverseTransformVectorNoScale(M->GetActorForwardVector()).GetSafeNormal();
        Right=Frame.InverseTransformVectorNoScale(M->GetActorRightVector()).GetSafeNormal();
        const auto State=M->NetState.State;const float T=float(M->StateElapsed());
        if(M->TentacleRecovering())
        {
            if(!WasRecovering)
            {ReleasedRootPitch=RootPitch;ReleasedRootYaw=RootYaw;ReleasedBodyPitch=BodyPitch;ReleasedBodyShift=BodyShift;ReleasedBodyDrop=BodyDrop;}
            const float RecoveryTime=float(M->TentacleRecoveryElapsed());
            const float U=FMath::Clamp(RecoveryTime/FMath::Max(.001f,M->TentacleRecoverSeconds),0.f,1.f);
            const float Fade=1.f-BoundCongregateTentacleTiming::RecoveryPhase(RecoveryTime,M->TentacleRecoverSeconds);
            // A single restrained opposite recoil; the endpoint still returns
            // exactly to the locomotion pose with no held final frame.
            const float Rebound=-7.f*FMath::Sin(2.f*PI*U)*FMath::Sin(PI*U)*Fade;
            RootPitch=ReleasedRootPitch*Fade+Rebound;RootYaw=ReleasedRootYaw*Fade;
            BodyPitch=ReleasedBodyPitch*Fade;BodyShift=ReleasedBodyShift*Fade;BodyDrop=ReleasedBodyDrop*Fade;
            WasRecovering=true;return;
        }
        WasRecovering=false;
        if(State==EBoundCongregateState::TentacleWindup)
        {
            const float U=FMath::Clamp(T/FMath::Max(.001f,M->TentacleWindupSeconds),0.f,1.f);
            const float Load=U*U*(2.f-U);
            RootPitch=-38.f*Load;RootYaw=12.f*Load;
            BodyPitch=-6.f*Load;BodyShift=-8.f*Load;BodyDrop=-5.f*Load;
        }
        else if(State==EBoundCongregateState::TentacleStrike)
        {
            const float U=FMath::Clamp(T/FMath::Max(.001f,M->TentacleReleaseDuration()),0.f,1.f);
            // The thick base leads the distal whip: maximum torque is reached
            // during the first half, followed by braking while the tip overtakes.
            const float Drive=FMath::SmoothStep(0.f,.48f,U),Brake=FMath::SmoothStep(.48f,1.f,U);
            RootPitch=FMath::Lerp(-38.f,52.f,Drive)-34.f*Brake;
            RootYaw=FMath::Lerp(12.f,-10.f,Drive)+10.f*Brake;
            BodyPitch=FMath::Lerp(-6.f,8.f,Drive)-6.f*Brake;
            BodyShift=FMath::Lerp(-8.f,14.f,Drive)-11.f*Brake;BodyDrop=-5.f-3.f*FMath::Sin(PI*U);
        }
        else
        {
            // Capture may interrupt the throw before its last frame. Ease the
            // existing driver into the held pose rather than resetting its base.
            const float Follow=FMath::SmoothStep(0.f,.12f,T);
            RootPitch=FMath::Lerp(RootPitch,18.f,Follow);RootYaw=FMath::Lerp(RootYaw,0.f,Follow);
            BodyPitch=FMath::Lerp(BodyPitch,2.f,Follow);BodyShift=FMath::Lerp(BodyShift,3.f,Follow);BodyDrop=FMath::Lerp(BodyDrop,-5.f,Follow);
        }
    }
};

/** Move the torso before the existing foot IK, which retains raw foot goals. */
struct FCongregateWhipBody : FAnimNode_SkeletalControlBase
{
    FCongregateWhipDriveState* Drive=nullptr;
    FBoneReference Body;
    FPoseSnapshot UncorrectedPose;
    TArray<FTransform> RawComponentPose;
    TArray<FCompactPoseBoneIndex> Descendants;
    FCongregateWhipBody(){Alpha=1.f;Body.BoneName=TEXT("body");}
    virtual void InitializeBoneReferences(const FBoneContainer& C) override
    {
        Body.Initialize(C);const auto& Ref=C.GetReferenceSkeleton();
        UncorrectedPose.LocalTransforms=Ref.GetRefBonePose();UncorrectedPose.BoneNames.SetNum(Ref.GetNum());
        for(int32 I=0;I<Ref.GetNum();++I)UncorrectedPose.BoneNames[I]=Ref.GetBoneName(I);
        UncorrectedPose.bIsValid=false;RawComponentPose.SetNum(C.GetCompactPoseNumBones());Descendants.Reset();
        if(!Body.IsValidToEvaluate(C))return;
        const auto Root=Body.GetCompactPoseIndex(C);
        for(int32 I=0;I<C.GetCompactPoseNumBones();++I)
            for(auto P=FCompactPoseBoneIndex(I);P!=INDEX_NONE;P=C.GetParentBoneIndex(P))
                if(P==Root){Descendants.Add(FCompactPoseBoneIndex(I));break;}
    }
    virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer& C) override{return Body.IsValidToEvaluate(C);}
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out) override
    {
        const auto& C=Output.Pose.GetPose().GetBoneContainer();
        for(const FCompactPoseBoneIndex I:Output.Pose.GetPose().ForEachBoneIndex())
        {
            UncorrectedPose.LocalTransforms[C.MakeMeshPoseIndex(I).GetInt()]=Output.Pose.GetLocalSpaceTransform(I);
            RawComponentPose[I.GetInt()]=Output.Pose.GetComponentSpaceTransform(I);
        }
        UncorrectedPose.bIsValid=true;
        if(!Drive||!Drive->Active)return;
        const FVector Pivot=RawComponentPose[Body.GetCompactPoseIndex(C).GetInt()].GetLocation();
        const FQuat R(Drive->Right,FMath::DegreesToRadians(Drive->BodyPitch));
        const FVector Shift=Drive->Forward*Drive->BodyShift+FVector::UpVector*Drive->BodyDrop;
        for(const auto I:Descendants)
        {
            FTransform T=RawComponentPose[I.GetInt()];T.SetLocation(Pivot+R.RotateVector(T.GetLocation()-Pivot)+Shift);
            T.SetRotation((R*T.GetRotation()).GetNormalized());Out.Emplace(I,T);
        }
    }
};

/** Bend the formerly fixed thick stem, carrying the entire curled organ. */
struct FCongregateWhipStem : FAnimNode_SkeletalControlBase
{
    static constexpr int32 Count=57,EndOfStem=8;
    FCongregateWhipDriveState* Drive=nullptr;
    FBoneReference Bones[Count];
    FCongregateWhipStem()
    {Alpha=1.f;for(int32 I=0;I<Count;++I)Bones[I].BoneName=FName(FString::Printf(TEXT("attack_tentacle_%02d"),I));}
    virtual void InitializeBoneReferences(const FBoneContainer& C) override{for(auto& B:Bones)B.Initialize(C);}
    virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer& C) override
    {for(const auto& B:Bones)if(!B.IsValidToEvaluate(C))return false;return true;}
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out) override
    {
        if(!Drive||!Drive->Active)return;
        const auto& C=Output.Pose.GetPose().GetBoneContainer();
        FTransform Original[Count];FVector Goals[Count];
        for(int32 I=0;I<Count;++I)Original[I]=Output.Pose.GetComponentSpaceTransform(Bones[I].GetCompactPoseIndex(C));
        Goals[0]=Original[0].GetLocation();Goals[1]=Original[1].GetLocation();
        for(int32 I=2;I<Count;++I)
        {
            const float Across=FMath::SmoothStep(0.f,float(EndOfStem-1),float(I-1));
            const FQuat R=FQuat(FVector::UpVector,FMath::DegreesToRadians(Drive->RootYaw*Across))*
                FQuat(Drive->Right,FMath::DegreesToRadians(Drive->RootPitch*Across));
            Goals[I]=Goals[I-1]+R.RotateVector(Original[I].GetLocation()-Original[I-1].GetLocation());
        }
        FQuat Transport=FQuat::Identity;
        for(int32 I=1;I<Count;++I)
        {
            const int32 A=I==Count-1?I-1:I,B=A+1;
            const FVector Before=(Original[B].GetLocation()-Original[A].GetLocation()).GetSafeNormal();
            const FVector After=(Goals[B]-Goals[A]).GetSafeNormal();
            Transport=(FQuat::FindBetweenNormals(Transport.RotateVector(Before),After)*Transport).GetNormalized();
            FTransform T=Original[I];T.SetLocation(Goals[I]);T.SetRotation((Transport*T.GetRotation()).GetNormalized());
            Out.Emplace(Bones[I].GetCompactPoseIndex(C),T);
        }
    }
};
