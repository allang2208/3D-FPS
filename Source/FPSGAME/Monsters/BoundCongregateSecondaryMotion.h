#pragma once
#include "BoundCongregate.h"
#include "Animation/AnimInstanceProxy.h"
#include "BoneControllers/AnimNode_SkeletalControlBase.h"
#include "Components/SkeletalMeshComponent.h"
#include "BoundCongregateTentacleGround.h"

/** Shape-supported flesh: inertial bending about the authored curl, not a dangling rope. */
struct FCongregateSecondaryMotion : FAnimNode_SkeletalControlBase
{
    static constexpr int32 Count=57,Anchor=3;
    FBoneReference Bones[Count],Body;
    FTransform ReferenceLocal[Count],Result[Count],Frame;
    FVector Offset[Count]{},Velocity[Count]{},PreviousTarget[Count]{},TargetVelocity[Count]{};
    FCongregateTentacleGround* Ground=nullptr;
    float Dt=0,Weight=1,MotionPhase=0,PreviousPhase=0,MotionAmount=0,IdleTime=0;
    bool WasWalking=false;
    FVector SideAxis=FVector::RightVector,ForwardAxis=FVector::ForwardVector;
    bool Enabled=false,Initialized=false;
    uint64 Serial=0,Solved=MAX_uint64;
    FCongregateSecondaryMotion()
    {
        Alpha=1.f;Body.BoneName=TEXT("body");
        for(int32 I=0;I<Count;++I)Bones[I].BoneName=FName(FString::Printf(TEXT("attack_tentacle_%02d"),I));
    }
    virtual void InitializeBoneReferences(const FBoneContainer& Container) override
    {
        Body.Initialize(Container);Initialized=false;Solved=MAX_uint64;
        for(int32 I=0;I<Count;++I)
        {
            Bones[I].Initialize(Container);
            if(Bones[I].IsValidToEvaluate(Container))ReferenceLocal[I]=Container.GetRefPoseTransform(Bones[I].GetCompactPoseIndex(Container));
        }
    }
    virtual bool IsValidToEvaluate(const USkeleton*,const FBoneContainer& Container) override
    {
        if(!Body.IsValidToEvaluate(Container))return false;
        for(const auto& B:Bones)if(!B.IsValidToEvaluate(Container))return false;
        return true;
    }
    void Prepare(const ABoundCongregate* Monster,float Phase,bool Walking,float Delta)
    {
        Enabled=!Monster->Dead();Dt=FMath::Clamp(Delta,0.f,.1f);Serial=GFrameCounter;
        Frame=Monster->GetMesh()->GetComponentTransform();Weight=1.f;
        SideAxis=Monster->GetActorRightVector();ForwardAxis=Monster->GetActorForwardVector();
        if(Walking&&WasWalking)MotionPhase+=FMath::Frac(Phase-PreviousPhase+1.f)*2.f*PI;
        MotionPhase=FMath::Fmod(MotionPhase,2.f*PI);PreviousPhase=Phase;WasWalking=Walking;
        IdleTime=FMath::Fmod(IdleTime+Dt,200.f*PI);
        const float Amount=Walking?FMath::Clamp(float(Monster->GetVelocity().Size2D())/65.f,0.f,1.f):0.f;
        MotionAmount=FMath::FInterpTo(MotionAmount,Amount,Dt,5.f);
        if(Monster->TentacleActive())
        {
            const float T=float(Monster->StateElapsed());
            const auto State=Monster->NetState.State;
            Weight=State==EBoundCongregateState::TentacleWindup?1.f-FMath::SmoothStep(0.f,.24f,T):
                State==EBoundCongregateState::TentacleRecover?FMath::SmoothStep(.7f,1.f,T/Monster->TentacleRecoverSeconds):0.f;
        }
    }
    virtual void EvaluateSkeletalControl_AnyThread(FComponentSpacePoseContext& Output,TArray<FBoneTransform>& Out) override
    {
        if(!Enabled){Initialized=false;return;}
        const auto& C=Output.Pose.GetPose().GetBoneContainer();
        if(Solved==Serial)
        {for(int32 I=0;I<Count;++I)Out.Emplace(Bones[I].GetCompactPoseIndex(C),Result[I]);return;}
        FTransform Rest[Count];FVector Target[Count],Acceleration[Count];
        FTransform Parent=Output.Pose.GetComponentSpaceTransform(Body.GetCompactPoseIndex(C));
        for(int32 I=0;I<Count;++I)
        {
            // Clip-switch snapshots may already contain secondary motion. Use
            // this chain's authored locals once, preserving animated body motion.
            Rest[I]=ReferenceLocal[I]*Parent;Parent=Rest[I];
            Target[I]=Frame.TransformPosition(Rest[I].GetLocation());
        }
        const bool Reset=!Initialized||FVector::DistSquared(Target[Anchor],PreviousTarget[Anchor])>FMath::Square(100.f);
        for(int32 I=0;I<Count;++I)
        {
            if(Reset){Offset[I]=Velocity[I]=TargetVelocity[I]=FVector::ZeroVector;}
            const FVector V=(!Reset&&Dt>UE_SMALL_NUMBER)?(Target[I]-PreviousTarget[I])/Dt:FVector::ZeroVector;
            Acceleration[I]=(!Reset&&Dt>UE_SMALL_NUMBER)?((V-TargetVelocity[I])/Dt).GetClampedToMaxSize(1800.f):FVector::ZeroVector;
            PreviousTarget[I]=Target[I];TargetVelocity[I]=V;
        }
        // Step energy continues travelling along the organ at constant speed.
        // Acceleration and turn inertia remain independent spring inputs.
        const int32 Steps=FMath::Max(1,FMath::CeilToInt(Dt*120.f));const float H=Dt/Steps;
        for(int32 Step=0;Step<Steps;++Step)
        {
            FVector Force[Count];
            for(int32 I=Anchor+1;I<Count;++I)
            {
                const float S=float(I-Anchor)/(Count-1-Anchor),Flex=FMath::SmoothStep(0.f,1.f,S);
                const float K=FMath::Lerp(225.f,42.f,Flex),Damping=1.35f*FMath::Sqrt(K);
                const FVector Neighbour=Offset[I-1]+Offset[FMath::Min(I+1,Count-1)]-2.f*Offset[I];
                const float Wave=MotionPhase-5.4f*S;
                const FVector Gait=SideAxis*(13.f*FMath::Sin(Wave))+ForwardAxis*(5.f*FMath::Sin(Wave-.8f))+FVector::UpVector*(4.f*FMath::Sin(2.f*Wave-.6f));
                const FVector Idle=SideAxis*(1.4f*FMath::Sin(IdleTime*1.17f-3.5f*S))+FVector::UpVector*(.8f*FMath::Sin(IdleTime*.91f-4.f*S));
                const FVector Driven=(Gait*MotionAmount+Idle*(1.f-MotionAmount))*Flex;
                Force[I]=K*(Driven-Offset[I])-Damping*Velocity[I]+80.f*Neighbour-Acceleration[I]*Flex+FVector(0,0,-35.f)*Flex;
            }
            for(int32 I=Anchor+1;I<Count;++I)
            {
                const float Flex=FMath::SmoothStep(0.f,1.f,float(I-Anchor)/(Count-1-Anchor));
                Velocity[I]=(Velocity[I]+Force[I]*H).GetClampedToMaxSize(200.f);
                const FVector Next=Offset[I]+Velocity[I]*H;
                Offset[I]=Next.GetClampedToMaxSize(38.f*Flex);
                if(!Next.Equals(Offset[I],.0001f))Velocity[I]=FVector::VectorPlaneProject(Velocity[I],Offset[I].GetSafeNormal());
            }
        }
        FVector Goals[Count];FQuat Transport=FQuat::Identity;
        for(int32 I=0;I<=Anchor;++I){Goals[I]=Rest[I].GetLocation();Result[I]=Rest[I];}
        for(int32 I=Anchor+1;I<Count;++I)
        {
            const FVector Segment=Rest[I].GetLocation()-Rest[I-1].GetLocation();
            const FVector Deflection=Frame.InverseTransformVector(Offset[I]-Offset[I-1])*Weight;
            const FVector Direction=(Segment+Deflection).GetSafeNormal();
            const FQuat Bend=FQuat::FindBetweenNormals(Segment.GetSafeNormal(),Direction);
            const float S=float(I-Anchor)/(Count-1-Anchor);
            const float MaxAngle=FMath::DegreesToRadians(FMath::Lerp(1.5f,18.f,S*S));
            const float Fraction=FMath::Min(1.f,MaxAngle/FMath::Max(.00001f,float(Bend.GetAngle())));
            Goals[I]=Goals[I-1]+FQuat::Slerp(FQuat::Identity,Bend,Fraction).RotateVector(Segment);
        }
        for(int32 I=Anchor;I<Count;++I)
        {
            const int32 A=I==Count-1?I-1:I,B=A+1;
            const FVector Before=(Rest[B].GetLocation()-Rest[A].GetLocation()).GetSafeNormal();
            const FVector After=(Goals[B]-Goals[A]).GetSafeNormal();
            Transport=(FQuat::FindBetweenNormals(Transport.RotateVector(Before),After)*Transport).GetNormalized();
            Result[I]=Rest[I];Result[I].SetLocation(Goals[I]);Result[I].SetRotation((Transport*Rest[I].GetRotation()).GetNormalized());
        }
        if(Ground)Ground->Constrain(Result,Anchor);
        for(int32 I=0;I<Count;++I)Out.Emplace(Bones[I].GetCompactPoseIndex(C),Result[I]);
        Initialized=true;Solved=Serial;
    }
};
