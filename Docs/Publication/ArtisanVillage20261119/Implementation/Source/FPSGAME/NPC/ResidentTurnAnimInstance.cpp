#include "ResidentTurnAnimInstance.h"
#include "ResidentConversation.h"
#include "Animation/AnimSingleNodeInstanceProxy.h"
#include "BonePose.h"
#include "Components/SkeletalMeshComponent.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "TwoBoneIK.h"

namespace ResidentTurn
{
struct FFootstep
{
    float Angle=0.f;
    float Lift=0.f;

    void Swing(float Time,float Begin,float End,float From,float To)
    {
        const float T=FMath::Clamp((Time-Begin)/(End-Begin),0.f,1.f);
        Angle=FMath::Lerp(From,To,FMath::SmoothStep(0.f,1.f,T));
        // As on the player, the leading foot lifts first. Ease both the toe-off and heel contact.
        Lift=FMath::Square(FMath::Sin(PI*T))*FMath::GetMappedRangeValueClamped(
            FVector2D(0.,90.),FVector2D(0.,7.),FMath::Abs(To-From));
    }
};

struct FTurnProxy final : FAnimSingleNodeInstanceProxy
{
    explicit FTurnProxy(UAnimInstance* Owner):FAnimSingleNodeInstanceProxy(Owner) {}

    float StartYaw=0.f, Angle=0.f, Elapsed=0.f, Duration=0.f;
    float BodyTravel=0.f;
    FFootstep Step[2];

    virtual void PreUpdate(UAnimInstance* Instance,float DeltaSeconds) override
    {
        // Sample the viewer and move only the visual frame on the game thread. All later
        // skeletal calculations read a value snapshot, including when evaluation runs in parallel.
        auto* Anim=CastChecked<UResidentTurnAnimInstance>(Instance);
        USkeletalMeshComponent* Body=Anim->GetSkelMeshComponent();
        if (Body) AdvanceFrame(*Body,Anim->ConversationPlayer.Get(),DeltaSeconds);
        FAnimSingleNodeInstanceProxy::PreUpdate(Instance,DeltaSeconds);
    }

    void AdvanceFrame(USkeletalMeshComponent& Body,const APlayerController* Viewer,float DeltaSeconds)
    {
        if (Duration<=0.f)
        {
            const APawn* Pawn=Viewer && Viewer->IsLocalController() && Viewer->GetWorld()==Body.GetWorld()
                ? Viewer->GetPawn() : nullptr;
            if (!Pawn || !Body.GetOwner()) return;
            const FVector Towards=Pawn->GetActorLocation()-Body.GetComponentLocation();
            if (Towards.SizeSquared2D()<=UE_KINDA_SMALL_NUMBER) return;
            const float Goal=FResidentConversationFacing::RestYaw+Towards.Rotation().Yaw-Body.GetOwner()->GetActorRotation().Yaw;
            StartYaw=Body.GetRelativeRotation().Yaw;
            Angle=FMath::FindDeltaAngleDegrees(StartYaw,Goal);
            if (FMath::Abs(Angle)<1.f) return;
            Duration=FMath::GetMappedRangeValueClamped(FVector2D(0.,180.),FVector2D(.17,.46),FMath::Abs(Angle));
            Elapsed=0.f;
        }
        // A closed conversation still finishes the committed footfalls and retains the landing yaw.
        Elapsed+=FMath::Max(DeltaSeconds,0.f);
        const float T=FMath::Min(Elapsed/Duration,1.f);
        BodyTravel=Angle*FMath::SmoothStep(0.f,1.f,T);
        Body.SetRelativeRotation(FRotator(0.,StartYaw+BodyTravel,0.));
        if (T>=1.f)
        {
            Duration=0.f;
            return;
        }

        const int32 Lead=Angle>0.f?0:1; // right / left in the shared player rig
        if (FMath::Abs(Angle)>88.f)
        {
            // A half turn uses three contacts. Moving a leading foot straight through a
            // full half-circle in two contacts would put it on top of the supporting foot.
            if (T<.5f) Step[Lead].Swing(T,0.f,.30f,0.f,Angle*.5f);
            else Step[Lead].Swing(T,.70f,1.f,Angle*.5f,Angle);
            Step[1-Lead].Swing(T,.30f,.70f,0.f,Angle);
        }
        else
        {
            Step[Lead].Swing(T,0.f,.5f,0.f,Angle);
            Step[1-Lead].Swing(T,.5f,1.f,0.f,Angle);
        }
    }

    virtual bool Evaluate(FPoseContext& Output) override
    {
        FAnimSingleNodeInstanceProxy::Evaluate(Output);
        if (Duration<=0.f) return true;
        const FBoneContainer& Bones=Output.Pose.GetBoneContainer();
        const auto Compact=[&Bones](FName Name)
        {
            const int32 Index=Bones.GetPoseBoneIndexForBoneName(Name);
            return Index==INDEX_NONE?FCompactPoseBoneIndex(INDEX_NONE):Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Index));
        };
        static const FName PelvisName(TEXT("pelvis")), RightFoot(TEXT("foot_r")), LeftFoot(TEXT("foot_l"));
        const auto Pelvis=Compact(PelvisName);
        const FCompactPoseBoneIndex Feet[]={Compact(RightFoot),Compact(LeftFoot)};
        if (Pelvis==INDEX_NONE || Feet[0]==INDEX_NONE || Feet[1]==INDEX_NONE) return true;

        FCSPose<FCompactPose> Pose;
        Pose.InitPose(Output.Pose);
        FTransform Target[2];
        FVector KneeDirection[2];
        FCompactPoseBoneIndex Thigh[2],Calf[2];
        for (int32 I=0;I<2;++I)
        {
            Calf[I]=Bones.GetParentBoneIndex(Feet[I]);
            if (Calf[I]==INDEX_NONE) return true;
            Thigh[I]=Bones.GetParentBoneIndex(Calf[I]);
            if (Thigh[I]==INDEX_NONE) return true;
            const FTransform& Ankle=Pose.GetComponentSpaceTransform(Feet[I]);
            const FVector Hip=Pose.GetComponentSpaceTransform(Thigh[I]).GetLocation();
            const FVector Knee=Pose.GetComponentSpaceTransform(Calf[I]).GetLocation();
            const FVector Axis=(Ankle.GetLocation()-Hip).GetSafeNormal();
            const float LocalYaw=Step[I].Angle-BodyTravel;
            const FQuat FootTurn(FVector::UpVector,FMath::DegreesToRadians(LocalYaw));
            // Counter-rotate the stance foot about the mesh origin. Its world position
            // and boot direction stay fixed until this foot's own swing window opens.
            Target[I]=Ankle;
            Target[I].SetRotation((FootTurn*Ankle.GetRotation()).GetNormalized());
            Target[I].SetLocation(FootTurn.RotateVector(Ankle.GetLocation())+FVector(0.,0.,Step[I].Lift));
            FVector Bend=FVector::VectorPlaneProject(Knee-Hip,Axis);
            if (!Bend.Normalize()) Bend=FVector::RightVector;
            KneeDirection[I]=FQuat(FVector::UpVector,FMath::DegreesToRadians(.4f*LocalYaw)).RotateVector(Bend);
        }

        const int32 Planted=Step[0].Lift>Step[1].Lift?1:0;
        const float Weight=FMath::Max(Step[0].Lift,Step[1].Lift)/7.f;
        FTransform Hips=Pose.GetComponentSpaceTransform(Pelvis);
        const FVector ToSupport=(Target[Planted].GetLocation()-Hips.GetLocation()).GetSafeNormal2D();
        FVector Shift=Weight*(1.8f*ToSupport-FVector(0.,0.,1.0));
        // Lower the hips enough for the planted ankle to stay put, instead of stretching a leg.
        for (int32 I=0;I<2;++I)
        {
            const FVector H=Pose.GetComponentSpaceTransform(Thigh[I]).GetLocation();
            const FVector K=Pose.GetComponentSpaceTransform(Calf[I]).GetLocation();
            const FVector F=Pose.GetComponentSpaceTransform(Feet[I]).GetLocation();
            const double Reach=FMath::Max(FVector::Distance(H,F),.995*(FVector::Distance(H,K)+FVector::Distance(K,F)));
            const FVector Span=H+Shift-Target[I].GetLocation();
            const double Height=FMath::Sqrt(FMath::Max(0.,Reach*Reach-Span.SizeSquared2D()));
            Shift.Z-=FMath::Max(0.,Span.Z-Height);
        }
        Hips.AddToTranslation(Shift);
        TArray<FBoneTransform,TInlineAllocator<1>> PelvicChange;
        PelvicChange.Emplace(Pelvis,Hips);
        Pose.LocalBlendCSBoneTransforms(PelvicChange,1.f);
        for (int32 I=0;I<2;++I)
        {
            FTransform Hip=Pose.GetComponentSpaceTransform(Thigh[I]);
            FTransform Knee=Pose.GetComponentSpaceTransform(Calf[I]);
            FTransform Ankle=Pose.GetComponentSpaceTransform(Feet[I]);
            const FVector Pole=Hip.GetLocation()+KneeDirection[I]*80.;
            AnimationCore::SolveTwoBoneIK(Hip,Knee,Ankle,Pole,Target[I].GetLocation(),false,1.,1.);
            Ankle.SetRotation(Target[I].GetRotation());
            TArray<FBoneTransform,TInlineAllocator<3>> Leg;
            Leg.Emplace(Thigh[I],Hip);
            Leg.Emplace(Calf[I],Knee);
            Leg.Emplace(Feet[I],Ankle);
            Pose.LocalBlendCSBoneTransforms(Leg,1.f);
        }
        FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(Pose,Output.Pose);
        return true;
    }
};
}

FAnimInstanceProxy* UResidentTurnAnimInstance::CreateAnimInstanceProxy()
{
    return new ResidentTurn::FTurnProxy(this);
}
