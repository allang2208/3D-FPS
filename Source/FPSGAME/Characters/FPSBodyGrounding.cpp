#include "FPSBodyGrounding.h"
#include "FPSPlayerBodyAnimInstance.h"
#include "FPSPlayerBodyPoses.h"
#include "FPSBodyMeleePose.h"
#include "Components/SkeletalMeshComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"

void FFPSBodyGrounding::Reset()
{
    Pose=FFPSBodyGroundPose();Contacts[0]=FContact();Contacts[1]=FContact();
    bInitialized=bTurning=false;ProbeCountdown=0.f;
}

void FFPSBodyGrounding::Update(USkeletalMeshComponent& Mesh,const UFPSPlayerBodyAnimInstance& Anim,
    const FFPSBodyFootSeed (&Feet)[2],float WalkWeight,float Delta)
{
    const auto* Character=Cast<ACharacter>(Mesh.GetOwner());
    const auto* Move=Character?Character->GetCharacterMovement():nullptr;
    if(!Move||!Mesh.GetWorld())return;
    const FVector Location=Character->GetActorLocation();
    const float Yaw=Character->GetActorRotation().Yaw;
    const bool Jumped=bInitialized&&FVector::DistSquared(Location,LastLocation)>FMath::Square(150.f);
    if(Jumped||Asset.Get()!=Mesh.GetSkinnedAsset())
    {Reset();Asset=Mesh.GetSkinnedAsset();}
    if(!bInitialized){FeetYaw=Yaw;bInitialized=true;}
    LastLocation=Location;
    const bool Grounded=Move->IsMovingOnGround()&&!Anim.bFalling&&Anim.BodyState.Motion==EFPSBodyMotion::Ground
        &&Anim.BodyState.Action!=EFPSBodyAction::Dead;
    const bool Pushed=Anim.Clock-Anim.Reactions.PushAt<Anim.Reactions.PushSeconds;
    const bool Melee=FPSBodyMelee::Active(Anim.BodyState);
    const bool CanTurn=Grounded&&Anim.Speed<15.f&&!Anim.Reactions.bStunned&&!Pushed&&!Melee;
    constexpr float TurnSeconds=.48f;
    if(CanTurn)
    {
        const float Error=FMath::FindDeltaAngleDegrees(FeetYaw,Yaw);
        if(!bTurning&&FMath::Abs(Error)>35.f)
        {bTurning=true;TurnAge=0.f;TurnFrom=FeetYaw;TurnDelta=FMath::Clamp(Error,-65.f,65.f);}
        if(bTurning)
        {
            TurnAge+=Delta;const float T=FMath::Clamp(TurnAge/TurnSeconds,0.f,1.f);
            FeetYaw=TurnFrom+TurnDelta*FMath::SmoothStep(0.f,1.f,T);
            const int32 Lead=TurnDelta>0.f?0:1;
            for(int32 I=0;I<2;++I)
            {
                const float Phase=I==Lead?T*2.f:(T-.5f)*2.f;
                Pose.TurnLift[I]=(Phase>0.f&&Phase<1.f)?FMath::Sin(PI*Phase)*7.f:0.f;
            }
            if(T>=1.f)bTurning=false;
        }
        else Pose.TurnLift[0]=Pose.TurnLift[1]=0.f;
    }
    else
    {
        bTurning=false;Pose.TurnLift[0]=Pose.TurnLift[1]=0.f;
        FeetYaw+=FMath::Clamp(FMath::FindDeltaAngleDegrees(FeetYaw,Yaw),-Delta*360.f,Delta*360.f);
    }
    Pose.TurnAlpha=FMath::FInterpTo(Pose.TurnAlpha,CanTurn?1.f:0.f,Delta,14.f);
    Pose.LowerYaw=FMath::Clamp(FMath::FindDeltaAngleDegrees(Yaw,FeetYaw),-70.f,70.f)*Pose.TurnAlpha;
    if(!Grounded)
    {
        for(int32 I=0;I<2;++I)
        {Contacts[I]=FContact();Pose.SolePlant[I]=0.f;Pose.Weight[I]=FMath::FInterpConstantTo(Pose.Weight[I],0.f,Delta,14.f);}
        Pose.PelvisZ=FMath::FInterpTo(Pose.PelvisZ,0.f,Delta,18.f);ProbeCountdown=0.f;
        return;
    }
    const FTransform Frame=Mesh.GetComponentTransform();
    const float Step=FMath::Clamp(Move->MaxStepHeight,15.f,55.f);
    ProbeCountdown-=Delta;
    if(ProbeCountdown<=0.f)
    {
        float Interval=1.f/30.f;
        if(const auto* PC=Mesh.GetWorld()->GetFirstPlayerController();PC&&PC->GetPawn())
            if(FVector::DistSquared(PC->GetPawn()->GetActorLocation(),Location)>FMath::Square(1800.f))Interval=.1f;
        ProbeCountdown=Interval;
        FCollisionQueryParams Params(SCENE_QUERY_STAT(PlayerBodyFeet),false,Character);
        const auto Trace=[&](FVector At,FHitResult& Hit)
        {
            const double Base=Frame.GetLocation().Z;
            return Mesh.GetWorld()->LineTraceSingleByChannel(Hit,FVector(At.X,At.Y,Base+Step+22.f),
                FVector(At.X,At.Y,Base-Step-20.f),ECC_Pawn,Params)&&!Hit.bStartPenetrating&&
                Hit.GetComponent()&&Hit.GetComponent()->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block&&
                !Cast<APawn>(Hit.GetActor())&&Move->IsWalkable(Hit);
        };
        for(int32 I=0;I<2;++I)
        {
            auto& C=Contacts[I];if(!Feet[I].bValid){C=FContact();continue;}
            const FVector Ankle=Frame.TransformPosition(Feet[I].Ankle.GetLocation());
            FHitResult Center;
            if(!Trace(Ankle,Center)){C=FContact();continue;}
            FVector Normal=Center.ImpactNormal;
            FVector Forward=Frame.TransformVector(Feet[I].Toe-Feet[I].Ankle.GetLocation()).GetSafeNormal2D();
            if(Forward.IsNearlyZero())Forward=Character->GetActorForwardVector();
            // Avoid fitting a fake slope across two different stair treads.
            FHitResult Toe,Heel;
            const bool ToeHit=Trace(Ankle+Forward*10.f,Toe),HeelHit=Trace(Ankle-Forward*5.f,Heel);
            if(ToeHit&&HeelHit&&Toe.GetComponent()==Center.GetComponent()&&Heel.GetComponent()==Center.GetComponent()&&
                FMath::Abs(Toe.ImpactPoint.Z-Heel.ImpactPoint.Z)<8.f)
                Normal=(Normal+Toe.ImpactNormal+Heel.ImpactNormal).GetSafeNormal();
            auto* Surface=Center.GetComponent();
            if(C.Surface.Get()!=Surface)C.bPlanted=false;
            C.Surface=Surface;const FTransform SurfaceFrame=Surface->GetComponentTransform();
            C.LocalPoint=SurfaceFrame.InverseTransformPosition(Center.ImpactPoint);
            C.LocalNormal=SurfaceFrame.InverseTransformVectorNoScale(Normal);C.bValid=true;
        }
    }
    float Pelvis=0.f;
    for(int32 I=0;I<2;++I)
    {
        auto& C=Contacts[I];auto* Surface=C.Surface.Get();
        const bool Valid=C.bValid&&Surface&&Surface->IsRegistered()&&Surface->IsQueryCollisionEnabled()&&
            Surface->GetCollisionResponseToChannel(ECC_Pawn)==ECR_Block&&Feet[I].bValid;
        Pose.Weight[I]=FMath::FInterpTo(Pose.Weight[I],Valid?1.f:0.f,Delta,20.f);
        if(!Valid){C.bPlanted=false;Pose.SolePlant[I]=0.f;continue;}
        const FTransform SurfaceFrame=Surface->GetComponentTransform();
        const FVector Point=SurfaceFrame.TransformPosition(C.LocalPoint);
        FVector Normal=SurfaceFrame.TransformVectorNoScale(C.LocalNormal).GetSafeNormal();
        const FVector Raw=Frame.TransformPosition(Feet[I].Ankle.GetLocation());
        const float Lift=FMath::Max(0.f,float(Feet[I].Ankle.GetLocation().Z)-Feet[I].SoleHeight);
        // These feet came from the previous completed animation evaluation. Use
        // its contact phase too, rather than next frame's already advanced clock.
        const float Phase=FMath::Frac(Feet[I].GaitPhase+(I==0?.5f:0.f));
        const float Load=Anim.Speed<15.f?(Pose.TurnLift[I]<.5f?1.f:0.f):
            FMath::SmoothStep(0.f,.10f,Phase)*(1.f-FMath::SmoothStep(.30f,.48f,Phase))*WalkWeight;
        // A rising ankle can mean heel roll, not swing clearance. Settle the heel
        // during walking mid-stance; keep toe-first backward landings, toe-off,
        // airborne feet and the authored jog/reaction/attack steps intact.
        Pose.SolePlant[I]=!Melee&&!Pushed?Load*(1.f-FMath::SmoothStep(6.f,14.f,Lift)):0.f;
        FVector Goal(Raw.X,Raw.Y,Point.Z+(Feet[I].SoleHeight+Lift*(1.f-Pose.SolePlant[I]))*Frame.GetScale3D().Z);
        const bool Stance=(Anim.Speed<15.f?Pose.TurnLift[I]<.5f:(Phase<.55f&&Lift<6.f))&&!Melee&&!Pushed;
        if(!Stance)C.bPlanted=false;
        else
        {
            if(!C.bPlanted){C.PlantLocal=SurfaceFrame.InverseTransformPosition(Goal);C.bPlanted=true;}
            const FVector Plant=SurfaceFrame.TransformPosition(C.PlantLocal);
            const FVector Hip=Feet[I].Hip+FVector(0,0,Pose.PelvisZ);
            const bool Overextended=Feet[I].ReachLimit>0.f&&
                FVector::DistSquared(Hip,Frame.InverseTransformPosition(Plant))>FMath::Square(Feet[I].ReachLimit+.5f);
            // A fixed 28 cm slip budget can lock a short/near-straight leg beyond
            // reach. Release the plant before IK erases the authored knee bend.
            if(Overextended||FVector::DistSquared2D(Plant,Goal)>FMath::Square(28.f)||FMath::Abs(Plant.Z-Goal.Z)>2.f)C.bPlanted=false;
            else {Goal.X=Plant.X;Goal.Y=Plant.Y;Goal.Z=Plant.Z;}
        }
        const FVector Offset=Frame.InverseTransformVector(Goal-Raw);
        FVector Clamped=Offset;Clamped.Z=FMath::Clamp(Clamped.Z,-Step,Step);
        // Actual tread height is immediate when rising; downward pelvis/ankle
        // settling is damped, preventing accumulated feedback from the solved foot.
        const float Z=Clamped.Z>Pose.FootOffset[I].Z?Clamped.Z:FMath::FInterpTo(float(Pose.FootOffset[I].Z),float(Clamped.Z),Delta,18.f);
        Pose.FootOffset[I]=FMath::VInterpTo(Pose.FootOffset[I],Clamped,Delta,22.f);Pose.FootOffset[I].Z=Z;
        Normal=Frame.InverseTransformVectorNoScale(Normal).GetSafeNormal();
        FQuat Tilt=FQuat::FindBetweenNormals(FVector::UpVector,Normal);
        const float Angle=Tilt.GetAngle();if(Angle>FMath::DegreesToRadians(35.f))Tilt=FQuat::Slerp(FQuat::Identity,Tilt,FMath::DegreesToRadians(35.f)/Angle);
        Pose.FootTilt[I]=FQuat::Slerp(Pose.FootTilt[I],Tilt,FMath::Clamp(Delta*16.f,0.f,1.f)).GetNormalized();
        Pelvis=FMath::Min(Pelvis,float(Pose.FootOffset[I].Z)*Pose.Weight[I]);
    }
    Pose.PelvisZ=FMath::FInterpTo(Pose.PelvisZ,FMath::Clamp(Pelvis,-Step*.85f,0.f),Delta,18.f);
}
