#pragma once
#include "FPSPlayerBodyTypes.h"

// Independent world-body authoring, in Manny mesh centimetres (+Y forward).
// These curves consume gameplay progress; they never change movement or damage.
namespace FPSBodyPoses
{
inline float Smooth(float T){T=FMath::Clamp(T,0.f,1.f);return T*T*(3.f-2.f*T);}
inline float Progress(const FFPSBodyState& S,float Clock)
{
    return S.bHasActionProgress?FMath::Clamp(S.ActionProgress,0.f,1.f):
        (S.ActionDuration>0.f?FMath::Clamp((Clock-S.ActionStartedAt)/S.ActionDuration,0.f,1.f):0.f);
}
inline float Pulse(float T,float Contact)
{
    Contact=FMath::Clamp(Contact,.05f,.9f);
    return T<Contact?Smooth(T/Contact):1.f-Smooth((T-Contact)/(1.f-Contact));
}
inline bool Traversing(EFPSBodyMotion Motion){return Motion==EFPSBodyMotion::Vault||Motion==EFPSBodyMotion::Mantle;}
inline float PistolBashLift(float T,float Contact)
{
    Contact=FMath::Clamp(Contact,.1f,.85f);
    return Smooth(T/FMath::Max(.01f,Contact*.7f))*(1.f-Smooth((T-Contact)/(1.f-Contact)));
}

inline FTransform RightHand(const FFPSBodyState& S,float T,float Crouch,float Aim,float Sprint,const FTransform& Base)
{
    FTransform Result=Base;
    const bool Melee=S.Family==TEXT("Melee")||S.Family==TEXT("Tool");
    const bool Gun=S.Family==TEXT("Rifle")||S.Family==TEXT("Pistol");
    const FVector Rest(-18,43,111-40*Crouch);
    FVector Target=Melee?Rest:Base.GetLocation();
    FQuat Rotation=Base.GetRotation();
    const auto Turn=[&](FVector Axis,float Angle){Rotation=FQuat(Axis,Angle)*Rotation;};
    const float Edge=Smooth(T/.10f)*(1.f-Smooth((T-.85f)/.15f));
    const float Hit=Pulse(T,S.ContactFraction);
    if(Gun&&S.Action!=EFPSBodyAction::Reload&&S.Action!=EFPSBodyAction::ReloadEmpty&&S.Action!=EFPSBodyAction::Equip)
    {
        Target+=FVector(0,-7,-12)*(1.f-Aim);
        Target+=FVector(-7,-10,-10)*Sprint;
        Turn(FVector::UpVector,-.35f*Sprint);
        Turn(FVector::ForwardVector,.12f*(1.f-Aim)+.2f*Sprint);
    }
    if(Melee&&S.Action==EFPSBodyAction::None)
    {
        Target=FMath::Lerp(Rest,FVector(-22,22,148-40*Crouch),Sprint);
        Turn(FVector::ForwardVector,.35f*Sprint);
    }
    switch(S.Action)
    {
    case EFPSBodyAction::Guard:
        Target=FMath::Lerp(Rest,FVector(-8,38,137-40*Crouch),Smooth(S.ActionWeight));
        Turn(FVector::UpVector,PI*.25f*Smooth(S.ActionWeight));break;
    case EFPSBodyAction::GuardHit:
        Target=FVector(-8,38,137-40*Crouch)+FVector(-5,-12,7)*Pulse(T,.18f);
        Turn(FVector::UpVector,PI*.25f);break;
    case EFPSBodyAction::GuardBreak:
        Target=FMath::Lerp(FVector(-8,38,137-40*Crouch),Rest+FVector(-17,-14,-16),Smooth(T/.4f));
        Turn(FVector::ForwardVector,.55f*Smooth(T));break;
    case EFPSBodyAction::Charge:
    {
        const float Load=Smooth(T/.8f)*S.ActionWeight;
        Target=FMath::Lerp(Rest,FVector(-38,17,151-40*Crouch),Load);
        Turn(FVector::UpVector,-.6f*Load);break;
    }
    case EFPSBodyAction::Strike:
    {
        const bool Reverse=S.ActionVariant==TEXT("Slash2");
        const FVector A(Reverse?32.f:-42.f,29,138-40*Crouch),B(Reverse?-36.f:31.f,59,111-40*Crouch);
        Target=FMath::Lerp(Rest,FMath::Lerp(A,B,Hit),Edge);
        Turn(FVector::UpVector,(Reverse?-1.f:1.f)*(1.4f*Hit-.5f)*Edge);break;
    }
    case EFPSBodyAction::HeavyStrike:
        if(S.ActionVariant==TEXT("shovel"))
        {
            Target=FMath::Lerp(Rest,FMath::Lerp(FVector(-18,32,116-40*Crouch),FVector(-12,66,70-40*Crouch),Hit),Edge);
            Turn(FVector::ForwardVector,-.65f*Hit*Edge);
        }
        else
        {
            const FVector Raised(-10,22,166-40*Crouch),Contact(-12,63,96-40*Crouch);
            Target=FMath::Lerp(Rest,FMath::Lerp(Raised,Contact,Hit),Edge);
            Turn(FVector::ForwardVector,-1.15f*Hit*Edge);
        }
        break;
    case EFPSBodyAction::Thrust:
        Target=Rest+FVector(0,32,5)*Hit;
        Turn(FVector::ForwardVector,-.3f*Hit);break;
    case EFPSBodyAction::Pommel:
        Target=Rest+FVector(9,25,23)*Hit;
        Turn(FVector::ForwardVector,1.1f*Hit);break;
    case EFPSBodyAction::Whirlwind:
    {
        const float Entry=Smooth(T/FMath::Max(.01f,S.ContactFraction));
        const float Exit=1.f-Smooth((T-S.ReleaseFraction)/FMath::Max(.01f,1.f-S.ReleaseFraction));
        // Actor yaw already follows the authoritative spin; do not rotate twice.
        Target=FMath::Lerp(Rest,FVector(-35,52,122-40*Crouch),Entry*Exit);
        Turn(FVector::UpVector,-.65f*Entry*Exit);break;
    }
    case EFPSBodyAction::ToolRecover:
        Target=FMath::Lerp(FVector(-12,63,96-40*Crouch),Rest,Smooth(T));
        Turn(FVector::ForwardVector,-1.15f*(1.f-Smooth(T)));break;
    case EFPSBodyAction::GunBash:
        if(S.ActionVariant==TEXT("RifleBash"))
        {
            Target+=FVector(18,24,8)*Hit;
            Turn(FVector::UpVector,-1.15f*Hit);
        }
        else
        {
            const float Lift=PistolBashLift(T,S.ContactFraction);
            Target+=FVector(3,20,8)*Hit+FVector(0,-5,25)*(Lift-Hit*.5f);
            Turn(FVector::ForwardVector,.8f*Lift);
        }
        break;
    case EFPSBodyAction::Inspect:
        Target+=FVector(7,-9,13)*Edge;
        Turn(FVector::UpVector,.55f*FMath::Sin(2.f*PI*T)*Edge);
        Turn(FVector::RightVector,.35f*Edge);break;
    case EFPSBodyAction::Equip:
        if(Melee)
        {
            Target+=FVector(-14,-10,-48)*(1.f-Smooth(T/.8f));
            Turn(FVector::ForwardVector,.55f*(1.f-Smooth(T/.8f)));
        }
        break;
    default:break;
    }
    Result.SetLocation(Target);Result.SetRotation(Rotation.GetNormalized());return Result;
}

inline FTransform CastHand(const FFPSBodyState& S,float Crouch,const FTransform& Base)
{
    // Recovery is sampled from the actual entry hand by the animation node.
    if(S.ActionVariant==TEXT("Recover"))return Base;
    const float T=Smooth(S.ActionProgress);FTransform Result=Base;
    const FVector Gather(32,40,136-40*Crouch),Ready(27,32,147-40*Crouch),Push(27,70,144-40*Crouch);
    FVector Target=Gather;
    float Weight=1.f;
    if(S.ActionVariant==TEXT("Gather")){Target=Gather;Weight=T;}
    else if(S.ActionVariant==TEXT("Ready")){Target=Ready;Weight=T;}
    else if(S.ActionVariant==TEXT("Release"))Target=FMath::Lerp(Ready,Push,FMath::Clamp(S.ReleaseFraction,0.f,1.f));
    Result.SetLocation(FMath::Lerp(Base.GetLocation(),Target,Weight));return Result;
}
}
