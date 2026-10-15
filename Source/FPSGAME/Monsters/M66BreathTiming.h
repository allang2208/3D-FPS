#pragma once
#include "CoreMinimal.h"
namespace M66BreathTiming
{
    inline constexpr float AimLock=.95f,Release=1.2f,FireEnd=2.4f,HoldEnd=2.8f,End=3.4f;
    inline constexpr float Interval=.2f,Tail=.65f,MouthSampleRate=60.f;
    inline constexpr int32 HitCount=6;
    inline constexpr float ReleaseSoundPitch=.78f;
    inline float ReleaseSoundOffset(float Age)
    {return FMath::Max(0.f,Age-Release)*ReleaseSoundPitch;}
    inline float Mouth(float Age)
    {return FMath::SmoothStep(0.f,AimLock,Age)*(1.f-FMath::SmoothStep(HoldEnd,End,Age));}
}
