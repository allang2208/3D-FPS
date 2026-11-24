#pragma once
#include "CoreMinimal.h"
#include "ReferenceSkeleton.h"
#include "TwoBoneIK.h"

// Shared anatomical transfer for the bow's FPS rig and native world body.
// The right palm closes before the bow moves; the left palm returns to that
// same live grip before the transfer runs backwards. No bone scaling.
struct FBowCastHandPose
{
    static constexpr float Seconds=.38f;
    TArray<FTransform> Reference;
    mutable TArray<FTransform> TransferSource,ArmSource;
    TArray<int32> Parents,RightToLeft;
    int32 Wrist[2]={INDEX_NONE,INDEX_NONE};
    FVector Across=FVector::RightVector;
    FVector PalmWidth[2]={FVector::RightVector,FVector::RightVector};
    void Initialize(const FReferenceSkeleton& Ref)
    {
        Reference=Ref.GetRefBonePose();Parents.SetNum(Reference.Num());RightToLeft.Init(INDEX_NONE,Reference.Num());
        Wrist[0]=Ref.FindBoneIndex(TEXT("hand_r"));Wrist[1]=Ref.FindBoneIndex(TEXT("hand_l"));
        for(int32 I=0;I<Reference.Num();++I)
        {
            Parents[I]=Ref.GetParentIndex(I);if(Parents[I]>=0)Reference[I]=Reference[I]*Reference[Parents[I]];
            FString Name=Ref.GetBoneName(I).ToString();
            if(Name.EndsWith(TEXT("_r")))RightToLeft[I]=Ref.FindBoneIndex(*(Name.LeftChop(2)+TEXT("_l")));
        }
        if(Wrist[0]>=0&&Wrist[1]>=0)Across=(Reference[Wrist[0]].GetLocation()-Reference[Wrist[1]].GetLocation()).GetSafeNormal();
        for(int32 Side=0;Side<2;++Side)
        {
            const FString Suffix=Side==0?TEXT("_r"):TEXT("_l");
            const int32 Index=Ref.FindBoneIndex(*(TEXT("index_01")+Suffix)),Pinky=Ref.FindBoneIndex(*(TEXT("pinky_01")+Suffix));
            if(Index>=0&&Pinky>=0)PalmWidth[Side]=(Reference[Pinky].GetLocation()-Reference[Index].GetLocation()).GetSafeNormal();
        }
    }
    FVector Reflect(const FVector& V) const {return V-2.*FVector::DotProduct(V,Across)*Across;}
    FQuat Reflect(const FQuat& Q) const
    {const FVector V=-Reflect(FVector(Q.X,Q.Y,Q.Z));return FQuat(V.X,V.Y,V.Z,Q.W).GetNormalized();}
    bool Under(int32 Bone,int32 Root) const
    {for(int32 P=Bone;P>=0;P=Parents[P])if(P==Root)return true;return false;}
    void Solve(TArray<FTransform>& Pose,int32 Side,const FTransform& Target,float Weight) const
    {
        const int32 W=Wrist[Side],E=Parents[W],U=Parents[E];ArmSource=Pose;const auto& Before=ArmSource;
        FTransform Root=Pose[U],Joint=Pose[E],Hand=Pose[W];
        const FVector RU=Reference[E].GetLocation()-Reference[U].GetLocation(),RL=Reference[W].GetLocation()-Reference[E].GetLocation();
        const double L1=RU.Size(),L2=RL.Size();const FVector Reach=Target.GetLocation()-Root.GetLocation();
        const FVector Shift=Reach.GetSafeNormal()*FMath::Max(0.,Reach.Size()-(L1+L2)*.94)*Weight;
        Root.AddToTranslation(Shift);Joint.AddToTranslation(Shift);Hand.AddToTranslation(Shift);
        // Keep the donor's elbow plane on entry instead of introducing an
        // unrelated bend as soon as the first transfer frame becomes active.
        const FVector Pole=Joint.GetLocation();
        AnimationCore::SolveTwoBoneIK(Root,Joint,Hand,Pole,Target.GetLocation(),L1,L2,false,1.,1.);
        // Distribute palm roll through the forearm instead of twisting the wrist.
        const FVector Axis=(Hand.GetLocation()-Joint.GetLocation()).GetSafeNormal();
        const FQuat PalmDelta=Target.GetRotation()*Reference[W].GetRotation().Inverse();
        const FVector PalmAcross=PalmDelta.RotateVector(PalmWidth[Side]);
        const FQuat Roll=FRotationMatrix::MakeFromXY(Axis,PalmAcross).ToQuat()*FRotationMatrix::MakeFromXY(RL,PalmWidth[Side]).ToQuat().Inverse();
        Joint.SetRotation(FQuat::Slerp(Joint.GetRotation(),Roll*Reference[E].GetRotation(),Weight).GetNormalized());Hand.SetRotation(Target.GetRotation());
        for(int32 I=0;I<Pose.Num();++I)
        {
            if(I==U)Pose[I]=Root;else if(I==E)Pose[I]=Joint;else if(I==W)Pose[I]=Hand;
            else if(Under(I,U))Pose[I]=Before[I].GetRelativeTransform(Before[Parents[I]])*Pose[Parents[I]];
        }
    }
    FTransform Apply(TArray<FTransform>& Pose,const FTransform Grip,float Fraction,const FTransform& AimFrame=FTransform::Identity) const
    {
        if(Wrist[0]<0||Wrist[1]<0||Pose.Num()!=Reference.Num()||Fraction<=0.f)return Grip;
        TransferSource=Pose;const auto& Before=TransferSource;const int32 R=Wrist[0],L=Wrist[1];
        const float Close=FMath::SmoothStep(0.f,.45f,Fraction),Move=FMath::SmoothStep(.45f,1.f,Fraction);
        // Mirror the authored grip before world-body aim, then apply the same
        // aim to both hands. Reflecting aim itself would counter-rotate the
        // supporting wrist against the bow when the player looks sideways.
        const FTransform UnaimedGrip=Grip.GetRelativeTransform(AimFrame),UnaimedLeft=Before[L].GetRelativeTransform(AimFrame);
        const FVector Centre=(Reference[R].GetLocation()+Reference[L].GetLocation())*.5;
        const FVector Shift=AimFrame.TransformVectorNoScale(-2.*Across*FVector::DotProduct(UnaimedGrip.GetLocation()-Centre,Across)*Move);
        FTransform MovedGrip=Grip;MovedGrip.AddToTranslation(Shift);
        FTransform Left=Before[L];Left.AddToTranslation(Shift);if(Move>0.f)Solve(Pose,1,Left,Move);
        FTransform Right=Before[R];
        const FQuat Deform=UnaimedLeft.GetRotation()*Reference[L].GetRotation().Inverse();
        FTransform Contact((AimFrame.GetRotation()*Reflect(Deform)*Reference[R].GetRotation()).GetNormalized(),
            MovedGrip.GetLocation()+AimFrame.TransformVectorNoScale(Reflect(UnaimedLeft.GetLocation()-UnaimedGrip.GetLocation()))
                +Grip.TransformVectorNoScale(FVector(0,0,-5.f)));
        // Support the lower end of the grip so both palms have room during
        // the two-handed transfer and the left can recover to its own seat.
        Right.Blend(Before[R],Contact,Close);Solve(Pose,0,Right,Close);
        // Mirror flexion in bind component axes, then return it to the right
        // parent's native frame. Keep native translations and auxiliary bones.
        for(int32 I=R+1;I<Pose.Num();++I)if(Under(I,R))
        {
            const int32 J=RightToLeft[I],P=Parents[I];FTransform Local=Before[I].GetRelativeTransform(Before[P]);
            if(J>=0&&Parents[J]>=0)
            {
                const int32 LP=Parents[J];const FQuat LLocal=Before[J].GetRelativeTransform(Before[LP]).GetRotation();
                const FQuat LBind=Reference[J].GetRelativeTransform(Reference[LP]).GetRotation();
                const FQuat Delta=Reference[LP].GetRotation()*(LLocal*LBind.Inverse())*Reference[LP].GetRotation().Inverse();
                const FQuat RDelta=Reference[P].GetRotation().Inverse()*Reflect(Delta)*Reference[P].GetRotation();
                const FQuat Target=RDelta*Reference[I].GetRelativeTransform(Reference[P]).GetRotation();
                Local.SetRotation(FQuat::Slerp(Local.GetRotation(),Target,Close).GetNormalized());
            }
            Pose[I]=Local*Pose[P];
        }
        return MovedGrip;
    }
};
