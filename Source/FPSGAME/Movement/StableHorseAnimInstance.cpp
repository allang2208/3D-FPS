#include "StableHorseAnimInstance.h"
#include "StableRidingHorse.h"
#include "Animation/AnimSingleNodeInstanceProxy.h"
#include "Animation/AnimSequence.h"
#include "Components/SkeletalMeshComponent.h"
#include "BonePose.h"
#include "TwoBoneIK.h"

namespace StableTurn
{
struct FProxy final : FAnimSingleNodeInstanceProxy
{
    explicit FProxy(UAnimInstance* Instance):FAnimSingleNodeInstanceProxy(Instance){}
    TWeakObjectPtr<UAnimationAsset> PreviousAsset;
    TArray<FTransform> LastPose, FromPose;
    float BlendAge=1.f, Turn=0.f, WalkLength=0.f;
    void PreUpdate(UAnimInstance* Instance,float Dt) override
    {
        FAnimSingleNodeInstanceProxy::PreUpdate(Instance,Dt);
        auto* Single=CastChecked<UStableHorseAnimInstance>(Instance);
        auto* Horse=Cast<AStableRidingHorse>(Instance->GetOwningActor());
        auto* Clip=Single->GetCurrentAsset();
        if(Clip!=PreviousAsset.Get())
        {
            FromPose=LastPose;
            BlendAge=0.f;
            PreviousAsset=Clip;
        }
        BlendAge+=Dt;
        WalkLength=Horse && Horse->WalkAnimation && Clip==Horse->WalkAnimation ? Horse->WalkAnimation->GetPlayLength() : 0.f;
        Turn=WalkLength>0.f ? Horse->GetPivotWeight() : 0.f;
    }

    void PlaceHoof(FCSPose<FCompactPose>& Pose, const FBoneContainer& Bones, FName TipName,bool bFront,const FVector& HorseForward,float Plant,float Phase)
    {
        int32 TipIndex=Bones.GetPoseBoneIndexForBoneName(TipName);
        if(TipIndex==INDEX_NONE)return;
        const auto Tip=Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(TipIndex));
        if(Tip==INDEX_NONE)return;
        const auto Ankle=Bones.GetParentBoneIndex(Tip);
        if(Ankle==INDEX_NONE)return;
        const auto Knee=Bones.GetParentBoneIndex(Ankle);
        if(Knee==INDEX_NONE)return;
        const auto Hip=Bones.GetParentBoneIndex(Knee);
        if(Hip==INDEX_NONE)return;
        FTransform A=Pose.GetComponentSpaceTransform(Hip), B=Pose.GetComponentSpaceTransform(Knee);
        FTransform C=Pose.GetComponentSpaceTransform(Ankle);
        const FVector Toe=Pose.GetComponentSpaceTransform(Tip).GetLocation();
        const FVector Rest=Bones.GetReferenceSkeleton().GetBoneAbsoluteTransform(TipIndex).GetLocation();
        const float P=FMath::Frac(Phase-Plant+1.f);
        // During stance, counter-rotate the planted shoe. Swing returns it to the next contact
        // with continuous angular velocity. The vertical lift and fetlock roll come from Walk.
        constexpr float Support=.62f;
        float Travel=P-Support*.5f-FMath::SmoothStep(Support,1.f,P);
        const FQuat Yaw(FVector::UpVector,FMath::DegreesToRadians(-FMath::Sign(Turn)*60.f*Travel));
        FVector Goal=Yaw.RotateVector(Rest);
        Goal.Z=Toe.Z;
        const FVector Axis=(C.GetLocation()-A.GetLocation()).GetSafeNormal();
        const FVector RawBend=FVector::VectorPlaneProject(B.GetLocation()-A.GetLocation(),Axis);
        const FVector Sagittal=FVector::VectorPlaneProject(bFront?-HorseForward:HorseForward,Axis).GetSafeNormal();
        FVector Pole=Sagittal;
        if(!RawBend.IsNearlyZero(.5))
        {
            const FVector Dir=RawBend.GetSafeNormal();
            if(Sagittal.IsNearlyZero() || FVector::DotProduct(Dir,Sagittal)>.25)
            {
                const double Blend=FMath::Clamp((RawBend.Size()-4.)/14.,0.,1.);
                Pole=(Sagittal.IsNearlyZero()?Dir:FMath::Lerp(Sagittal,Dir,Blend)).GetSafeNormal();
            }
        }
        if(Pole.IsNearlyZero())return;
        const FVector AnkleGoal=Goal+Yaw.RotateVector(C.GetLocation()-Toe);
        const FQuat FootRotation=Yaw*C.GetRotation();
        AnimationCore::SolveTwoBoneIK(A,B,C,A.GetLocation()+Pole*100.,AnkleGoal,false,1.,1.);
        C.SetRotation(FootRotation);
        TArray<FBoneTransform,TInlineAllocator<3>> Chain;
        Chain.Emplace(Hip,A);Chain.Emplace(Knee,B);Chain.Emplace(Ankle,C);
        Pose.LocalBlendCSBoneTransforms(Chain,FMath::Abs(Turn));
    }

    bool Evaluate(FPoseContext& Output) override
    {
        FAnimSingleNodeInstanceProxy::Evaluate(Output);
        if(WalkLength>0.f && FMath::Abs(Turn)>.001f)
        {
            FCSPose<FCompactPose> CS;CS.InitPose(Output.Pose);
            const auto& Bones=Output.Pose.GetBoneContainer();
            const float Phase=GetCurrentTime()/WalkLength;
            // Derive mesh-space forward from bind-pose front vs hind hoof anchors.
            FVector HorseForward=FVector::ForwardVector;
            const int32 FrontIdx=Bones.GetPoseBoneIndexForBoneName(TEXT("finger_L"));
            const int32 HindIdx=Bones.GetPoseBoneIndexForBoneName(TEXT("toe_L"));
            if(FrontIdx!=INDEX_NONE && HindIdx!=INDEX_NONE)
            {
                const FVector Span=Bones.GetReferenceSkeleton().GetBoneAbsoluteTransform(FrontIdx).GetLocation()
                    -Bones.GetReferenceSkeleton().GetBoneAbsoluteTransform(HindIdx).GetLocation();
                const FVector Flat=FVector(Span.X,Span.Y,0.).GetSafeNormal();
                if(!Flat.IsNearlyZero())HorseForward=Flat;
            }
            // True 4-beat lateral equine walk order (LH 0.00 -> LF 0.25 -> RH 0.50 -> RF 0.75).
            static const FName Feet[]={TEXT("toe_L"),TEXT("finger_L"),TEXT("toe_R"),TEXT("finger_R")};
            static const bool IsFront[]={false,true,false,true};
            for(int32 I=0;I<4;++I)PlaceHoof(CS,Bones,Feet[I],IsFront[I],HorseForward,I*.25f,Phase);
            FCSPose<FCompactPose>::ConvertComponentPosesToLocalPosesSafe(CS,Output.Pose);
        }
        const int32 Count=Output.Pose.GetNumBones();
        const float Alpha=FMath::SmoothStep(0.f,.13f,BlendAge);
        LastPose.SetNumUninitialized(Count);
        for(auto Bone:Output.Pose.ForEachBoneIndex())
        {
            FTransform& T=Output.Pose[Bone];
            if(Alpha<1.f && FromPose.Num()==Count)
            {
                const FTransform Current=T;
                T.Blend(FromPose[Bone.GetInt()],Current,Alpha);
            }
            LastPose[Bone.GetInt()]=T;
        }
        return true;
    }
};
}
FAnimInstanceProxy* UStableHorseAnimInstance::CreateAnimInstanceProxy(){return new StableTurn::FProxy(this);}
