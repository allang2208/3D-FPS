#pragma once
#include "CoreMinimal.h"

// Source seconds match StrideThrustV16/thrust_motion.py. Attack speed scales
// animation, contact, forward step and camera together.
namespace RuneSwordThrustRhythm
{
    inline constexpr float AlignEnd=.24f, LoadEnd=.40f;
    inline constexpr float ContactStart=.48f, ExtensionEnd=.58f, ContactEnd=.64f;
    inline constexpr float ArrestEnd=.64f, ReturnCorner=.94f, AttackEnd=1.25f;
    inline constexpr float LungeStart=.40f, LungeEnd=.64f, LungeDistance=100.f;
    inline constexpr float BladeRadius=3.f, CorridorRadius=18.f, ReachBonus=32.f;
    inline constexpr float SampleRate=480.f;
    inline float LungeAlpha(float Time) { return FMath::SmoothStep(LungeStart,LungeEnd,Time); }
}
