#pragma once
#include "CoreMinimal.h"
#include "../Weapons/RuneSwordHeavyRhythm.h"

namespace WarhammerHeavy
{
    inline constexpr float ChargeSeconds=RuneSwordHeavyRhythm::ChargeSeconds;
    inline constexpr float Contact=RuneSwordHeavyRhythm::ContactEnd;
    inline constexpr float FloorHoldSeconds=.7f;
    inline constexpr float HoldEnd=Contact+FloorHoldSeconds;
    inline constexpr float Duration=HoldEnd+.5f;
    inline constexpr float Radius=300.f;
    inline constexpr float WaveSeconds=.36f;
    inline constexpr float Arc=120.f;
    inline constexpr float DamageMultiplier=2.5f;
    inline constexpr float LandingForward=125.f;
    inline constexpr float WaistBendDegrees=62.f;
    inline constexpr float PlantedViewPitch=-52.f;
    inline float ChargeSource(float Held)
    {
        if(Held<=.65f)return .13f*FMath::SmoothStep(0.f,.65f,Held);
        return FMath::Lerp(.13f,.188f,FMath::SmoothStep(.65f,1.6f,Held));
    }
    inline float FloorWeight(float Time)
    {
        return FMath::SmoothStep(.025f,Contact,Time)*(1.f-FMath::SmoothStep(HoldEnd,Duration,Time));
    }
    inline float PostureEase(float Start,float End,float Time)
    {
        const float U=FMath::Clamp((Time-Start)/(End-Start),0.f,1.f);
        return U*U*U*(10.f+U*(-15.f+6.f*U));
    }
    inline float AnchorWeight(float Time){return 1.f-PostureEase(HoldEnd,Duration,Time);}
    inline float BodyWeight(float Time){return FMath::SmoothStep(0.f,Contact,Time)*AnchorWeight(Time);}
    inline FVector EyeOffset(float Time){return FVector(20.f,0.f,-52.f)*BodyWeight(Time);}
    inline float ViewWeight(float Time){return FMath::SmoothStep(.025f,Contact+.10f,Time)*AnchorWeight(Time);}
    inline float RealDuration(float Rate){return (Duration-FloorHoldSeconds)/Rate+FloorHoldSeconds;}
    inline float SourceTime(float RealTime,float Rate)
    {
        const float Hit=Contact/Rate;
        if(RealTime<=Hit)return RealTime*Rate;
        if(RealTime<=Hit+FloorHoldSeconds)return Contact+RealTime-Hit;
        return HoldEnd+(RealTime-Hit-FloorHoldSeconds)*Rate;
    }
}
namespace WarhammerSprint
{
    inline constexpr float CarryTransitionSeconds=.5f;
    inline constexpr float LiftSeconds=.25f;
}
