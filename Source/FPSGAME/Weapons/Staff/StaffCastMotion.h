#pragma once
#include "CoreMinimal.h"

// Contact trajectory and complete authored arm pose share the casting clock.
struct FStaffCastPose
{
    FTransform Contact=FTransform::Identity;
    FVector Shoulder=FVector(1,20,-24),Elbow=FVector(16,35,-39);
    // Idle, raised, windup, release, follow-through, run, then five action-bank
    // keys: primary smash or charge flow selected by the active staff action.
    static constexpr int32 ArmPoseCount=11;
    float ArmWeights[ArmPoseCount]={1,0,0,0,0,0};
    // V30 continuous 60 Hz primary swing curve sample (PrimaryWeight=0 disables).
    float PrimaryPhase=-1.f;
    float PrimaryWeight=0.f;
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
        P.PrimaryWeight=FMath::Lerp(A.PrimaryWeight,B.PrimaryWeight,Alpha);
        P.PrimaryPhase=A.PrimaryWeight>0.f&&B.PrimaryWeight>0.f
            ?FMath::Lerp(A.PrimaryPhase,B.PrimaryPhase,Alpha)
            :(B.PrimaryWeight>0.f?B.PrimaryPhase:A.PrimaryPhase);
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

    // Dedicated Absolute Zero staff animation: vertical upright lift (0..86% channel)
    // with mounting cryo tremor -> rapid vertical ground slam (86..100%) -> heavy
    // ground-thud hit-stop & smooth return to carry (0..0.44 s post-detonation).
    inline constexpr float AbsoluteZeroSlamStart=.86f;
    inline constexpr float AbsoluteZeroSlamHold=.12f;
    inline constexpr float AbsoluteZeroSlamRecoverSeconds=.44f;

    inline FStaffCastPose AbsoluteZeroLiftedPose()
    {
        return Pose(FVector(42,15,5),FVector(.11f,-.04f,.993f),
            FVector(3,21,-18),FVector(21,34,-17),1);
    }
    inline FStaffCastPose AbsoluteZeroSlammedPose()
    {
        return Pose(FVector(47,13,-24),FVector(.16f,-.04f,.986f),
            FVector(6,20,-27),FVector(25,33,-38),4);
    }
    inline FStaffCastPose AbsoluteZeroChannel(const FStaffCastPose& Entry,float Alpha,float Age)
    {
        Alpha=FMath::Clamp(Alpha,0.f,1.f);
        const auto Lifted=AbsoluteZeroLiftedPose();
        if(Alpha<AbsoluteZeroSlamStart)
        {
            const float LiftT=FMath::Clamp(Alpha/.24f,0.f,1.f);
            auto P=Blend(Entry,Lifted,Ease(LiftT));
            const float HoldT=FMath::Clamp((Alpha-.24f)/FMath::Max(.01f,AbsoluteZeroSlamStart-.24f),0.f,1.f);
            // Draw slightly higher with rising cryo tremor before slamming down.
            const float PeakLift=3.6f*Ease(HoldT);
            const float Tremor=HoldT*HoldT;
            const FVector Jitter(FMath::Sin(Age*43.f)*.24f*Tremor,FMath::Cos(Age*37.f)*.28f*Tremor,PeakLift+FMath::Sin(Age*53.f)*.34f*Tremor);
            P.Contact.AddToTranslation(Jitter);
            P.Shoulder+=Jitter*.45f;P.Elbow+=Jitter*.75f;
            return P;
        }
        auto Peak=Lifted;
        Peak.Contact.AddToTranslation(FVector(0,0,3.6f));
        Peak.Shoulder+=FVector(0,0,1.6f);Peak.Elbow+=FVector(0,0,2.7f);
        const float SlamT=FMath::Clamp((Alpha-AbsoluteZeroSlamStart)/FMath::Max(.01f,1.f-AbsoluteZeroSlamStart),0.f,1.f);
        // Accelerating vertical drive straight into the earth at exact detonation (Alpha=1).
        const float Plunge=FMath::Pow(SlamT,1.85f);
        return Blend(Peak,AbsoluteZeroSlammedPose(),Plunge);
    }
    inline FStaffCastPose AbsoluteZeroRecover(const FStaffCastPose& Current,float SlamAge)
    {
        auto Slammed=AbsoluteZeroSlammedPose();
        if(SlamAge<AbsoluteZeroSlamHold)
        {
            const float Rattle=FMath::Sin(SlamAge*62.f)*FMath::Exp(-SlamAge*18.f);
            const FVector Shift(0.f,Rattle*.25f,Rattle*1.45f);
            Slammed.Contact.AddToTranslation(Shift);Slammed.Shoulder+=Shift*.4f;Slammed.Elbow+=Shift*.7f;
            return Slammed;
        }
        const float RecT=FMath::Clamp((SlamAge-AbsoluteZeroSlamHold)/FMath::Max(.01f,AbsoluteZeroSlamRecoverSeconds-AbsoluteZeroSlamHold),0.f,1.f);
        return Recover(Slammed,Current,RecT);
    }
    inline void AbsoluteZeroCamera(bool bChanneling,float Alpha,float SlamAge,FVector& OutLoc,FRotator& OutRot,float* OutFov)
    {
        OutLoc=FVector::ZeroVector;OutRot=FRotator::ZeroRotator;if(OutFov)*OutFov=0.f;
        if(bChanneling)
        {
            Alpha=FMath::Clamp(Alpha,0.f,1.f);
            if(Alpha<AbsoluteZeroSlamStart)
            {
                const float T=Ease(Alpha/AbsoluteZeroSlamStart);
                OutLoc=FVector(-.6f*T,0.f,.85f*T);
                OutRot=FRotator(1.35f*T,0.f,-.35f*T);
                if(OutFov)*OutFov=-2.4f*T;
            }
            else
            {
                const float S=FMath::Pow(FMath::Clamp((Alpha-AbsoluteZeroSlamStart)/FMath::Max(.01f,1.f-AbsoluteZeroSlamStart),0.f,1.f),1.7f);
                OutLoc=FMath::Lerp(FVector(-.6f,0.f,.85f),FVector(.9f,0.f,-2.1f),S);
                OutRot=FRotator(FMath::Lerp(1.35f,-2.6f,S),0.f,FMath::Lerp(-.35f,.55f,S));
                if(OutFov)*OutFov=FMath::Lerp(-2.4f,1.2f,S);
            }
            return;
        }
        if(SlamAge>=0.f&&SlamAge<.36f)
        {
            const float Decay=FMath::Exp(-SlamAge*10.5f);
            const float Wave=FMath::Cos(SlamAge*25.f)*Decay;
            OutLoc=FVector(.65f*Decay,0.f,-1.85f*Wave);
            OutRot=FRotator(-2.8f*Wave,0.f,.45f*Wave);
            if(OutFov)*OutFov=3.4f*FMath::Exp(-SlamAge*9.f);
        }
    }
}
