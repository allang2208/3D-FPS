#pragma once
#include "CoreMinimal.h"

// Contact trajectory and complete authored arm pose share the casting clock.
struct FStaffCastPose
{
    FTransform Contact=FTransform::Identity;
    FVector Shoulder=FVector(1,20,-24),Elbow=FVector(16,35,-39);
    // Idle, raised, windup, release, follow-through, run, then five primary-smash keys.
    static constexpr int32 ArmPoseCount=11;
    float ArmWeights[ArmPoseCount]={1,0,0,0,0,0};
};

namespace StaffCastMotion
{
    // Camera +Y is screen-right. Move the contact and its whole supporting
    // arm together; preserve the accepted V13 wrist and finger rotations.
    inline FVector PresentationOffset(){return FVector(0,4,0);}
    // Camera +X is forward. Move the charged contact and its supporting arm
    // together; the same contact also drives the charge focus at the staff tip.
    inline constexpr float ChargeForwardCm=10.f;
    inline FVector ChargeOffset(){return FVector(ChargeForwardCm,0,0);}
    inline constexpr float ReadySeconds=.20f;
    inline constexpr float SwingSeconds=.28f;
    inline constexpr float ContactSeconds=.18f;
    inline constexpr float HoldSeconds=.10f;
    inline constexpr float RecoverSeconds=.42f;
    inline constexpr float ImpactSeconds=.16f;

    inline float Ease(float T)
    {T=FMath::Clamp(T,0.f,1.f);return T*T*T*(T*(T*6.f-15.f)+10.f);}
    inline FStaffCastPose Pose(const FVector& Point,const FVector& Axis,const FVector& Shoulder,const FVector& Elbow,int32 ArmPose)
    {
        FStaffCastPose P;
        P.Contact=FTransform(FRotationMatrix::MakeFromZX(Axis.GetSafeNormal(),FVector::ForwardVector).ToQuat(),Point+PresentationOffset());
        P.Shoulder=Shoulder+PresentationOffset();P.Elbow=Elbow+PresentationOffset();
        for(int32 I=0;I<FStaffCastPose::ArmPoseCount;++I)P.ArmWeights[I]=I==ArmPose?1.f:0.f;
        return P;
    }
    inline FStaffCastPose Raised()
    {
        // Lift the hand while leaning the long upper shaft forward into the view.
        return Pose(FVector(39,22,-8)+ChargeOffset(),FVector(.52,-.10,.848),
            FVector(3,22,-20)+ChargeOffset(),FVector(19,37,-24)+ChargeOffset(),1);
    }
    inline FStaffCastPose Blend(const FStaffCastPose& A,const FStaffCastPose& B,float Alpha)
    {
        FStaffCastPose P;
        P.Contact=FTransform(FQuat::Slerp(A.Contact.GetRotation(),B.Contact.GetRotation(),Alpha).GetNormalized(),
            FMath::Lerp(A.Contact.GetLocation(),B.Contact.GetLocation(),Alpha));
        P.Shoulder=FMath::Lerp(A.Shoulder,B.Shoulder,Alpha);P.Elbow=FMath::Lerp(A.Elbow,B.Elbow,Alpha);
        for(int32 I=0;I<FStaffCastPose::ArmPoseCount;++I)P.ArmWeights[I]=FMath::Lerp(A.ArmWeights[I],B.ArmWeights[I],Alpha);
        return P;
    }
    inline FStaffCastPose Raise(const FStaffCastPose& Entry,float T)
    {
        const float U=Ease(T);auto P=Blend(Entry,Raised(),U);
        const float Arc=16.f*U*U*(1.f-U)*(1.f-U);
        P.Contact.AddToTranslation(FVector(-3,2,1)*Arc);
        // Shoulder leads, elbow supports the lift, then the shaft settles.
        P.Shoulder=FMath::Lerp(Entry.Shoulder,Raised().Shoulder,Ease(T/.84f));
        P.Elbow=FMath::Lerp(Entry.Elbow,Raised().Elbow,Ease((T-.025f)/.92f));return P;
    }
    inline FStaffCastPose Swing(float Age)
    {
        const auto Windup=Pose(FVector(37,23,-7)+ChargeOffset(),FVector(.44,-.12,.890),
            FVector(3,23,-20)+ChargeOffset(),FVector(18,38,-24)+ChargeOffset(),2);
        const auto Contact=Pose(FVector(55,17,-12),FVector(.940,-.080,.332),FVector(7,21,-23),FVector(30,35,-30),3);
        const auto Follow=Pose(FVector(53,15,-16),FVector(.960,-.100,.262),FVector(6,21,-24),FVector(28,34,-32),4);
        constexpr float Anticipation=.035f;
        if(Age<Anticipation)return Blend(Raised(),Windup,Ease(Age/Anticipation));
        if(Age<ContactSeconds)return Blend(Windup,Contact,Ease((Age-Anticipation)/(ContactSeconds-Anticipation)));
        return Blend(Contact,Follow,Ease((Age-ContactSeconds)/(SwingSeconds-ContactSeconds)));
    }
    inline FStaffCastPose WithImpact(FStaffCastPose P,float Age)
    {
        if(Age<=0.f||Age>=ImpactSeconds)return P;
        const float Fade=Ease(Age/.012f)*(1.f-Ease(Age/ImpactSeconds));
        const FVector Shift=FVector(-.9f,0,.25f)*FMath::Sin(Age*2.f*PI*9.f)*Fade;
        P.Contact.AddToTranslation(Shift);P.Shoulder+=Shift;P.Elbow+=Shift;return P;
    }
    inline FStaffCastPose Recover(const FStaffCastPose& From,const FStaffCastPose& Current,float T)
    {
        const float U=Ease(T);auto P=Blend(From,Current,U);
        P.Contact.AddToTranslation(FVector(0,2,2)*(16.f*U*U*(1.f-U)*(1.f-U)));return P;
    }
    inline FVector Tip(const FStaffCastPose& P)
    {return P.Contact.TransformPosition(FVector(0,0,48));}
    inline FVector Focus(const FStaffCastPose& P)
    {return Tip(P)+FVector(16,0,0);}
}
