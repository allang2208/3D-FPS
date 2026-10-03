#pragma once
#include "FPSPlayerBodyPoses.h"

/** Body effort accompanying the existing weapon's source clock. No gameplay/root motion. */
namespace FPSBodyMelee
{
inline bool Active(const FFPSBodyState& S)
{
    if(S.Family!=TEXT("Melee")&&S.Family!=TEXT("Tool")&&S.Family!=TEXT("Staff"))return false;
    switch(S.Action)
    {
    case EFPSBodyAction::Strike:case EFPSBodyAction::HeavyStrike:case EFPSBodyAction::Thrust:
    case EFPSBodyAction::Pommel:case EFPSBodyAction::Whirlwind:case EFPSBodyAction::Charge:
    case EFPSBodyAction::ToolRecover:return true;
    default:return false;
    }
}
struct FPose
{
    FVector Pelvis=FVector::ZeroVector;
    FVector Feet[2]={FVector::ZeroVector,FVector::ZeroVector};
    float HipYaw=0.f,ChestYaw=0.f,ChestPitch=0.f,ChestRoll=0.f;
};
inline FPose Sample(const FFPSBodyState& S,float T)
{
    using namespace FPSBodyPoses;
    FPose P;if(!Active(S))return P;
    if(S.Action==EFPSBodyAction::Charge)
    {
        const float W=Smooth(T/.8f)*S.ActionWeight;
        P.HipYaw=-9.f*W;P.ChestYaw=-24.f*W;P.ChestPitch=7.f*W;
        P.Pelvis=FVector(3,-5,-5)*W;return P;
    }
    if(S.Action==EFPSBodyAction::Whirlwind)
    {
        const float W=Smooth(T/FMath::Max(.01f,S.ContactFraction))*(1.f-Smooth((T-S.ReleaseFraction)/FMath::Max(.01f,1.f-S.ReleaseFraction)));
        // The actor owns the spin. Widen/brace without rotating a second time.
        P.ChestPitch=-9.f*W;P.Pelvis=FVector(0,0,-6)*W;
        P.Feet[0]=FVector(-5,5,0)*W;P.Feet[1]=FVector(5,-5,0)*W;return P;
    }
    if(S.Action==EFPSBodyAction::ToolRecover)
    {
        const float W=1.f-Smooth(T);P.ChestPitch=-15.f*W;P.Pelvis=FVector(0,5,-4)*W;
        P.Feet[0]=FVector(0,12,0)*W;return P;
    }
    const bool DashCut=Dash(S);
    const float Time=DashCut?DashProgress(S,T):T;
    const float Contact=FMath::Clamp(DashCut?DashContact(S):S.ContactFraction,.12f,.8f);
    const float Release=FMath::Clamp(DashCut?(S.ReleaseFraction-S.ActionEntryFraction)/FMath::Max(.01f,1.f-S.ActionEntryFraction):S.ReleaseFraction,Contact+.03f,.92f);
    const float LoadEnd=Contact*.75f;
    const float Gather=Smooth(Time/FMath::Max(.01f,LoadEnd));
    const float Cut=Smooth((Time-LoadEnd)/FMath::Max(.01f,Release-LoadEnd));
    const float Recover=1.f-Smooth((Time-Release)/FMath::Max(.01f,1.f-Release));
    const float Load=Gather*(1.f-Cut),Follow=Cut*Recover;
    const float Drive=Pulse(Time,Contact);
    int32 Lead=0;float Stride=12.f;
    if(S.Action==EFPSBodyAction::Thrust||S.Action==EFPSBodyAction::Pommel)
    {
        const bool Thrust=S.Action==EFPSBodyAction::Thrust;
        P.HipYaw=FMath::Lerp(-6.f,10.f,Cut)*Gather*Recover;
        P.ChestYaw=FMath::Lerp(-13.f,16.f,Cut)*Gather*Recover;
        P.ChestPitch=5.f*Load-(Thrust?13.f:10.f)*Follow;
        P.Pelvis=FVector(0,-4,0)*Load+FVector(0,Thrust?9.f:6.f,-5)*Follow;
        Stride=Thrust?22.f:13.f;
    }
    else if((S.Action==EFPSBodyAction::Strike&&S.Family!=TEXT("Staff"))||S.ActionVariant==TEXT("HeavyRelease"))
    {
        const float Side=S.ActionVariant==TEXT("Slash2")?-1.f:1.f;
        const float Strength=S.Action==EFPSBodyAction::HeavyStrike?1.3f:1.f;
        P.ChestYaw=Side*(-27.f*Load+34.f*Follow)*Strength;
        P.HipYaw=Side*(-10.f*Load+14.f*Follow)*Strength;
        P.ChestPitch=4.f*Load-8.f*Follow;P.ChestRoll=Side*4.f*Follow;
        P.Pelvis=FVector(Side*4,5,-4)*Drive;Lead=Side>0.f?0:1;
    }
    else if(S.ActionVariant==TEXT("Uppercut"))
    {
        P.ChestPitch=-12.f*Load+6.f*Follow;P.ChestYaw=-18.f*Load+20.f*Follow;
        P.HipYaw=P.ChestYaw*.3f;P.Pelvis=FVector(0,4,-9)*Load;
        Stride=16.f;
    }
    else
    {
        // Downward sword/tool strikes load backward, then fold at the contact.
        P.ChestPitch=10.f*Load-19.f*Follow;P.ChestYaw=-12.f*Load+10.f*Follow;
        P.HipYaw=P.ChestYaw*.35f;P.Pelvis=FVector(0,-3,-2)*Load+FVector(0,7,-7)*Follow;
        Stride=18.f;
    }
    if(!DashCut) // The existing dash layer already supplies its committed stride.
    {
        const float Plant=FMath::Sin(PI*FMath::Clamp(Time/Contact,0.f,1.f));
        P.Feet[Lead]=FVector(0,Stride*Drive,FMath::Max(0.f,Plant)*6.f);
        P.Feet[1-Lead]=FVector(0,-5.f*Drive,0);
    }
    else P.Pelvis=FVector::ZeroVector;
    return P;
}
}
