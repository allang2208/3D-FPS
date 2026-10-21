#pragma once
#include "CoreMinimal.h"
#include "ReferenceSkeleton.h"
#include "TwoBoneIK.h"

namespace SpellbookPistolArm
{
struct FJoints
{
    int32 Clavicle,Upper,Lower,Hand,Twist01,Twist02;
};

// Native lengths, one elbow hinge and a fixed contact hand. Every helper is
// reconstructed with its own bind, including upperarm twist children.
inline void Solve(const FReferenceSkeleton& Skeleton,const TArray<FTransform>& Reference,
    const TArray<FTransform>& Source,const TArray<int32>& Bones,const FJoints& J,
    FVector Shoulder,const FVector& RequestedWrist,const FVector& Pole,const FQuat& HandRotation,
    float HandRollDegrees,float CanonicalWeight,TArray<FTransform>& Target)
{
    const FVector RU=Reference[J.Lower].GetLocation()-Reference[J.Upper].GetLocation();
    const FVector RL=Reference[J.Hand].GetLocation()-Reference[J.Lower].GetLocation();
    const double UpperLength=RU.Size(),LowerLength=RL.Size();
    const FVector Reach=RequestedWrist-Shoulder;
    const double Maximum=(UpperLength+LowerLength)*.94;
    if(Reach.Size()>Maximum)Shoulder+=Reach.GetSafeNormal()*(Reach.Size()-Maximum);
    FVector Elbow,Wrist;
    AnimationCore::SolveTwoBoneIK(Shoulder,Shoulder+RU,Shoulder+RU+RL,Pole,RequestedWrist,
        Elbow,Wrist,UpperLength,LowerLength,false,1.,1.);
    const FVector UD=(Elbow-Shoulder).GetSafeNormal(),LD=(Wrist-Elbow).GetSafeNormal();
    const FVector Plane=(UD^LD).GetSafeNormal(),RestPlane=(RU^RL).GetSafeNormal();
    const auto Frame=[](const FVector& D,const FVector& N){return FRotationMatrix::MakeFromXZ(D,N).ToQuat();};
    const FQuat UpperDeform=Frame(UD,Plane)*Frame(RU,RestPlane).Inverse();
    const FQuat LowerDeform=Frame(LD,Plane)*Frame(RL,RestPlane).Inverse();
    FQuat UpperRotation=UpperDeform*Reference[J.Upper].GetRotation();
    FQuat LowerRotation=LowerDeform*Reference[J.Lower].GetRotation();
    if(CanonicalWeight<1.f)
    {
        // Fade from the live native arm without snapping its roll. Both
        // rotations map the bone axis to the same solved segment direction.
        const FVector SU=Source[J.Lower].GetLocation()-Source[J.Upper].GetLocation();
        const FVector SL=Source[J.Hand].GetLocation()-Source[J.Lower].GetLocation();
        const FVector SP=(SU^SL).GetSafeNormal();
        UpperRotation=FQuat::Slerp(Frame(UD,Plane)*Frame(SU,SP).Inverse()*Source[J.Upper].GetRotation(),UpperRotation,CanonicalWeight);
        LowerRotation=FQuat::Slerp(Frame(LD,Plane)*Frame(SL,SP).Inverse()*Source[J.Lower].GetRotation(),LowerRotation,CanonicalWeight);
    }
    Target=Source;
    Target[J.Upper].SetLocation(Shoulder);Target[J.Upper].SetRotation(UpperRotation.GetNormalized());
    Target[J.Lower].SetLocation(Elbow);Target[J.Lower].SetRotation(LowerRotation.GetNormalized());
    Target[J.Hand].SetLocation(Wrist);
    Target[J.Hand].SetRotation((FQuat(LD,FMath::DegreesToRadians(HandRollDegrees))*HandRotation).GetNormalized());
    Target[J.Clavicle].AddToTranslation(Shoulder-Source[J.Upper].GetLocation());
    const FQuat HandDeform=Target[J.Hand].GetRotation()*Reference[J.Hand].GetRotation().Inverse();
    const FQuat FinalLowerDeform=Target[J.Lower].GetRotation()*Reference[J.Lower].GetRotation().Inverse();
    FQuat Swing,Twist;(HandDeform*FinalLowerDeform.Inverse()).ToSwingTwist(LD,Swing,Twist);
    Twist.Normalize();if(Twist.W<0.)Twist=Twist*-1.;
    for(const int32 I:Bones)
    {
        if(I<0||I==J.Clavicle||I==J.Upper||I==J.Lower||I==J.Hand)continue;
        const int32 Parent=Skeleton.GetParentIndex(I);
        // Hand descendants retain the saved grasp. Arm helpers use native bind
        // locals so previously applied forearm roll is never added twice.
        const bool Finger=Skeleton.BoneIsChildOf(I,J.Hand);
        const auto& Donor=Finger?Source:Reference;
        Target[I]=Donor[I].GetRelativeTransform(Donor[Parent])*Target[Parent];
        if(I==J.Twist01||I==J.Twist02)
        {
            const FQuat Roll=I==J.Twist01?Twist:FQuat::Slerp(FQuat::Identity,Twist,.5f);
            Target[I].SetRotation((Roll*Target[I].GetRotation()).GetNormalized());
        }
    }
}
}
