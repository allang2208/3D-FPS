#pragma once
#include "StaffPrimaryKeys.h"

// Normalized action time follows the equipped attack interval. Hit stop uses
// real seconds and pauses only this action; aim, movement and enemies keep moving.
namespace StaffPrimaryAttackMotion
{
    inline constexpr float StrikeStart=.40f,ContactTime=.60f,StrikeEnd=.70f;
    inline constexpr float FleshStopSeconds=.035f,WallStopSeconds=.045f;
    inline constexpr float ImpactSeconds=.22f;

    inline float SegmentAlpha(int32 Segment,float T)
    {
        T=FMath::Clamp(T,0.f,1.f);
        if(Segment==2)return T*T*(2.f-T); // Shoulder-driven acceleration into contact.
        if(Segment==3)return 1.f-FMath::Pow(1.f-T,3.f); // Brake the heavy head after contact.
        return StaffCastMotion::Ease(T);
    }
    inline FStaffCastPose Key(int32 Index)
    {
        FStaffCastPose P;P.Contact=StaffPrimaryKeys::Contacts[Index];
        for(int32 I=0;I<FStaffCastPose::ArmPoseCount;++I)P.ArmWeights[I]=I==6+Index?1.f:0.f;
        return P;
    }
    inline FStaffCastPose Sample(const FStaffCastPose& Entry,const FStaffCastPose& Carry,float T)
    {
        FStaffCastPose From=Entry;float Start=0.f;
        for(int32 I=0;I<5;++I)
        {
            const auto To=Key(I);const float End=StaffPrimaryKeys::Times[I];
            if(T<End)return StaffCastMotion::Blend(From,To,SegmentAlpha(I,(T-Start)/(End-Start)));
            From=To;Start=End;
        }
        return StaffCastMotion::Blend(From,Carry,StaffCastMotion::Ease((T-Start)/(1.f-Start)));
    }
    inline FStaffCastPose Recoil(FStaffCastPose P,float Age,float Strength)
    {
        if(Age<0.f||Age>=ImpactSeconds)return P;
        const float Wave=FMath::Sin(Age*65.f)*FMath::Exp(-22.f*Age)*(1.f-StaffCastMotion::Ease(Age/ImpactSeconds))*Strength;
        // Translate the contact and entire supporting chain together, never loosen fingers.
        P.Contact.AddToTranslation(FVector(-1.5f,.25f,.65f)*Wave);
        return P;
    }
    inline void Camera(float T,float ImpactAge,float Strength,FVector& Location,FRotator& Rotation)
    {
        Location=FVector::ZeroVector;Rotation=FRotator::ZeroRotator;
        if(T>=0.f)
        {
            const FVector Points[]={FVector::ZeroVector,FVector(-.4f,.15f,.5f),FVector(-1.f,.3f,1.1f),
                FVector(.9f,0,-.65f),FVector(1.1f,-.1f,-1.1f),FVector(-.2f,.1f,.15f),FVector::ZeroVector};
            const FRotator Turns[]={FRotator::ZeroRotator,FRotator(.6f,0,-.35f),FRotator(1.6f,.2f,-.7f),
                FRotator(-2.1f,-.15f,.45f),FRotator(-2.8f,-.2f,.6f),FRotator(.35f,.05f,-.1f),FRotator::ZeroRotator};
            float Start=0;
            for(int32 I=0;I<6;++I)
            {
                const float End=I<5?StaffPrimaryKeys::Times[I]:1.f;
                if(T<=End)
                {
                    const float U=SegmentAlpha(I,(T-Start)/(End-Start));
                    Location=FMath::Lerp(Points[I],Points[I+1],U);
                    Rotation=FMath::Lerp(Turns[I],Turns[I+1],U);break;
                }
                Start=End;
            }
        }
        if(ImpactAge<0.f||ImpactAge>=ImpactSeconds)return;
        const float Fade=1.f-StaffCastMotion::Ease(ImpactAge/ImpactSeconds);
        const float Kick=FMath::Exp(-18.f*ImpactAge)*FMath::Cos(55.f*ImpactAge)*Fade*Strength;
        const float Rattle=FMath::Exp(-25.f*ImpactAge)*FMath::Sin(110.f*ImpactAge)*Fade*Strength;
        Location+=FVector(-1.8f,.18f,-.75f)*Kick+FVector(0,.18f,.12f)*Rattle;
        Rotation+=FRotator(-3.6f,.45f,.65f)*Kick+FRotator(.3f,-.22f,.25f)*Rattle;
    }
}
