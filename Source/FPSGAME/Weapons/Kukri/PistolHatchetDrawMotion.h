#pragma once
#include "CoreMinimal.h"

namespace PistolHatchetDrawMotion
{
    // Author seconds, advanced by the same action speed as the toss and catch.
    inline constexpr float CarryStart=.55f,CarryEnd=1.17f,End=1.48f;
    inline float Carry(float Time){return FMath::SmoothStep(CarryStart,CarryEnd,Time);}
    inline FVector PistolOffset(float Time)
    {
        const float Lead=FMath::SmoothStep(.02f,.18f,Time);
        const float Weight=Lead*(1.f-FMath::SmoothStep(CarryEnd,End,Time));
        // Clear the axe toss even when the pistol's draw points a suppressor
        // across it. Settle this extra lift before the left-hand carry begins.
        const float TossLift=Lead*(1.f-FMath::SmoothStep(.28f,.5f,Time));
        return FVector(-6.f,12.f,10.f)*Weight+FVector(0.f,0.f,6.f)*TossLift;
    }
    inline FVector WristArc(float Weight)
    {
        return FVector(0.f,0.f,-12.f*FMath::Square(FMath::Sin(PI*Weight)));
    }
}
