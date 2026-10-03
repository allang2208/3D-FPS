#pragma once
#include "CoreMinimal.h"

// Historical V3 timing, retained with its author source. V4 no longer uses it.
// Author seconds: SwordUppercut20261003/ArrowStepV3/author_uppercut_v3.py.
// Motion-only prototype. These describe the step/pose, not skill stat scaling.
namespace RuneSwordUppercutRhythm
{
    inline constexpr float StepStart=.10f, StepEnd=.36f;
    inline constexpr float ReleaseStart=.70f, RiseEnd=1.05f;
    inline constexpr float CarryEnd=1.20f, End=2.10f;
    inline constexpr float StepDistanceCM=85.f;

    inline float StepAlpha(float Time)
    {
        return FMath::SmoothStep(StepStart,StepEnd,Time);
    }

    inline void Camera(float Time,FVector& Location,FRotator& Rotation)
    {
        const float Gather=FMath::SmoothStep(0.f,StepEnd,Time);
        const float Rise=FMath::SmoothStep(ReleaseStart,RiseEnd,Time);
        const float Recover=FMath::SmoothStep(CarryEnd,End,Time);
        const float Low=Gather*(1.f-Rise),High=Rise*(1.f-Recover);
        // The swept capsule owns forward travel; the eye adds only weight shift.
        Location=FVector(2.f*Low+4.f*High,2.f*Low-3.f*High,-9.f*Low+3.f*High);
        Rotation=FRotator(-3.f*Low+4.f*High,-Low-3.f*High,-2.f*Low+2.f*High);
    }
}
