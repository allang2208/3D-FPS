#pragma once
#include "BoundCongregate.h"
#include "Animation/AnimInstanceProxy.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/SkeletalMesh.h"
#include "BoundCongregateWhipMotion.inl"
#include "BoundCongregateTentacleTiming.h"
#include "BoundCongregateTentacleGround.h"

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
        Aim=Frame.InverseTransformPosition(Target?Target->GetActorLocation():Monster->NetState.TentacleAim);
        Forward=Frame.InverseTransformVectorNoScale(Monster->GetActorForwardVector());
        Right=Frame.InverseTransformVectorNoScale(Monster->GetActorRightVector());
        Radius=Monster->NetState.TentacleRadius;
        Windup=State==EBoundCongregateState::TentacleWindup;
        Releasing=State==EBoundCongregateState::TentacleStrike;
        Recovering=State==EBoundCongregateState::TentacleRecover;
        const float Recovery=BoundCongregateTentacleTiming::RecoveryPhase(T,Monster->TentacleRecoverSeconds);
        const float PreviousRecovery=BoundCongregateTentacleTiming::RecoveryPhase(T-Dt,Monster->TentacleRecoverSeconds);
        RecoveryFollow=FMath::Clamp((Recovery-PreviousRecovery)/FMath::Max(UE_SMALL_NUMBER,1.f-PreviousRecovery),0.f,1.f);
        // Continuous rear loading; no held final quarter before release.
        Weight=Windup?FMath::SmoothStep(0.f,Monster->TentacleWindupSeconds,T):1.f;
        LoadPhase=FMath::Clamp(T/Monster->TentacleWindupSeconds,0.f,1.f);
        const auto Release=BoundCongregateTentacleTiming::Release(T,Monster->TentacleStrikeSeconds);
        Strike=Releasing?Release.Phase:Windup?0.f:1.f;
        // The authored stroke now runs 3x faster with a further nonlinear burst.
        // Its old fixed speed cap would delay the visible pose into recovery.
        ReleaseSpeedScale=BoundCongregateTentacleTiming::PreviousStrikeSeconds/FMath::Max(.001f,Monster->TentacleStrikeSeconds)*FMath::Max(1.f,Release.Rate);
        Wrap=State==EBoundCongregateState::TentacleWrap?FMath::SmoothStep(0.f,Monster->TentacleWrapSeconds,T):
            State==EBoundCongregateState::TentacleDrag?1.f:0.f;
        if(State==EBoundCongregateState::TentacleRecover)
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
        if(Windup||Releasing)
        {
            // Play the root-driven physical throw. Aim rotates its attack plane;
            // it never drags the tip or replaces the travelling whip wave by IK.
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
        // Load the length BEHIND the shoulder, then throw it over the shoulder
        // in one fast forward stroke. The old front/up target read as raising.
        const FVector DrawnTip=Root-Forward*230.f+Right*85.f+Up*20.f;
        const FVector Center=FMath::Lerp(DrawnTip,Aim,Strike)+Up*(95.f*FMath::Sin(PI*Strike));
        const FVector Direction=(Aim-Root).GetSafeNormal2D();
        const FVector Side=FVector::CrossProduct(Up,Direction).GetSafeNormal();
        const FVector End=Center-Direction*Radius*Wrap;
        FVector Curve[81];float Arc[81]={};
        constexpr int32 StemSamples=56;
        FVector RestCurve[StemSamples+1];
        for(int32 I=0;I<=StemSamples;++I)
        {
            const float Position=float(I)*(Count-1-Anchor)/StemSamples;
            const int32 J=FMath::Min(Count-2,Anchor+FMath::FloorToInt(Position));
            RestCurve[I]=FMath::Lerp(Original[J].GetLocation(),Original[J+1].GetLocation(),Position-float(J-Anchor));
        }
        const FVector Bow=(-Forward*(1.f-Strike)+Right*(.65f-.85f*Strike)+Up*.55f).GetSafeNormal();
        auto MakeStem=[&](float Amplitude)
        {
            // Keep the root exit tangent short and fixed. Surplus length is
            // folded behind the body, not put into a tall vertical root spike.
            const FVector C1=Root+RootTangent*60.f;
            const FVector C2=End-Direction*(75.f*Strike)+Bow*Amplitude;
            float Length=0.f;
            for(int32 I=0;I<=StemSamples;++I)
            {
                const float U=float(I)/StemSamples,V=1-U;
                Curve[I]=Root*(V*V*V)+C1*(3*V*V*U)+C2*(3*V*U*U)+End*(U*U*U);
                if(Windup)Curve[I]=FMath::Lerp(RestCurve[I],Curve[I],Weight)+Up*(150.f*U*FMath::Sin(PI*Weight));
                if(I)Length+=FVector::Distance(Curve[I-1],Curve[I]);
            }
            return Length;
        };
        const float StemLength=MakeStem(0.f);
        // Reserve actual chain length for the coil. Distant contact starts as
        // a hook, then closes further as the victim is pulled towards the body.
        const float CoilAngle=FMath::Clamp((TotalLength-StemLength-8.f)/FMath::Max(1.f,Radius),0.f,2.f*PI*.88f)*Wrap;
        const float CoilLength=FMath::Sqrt(FMath::Square(CoilAngle*Radius*Wrap)+FMath::Square(12.f*Wrap));
        const float DesiredStem=FMath::Max(StemLength,TotalLength*1.002f-CoilLength);
        // Fit the WHOLE length into one broad bow. A short guide plus FABRIK
        // distributed surplus length as dozens of tiny alternating folds.
        float Low=0.f,High=TotalLength*2.5f/(Windup?FMath::Max(.2f,Weight):1.f);
        for(int32 Iteration=0;Iteration<14;++Iteration)
        {
            const float Middle=(Low+High)*.5f;
            if(MakeStem(Middle)<DesiredStem)Low=Middle;else High=Middle;
        }
        MakeStem((Low+High)*.5f);
        for(int32 I=StemSamples+1;I<81;++I)
        {
            const float U=float(I-StemSamples)/(80-StemSamples),Angle=CoilAngle*U;
            Curve[I]=Windup?Curve[StemSamples]:Center+(-Direction*FMath::Cos(Angle)+Side*FMath::Sin(Angle))*(Radius*Wrap)+Up*(12.f*Wrap*U);
        }
        for(int32 I=1;I<81;++I)Arc[I]=Arc[I-1]+FVector::Distance(Curve[I-1],Curve[I]);
        float Along=0;
        for(int32 I=0;I<=Anchor;++I)Goals[I]=Original[I].GetLocation();
        for(int32 I=Anchor+1;I<Count;++I)
        {
            Along+=Lengths[I-1];const float Distance=Arc[80]*Along/TotalLength;
            int32 J=1;while(J<80&&Arc[J]<Distance)++J;
            Goals[I]=FMath::Lerp(Curve[J-1],Curve[J],(Distance-Arc[J-1])/FMath::Max(.001f,Arc[J]-Arc[J-1]));
            // Windup blending happens inside MakeStem, before fitting its arc
            // length. Blending joint positions here would shorten the guide
            // and force FABRIK to put surplus length into small unwanted folds.
            if(!Filtered)LastGoals[I]=HaveFinal?LastFinal[I].GetLocation():Original[I].GetLocation();
            if(Serial!=Evaluated)LastGoals[I]=FMath::VInterpConstantTo(LastGoals[I],Goals[I],Dt,Releasing?6500.f:Windup?1200.f:1000.f);
            Goals[I]=LastGoals[I];
        }
        Filtered=true;Evaluated=Serial;
        const FVector Tip=Root+(Goals[Count-1]-Root).GetClampedToMaxSize(TotalLength*.98f);
        // FABRIK preserves every original segment length; the winding guide only
        // supplies the bend directions, it never scales the existing flesh.
        for(int32 Iteration=0;Iteration<16;++Iteration)
        {
            Goals[Count-1]=Tip;
            for(int32 I=Count-2;I>=Anchor;--I)Goals[I]=Goals[I+1]+(Goals[I]-Goals[I+1]).GetSafeNormal()*Lengths[I];
            Goals[Anchor]=Root;
            for(int32 I=Anchor+1;I<Count;++I)Goals[I]=Goals[I-1]+(Goals[I]-Goals[I-1]).GetSafeNormal()*Lengths[I-1];
        }
        }
        FQuat Transport=FQuat::Identity;
        FTransform Desired[Count],Proposed[Count];
        Desired[Anchor-1]=Original[Anchor-1];
        for(int32 I=Anchor;I<Count;++I)
        {
            const int32 A=I==Count-1?I-1:I,B=A+1;
            const FVector OldDirection=(Original[B].GetLocation()-Original[A].GetLocation()).GetSafeNormal();
            const FVector NewDirection=(Goals[B]-Goals[A]).GetSafeNormal();
            // Parallel transport a single frame down the chain. Independent
            // shortest-arc rotations on each bone introduced alternating roll.
            Transport=(FQuat::FindBetweenNormals(Transport.RotateVector(OldDirection),NewDirection)*Transport).GetNormalized();
            Desired[I]=Original[I];Desired[I].SetLocation(Goals[I]);Desired[I].SetRotation((Transport*Original[I].GetRotation()).GetNormalized());
            // Follow the previous visible local pose, not a fresh ref-to-goal
            // shortest-arc blend on every frame. The latter changes branches
            // at 180 degrees and whips the whole downstream chain across space.
            FTransform Local=Original[I].GetRelativeTransform(Original[I-1]);
            const FTransform TargetLocal=Desired[I].GetRelativeTransform(Desired[I-1]);
            const float Follow=Recovering?RecoveryFollow:(Windup||Releasing)?1.f:1.f-FMath::Exp(-Dt*28.f);
            Local.SetRotation(FQuat::Slerp(LastLocal[I].GetRotation(),Recovering?Local.GetRotation():TargetLocal.GetRotation(),Follow).GetNormalized());
            Proposed[I]=Local;
        }
        FTransform Candidate[Count];
        for(int32 I=0;I<Anchor;++I)Candidate[I]=Original[I];
        auto Compose=[&](float Fraction)
        {
            FTransform Parent=Original[Anchor-1];float Maximum=0.f;
            for(int32 I=Anchor;I<Count;++I)
            {
                FTransform Local=Proposed[I];Local.SetRotation(FQuat::Slerp(LastLocal[I].GetRotation(),Local.GetRotation(),Fraction).GetNormalized());
                Candidate[I]=Local*Parent;Parent=Candidate[I];
                Maximum=FMath::Max(Maximum,float(FVector::Distance(Candidate[I].GetLocation(),LastFinal[I].GetLocation())));
            }
            return Maximum;
        };
        const float Limit=(Windup?1800.f:Recovering?1500.f:Releasing?8000.f*ReleaseSpeedScale:1800.f)*Dt;
        float Fraction=1.f;
        if(Compose(1.f)>Limit)
        {
            float LowerFraction=0.f,UpperFraction=1.f;
            for(int32 Iteration=0;Iteration<10;++Iteration)
            {const float Middle=(LowerFraction+UpperFraction)*.5f;if(Compose(Middle)>Limit)UpperFraction=Middle;else LowerFraction=Middle;}
            Fraction=LowerFraction;Compose(Fraction);
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
