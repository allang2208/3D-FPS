#pragma once
#include "BoundCongregate.h"
#include "Animation/AnimInstanceProxy.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "BoundCongregateWhipMotion.inl"
#include "BoundCongregateTentacleTiming.h"
#include "BoundCongregateTentacleGround.h"
#include "BoundCongregateTentacleReach.h"

/** Isolated original appendage. Old curl/feeler weights never drive an attack. */
struct FCongregateTentacle : FAnimNode_SkeletalControlBase
{
    // The recorded thin-chain throw starts at 7; WhipStem now actively bends
    // bones 1..8 upstream, so this anchor moves with the muscular whole organ.
    static constexpr int32 Count=57,Anchor=7;
    FBoneReference Bones[Count];
    FCongregateTentacleGround* Ground=nullptr;
    float Lengths[Count-1]={},TotalLength=0,Weight=0,Strike=0,Wrap=0,Dt=0;
    FVector Aim,Forward,Right;
    float Radius=34;
    bool Active=false,Windup=false,Filtered=false;
    FVector LastGoals[Count];
    FTransform LastLocal[Count],LastFinal[Count];
    bool HaveFinal=false,Recovering=false;
    bool Releasing=false;
    float LoadPhase=0;
    float RecoveryFollow=0,ReleaseSpeedScale=1;
    uint64 LastSolvedSerial=0;
    uint64 Serial=0,Evaluated=0;
    FCongregateTentacle()
    {
        Alpha=1.f;
        for(int32 I=0;I<Count;++I)Bones[I].BoneName=FName(FString::Printf(TEXT("attack_tentacle_%02d"),I));
    }
    virtual void InitializeBoneReferences(const FBoneContainer& Container) override
    {
        TotalLength=0;Filtered=false;HaveFinal=false;
        auto Ref=[&](FCompactPoseBoneIndex I)
        {FTransform T=Container.GetRefPoseTransform(I);for(auto P=Container.GetParentBoneIndex(I);P!=INDEX_NONE;P=Container.GetParentBoneIndex(P))T*=Container.GetRefPoseTransform(P);return T;};
        for(int32 I=0;I<Count;++I)
        {
            Bones[I].Initialize(Container);
            if(I&&Bones[I].IsValidToEvaluate(Container)&&Bones[I-1].IsValidToEvaluate(Container))
            {
                Lengths[I-1]=FVector::Distance(Ref(Bones[I].GetCompactPoseIndex(Container)).GetLocation(),Ref(Bones[I-1].GetCompactPoseIndex(Container)).GetLocation());
                if(I>Anchor)TotalLength+=Lengths[I-1];
            }
        }
    }
    virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer& Container) override
    {for(const auto& B:Bones)if(!B.IsValidToEvaluate(Container))return false;return TotalLength>1.f;}
    void Prepare(const ABoundCongregate* Monster,float Delta)
    {
        Active=Monster->TentacleActive();Dt=FMath::Clamp(Delta,0.f,.1f);Serial=GFrameCounter;
        if(!Active){Filtered=false;HaveFinal=false;return;}
        const auto State=Monster->NetState.State;const float T=float(Monster->StateElapsed());
        const FTransform& Frame=Monster->GetMesh()->GetComponentTransform();
        const auto* Target=Monster->NetState.CapturedTarget.Get();
        const FVector TargetPosition=Target?Target->GetActorLocation():FVector(Monster->NetState.TentacleAim);
        Aim=Frame.InverseTransformPosition(Monster->GetActorLocation()+
            (TargetPosition-Monster->GetActorLocation()).GetClampedToMaxSize(Monster->TentacleRange));
        Forward=Frame.InverseTransformVectorNoScale(Monster->GetActorForwardVector());
        Right=Frame.InverseTransformVectorNoScale(Monster->GetActorRightVector());
        Radius=Monster->NetState.TentacleRadius;
        Windup=State==EBoundCongregateState::TentacleWindup;
        Releasing=State==EBoundCongregateState::TentacleStrike;
        Recovering=Monster->TentacleRecovering();
        const float RecoveryTime=float(Monster->TentacleRecoveryElapsed());
        const float Recovery=BoundCongregateTentacleTiming::RecoveryPhase(RecoveryTime,Monster->TentacleRecoverSeconds);
        const float PreviousRecovery=BoundCongregateTentacleTiming::RecoveryPhase(RecoveryTime-Dt,Monster->TentacleRecoverSeconds);
        RecoveryFollow=FMath::Clamp((Recovery-PreviousRecovery)/FMath::Max(UE_SMALL_NUMBER,1.f-PreviousRecovery),0.f,1.f);
        // Continuous rear loading; no held final quarter before release.
        Weight=Windup?FMath::SmoothStep(0.f,Monster->TentacleWindupSeconds,T):1.f;
        LoadPhase=FMath::Clamp(T/Monster->TentacleWindupSeconds,0.f,1.f);
        const auto Release=BoundCongregateTentacleTiming::Release(T,Monster->TentacleReleaseDuration());
        Strike=Releasing?Release.Phase:Windup?0.f:1.f;
        // The authored stroke now runs 3x faster with a further nonlinear burst.
        // Its old fixed speed cap would delay the visible pose into recovery.
        ReleaseSpeedScale=BoundCongregateTentacleTiming::PreviousStrikeSeconds/FMath::Max(.001f,Monster->TentacleReleaseDuration())*FMath::Max(1.f,Release.Rate);
        Wrap=State==EBoundCongregateState::TentacleWrap?FMath::SmoothStep(0.f,Monster->TentacleWrapSeconds,T):
            Monster->NetState.CapturedTarget?1.f:0.f;
        if(Recovering)
        {
            const float Fade=1.f-Recovery;
            Weight=Monster->NetState.ReleasedWeight*Fade;Strike=Monster->NetState.ReleasedStrike*Fade;Wrap=Monster->NetState.ReleasedWrap*Fade;
        }
    }
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out) override
    {
        if(!Active||Weight<=UE_SMALL_NUMBER)return;
        const auto& Container=Output.Pose.GetPose().GetBoneContainer();
        FTransform Original[Count];FVector Goals[Count];
        for(int32 I=0;I<Count;++I)Original[I]=Output.Pose.GetComponentSpaceTransform(Bones[I].GetCompactPoseIndex(Container));
        if(HaveFinal&&LastSolvedSerial==Serial)
        {for(int32 I=Anchor;I<Count;++I)Out.Emplace(Bones[I].GetCompactPoseIndex(Container),LastFinal[I]);return;}
        if(!HaveFinal)for(int32 I=Anchor;I<Count;++I)
        {LastFinal[I]=Original[I];LastLocal[I]=Original[I].GetRelativeTransform(Original[I-1]);}
        const FVector Root=Original[Anchor].GetLocation(),Up=FVector::UpVector;
        const FVector RootTangent=(Original[Anchor+1].GetLocation()-Root).GetSafeNormal();
        if(!Recovering)
        {
            // Retain the root-driven recorded wave and shoulder transition.
            // The distal deployment pass adds reach after the muscular base.
            const FVector Direction=(Aim-Root).GetSafeNormal2D();
            const FVector Across=FVector::CrossProduct(Direction,Up).GetSafeNormal();
            const FVector Contact=BoundWhipMotion::Sample(1.f,Count-Anchor-1);
            const FVector ToAim=Aim-Root;
            float Yaw=FMath::Atan2(Contact.Y,Contact.X);
            float Pitch=FMath::Clamp(float(FMath::Atan2(ToAim.Z,ToAim.Size2D())-FMath::Atan2(Contact.Z,Contact.Size2D())),-.5f,.5f);
            auto ToFrame=[&](const FVector& P)
            {
                const float Along=P.X*FMath::Cos(Yaw)+P.Y*FMath::Sin(Yaw);
                const float Side=-P.X*FMath::Sin(Yaw)+P.Y*FMath::Cos(Yaw);
                return Direction*(Along*FMath::Cos(Pitch)-P.Z*FMath::Sin(Pitch))+Across*Side+Up*(Along*FMath::Sin(Pitch)+P.Z*FMath::Cos(Pitch));
            };
            auto SegmentDirection=[&](float Phase,int32 I)
            {
                const int32 J=I-Anchor;
                const FVector Rest=(Original[I].GetLocation()-Original[I-1].GetLocation()).GetSafeNormal();
                const FVector Thrown=ToFrame(BoundWhipMotion::Sample(Phase,J)-BoundWhipMotion::Sample(Phase,J-1)).GetSafeNormal();
                // A continuous shoulder tangent carries torque into the thin
                // chain instead of creating a new hinge at the fixed collar.
                const float Blend=FMath::SmoothStep(0.f,6.f,float(J-1));
                return FQuat::Slerp(FQuat::Identity,FQuat::FindBetweenNormals(Rest,Thrown),Blend).RotateVector(Rest);
            };
            // Align the whole recorded throw with the victim after adding the
            // shoulder transition. This rotates the clip, never attracts its tip.
            for(int32 Iteration=0;Iteration<5;++Iteration)
            {
                FVector End=FVector::ZeroVector;
                for(int32 I=Anchor+1;I<Count;++I)End+=SegmentDirection(1.f,I)*Lengths[I-1];
                Yaw+=FMath::Atan2(FVector::DotProduct(End,Across),FVector::DotProduct(End,Direction));
                Pitch=FMath::Clamp(Pitch+float(FMath::Atan2(ToAim.Z,ToAim.Size2D())-FMath::Atan2(End.Z,End.Size2D())),-.9f,.9f);
            }
            for(int32 I=0;I<=Anchor;++I)Goals[I]=Original[I].GetLocation();
            for(int32 I=Anchor+1;I<Count;++I)
            {
                FVector D=SegmentDirection(Strike,I);
                Goals[I]=Goals[I-1]+D*Lengths[I-1];
            }
            if(Windup)
            {
                // Unfold along a continuous, full-length arc. Independent
                // per-joint preparation rotations wound the distal chain around
                // itself and exhausted the speed limit before the throw began.
                const float U=LoadPhase;
                const float Blend=U*U*(2.f-U);
                FVector Base[Count],Curve[Count];float Arc[Count]={};
                for(int32 I=Anchor;I<Count;++I)Base[I]=FMath::Lerp(Original[I].GetLocation(),Goals[I],Blend);
                auto BowLength=[&](float Amplitude)
                {
                    Curve[Anchor]=Root;Arc[Anchor]=0.f;
                    for(int32 I=Anchor+1;I<Count;++I)
                    {
                        const float S=float(I-Anchor)/(Count-1-Anchor);
                        Curve[I]=Base[I]+Up*(Amplitude*FMath::Square(FMath::Sin(PI*S)));
                        Arc[I]=Arc[I-1]+FVector::Distance(Curve[I-1],Curve[I]);
                    }
                    return Arc[Count-1];
                };
                if(BowLength(0.f)<TotalLength-.01f)
                {
                    float Low=0.f,High=TotalLength;
                    for(int32 Iteration=0;Iteration<16;++Iteration)
                    {const float Middle=(Low+High)*.5f;if(BowLength(Middle)<TotalLength)Low=Middle;else High=Middle;}
                    BowLength((Low+High)*.5f);
                }
                float Along=0.f;int32 Segment=Anchor+1;
                for(int32 I=Anchor+1;I<Count;++I)
                {
                    Along+=Lengths[I-1];
                    while(Segment<Count-1&&Arc[Segment]<Along)++Segment;
                    const FVector At=FMath::Lerp(Curve[Segment-1],Curve[Segment],FMath::Clamp((Along-Arc[Segment-1])/FMath::Max(.001f,Arc[Segment]-Arc[Segment-1]),0.f,1.f));
                    Goals[I]=Goals[I-1]+(At-Goals[I-1]).GetSafeNormal()*Lengths[I-1];
                }
            }
            Filtered=false;
        }
        else
        {
            // Retract the actual visible long pose, with the shared nonlinear
            // recovery clock. Interpolating component stations contracts before
            // folding and avoids swinging a thirty-metre rigid lever overhead.
            for(int32 I=0;I<Count;++I)
                Goals[I]=I<=Anchor?Original[I].GetLocation():FMath::Lerp(
                    LastFinal[I].GetLocation(),Original[I].GetLocation(),RecoveryFollow);
        }
        if(!Windup&&!Recovering)
            BoundCongregateTentacleReach::Deploy(Goals,Lengths,Aim,Strike,Wrap,Radius);
        FQuat Transport=FQuat::Identity;
        FTransform Candidate[Count];
        for(int32 I=0;I<Anchor;++I)Candidate[I]=Original[I];
        for(int32 I=Anchor;I<Count;++I)
        {
            const int32 A=I==Count-1?I-1:I,B=A+1;
            const FVector Rest=Original[B].GetLocation()-Original[A].GetLocation();
            const FVector Segment=Goals[B]-Goals[A];
            Transport=(FQuat::FindBetweenNormals(Transport.RotateVector(Rest.GetSafeNormal()),Segment.GetSafeNormal())*Transport).GetNormalized();
            Candidate[I]=Original[I];
            Candidate[I].SetLocation(Goals[I]);
            Candidate[I].SetRotation((Transport*Original[I].GetRotation()).GetNormalized());
            float Stretch=Segment.Size()/FMath::Max(.001,Rest.Size());
            if(I>Anchor)
                Stretch=.5f*(Stretch+float(FVector::Distance(Goals[I],Goals[I-1])/FMath::Max(.001f,Lengths[I-1])));
            Candidate[I].SetScale3D(BoundCongregateTentacleReach::SectionScale(Original[I],Rest,Stretch,I));
        }
        if(Ground)Ground->Constrain(Candidate,Anchor);
        for(int32 I=Anchor;I<Count;++I)
        {
            // Cache the terrain-corrected pose so recovery starts where the
            // visible organ actually was, without fighting the floor next frame.
            LastLocal[I]=Candidate[I].GetRelativeTransform(Candidate[I-1]);LastFinal[I]=Candidate[I];
            Out.Emplace(Bones[I].GetCompactPoseIndex(Container),Candidate[I]);
        }
        HaveFinal=true;LastSolvedSerial=Serial;
        Out.Sort([](const FBoneTransform& A,const FBoneTransform& B){return A.BoneIndex.GetInt()<B.BoneIndex.GetInt();});
    }
};
