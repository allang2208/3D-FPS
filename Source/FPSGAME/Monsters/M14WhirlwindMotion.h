#pragma once
#include "CoreMinimal.h"

// The Blender author reads these constants directly. Root yaw and contact
// sweeps use the same integrated speed curve, with exactly six active turns.
namespace M14WhirlwindMotion
{
inline constexpr float ReadySeconds = 0.55f;
inline constexpr float SpinSeconds = 2.10f;
inline constexpr float RecoverSeconds = 0.65f;
inline constexpr float AccelSeconds = 0.18f;
inline constexpr float BrakeSeconds = 0.30f;
inline constexpr float TurnDegrees = 2160.0f;
inline constexpr float WindDegrees = -14.0f;
inline constexpr float OuterRadius = 162.5f;
inline constexpr float ContactRadius = 36.4f;
inline constexpr float ContactHeight = 36.0f;
inline constexpr int32 ContactHz = 120;
inline constexpr int32 ContactSamples = 252;

inline float Ease(float U) { U=FMath::Clamp(U,0.f,1.f);return U*U*(3.f-2.f*U); }
inline float Phase(float Seconds)
{
    const float T=FMath::Clamp(Seconds-ReadySeconds,0.f,SpinSeconds);
    const float Area=SpinSeconds-.5f*(AccelSeconds+BrakeSeconds);
    if(T<AccelSeconds)
    {
        const float U=T/AccelSeconds;
        return AccelSeconds*(U*U*U-.5f*U*U*U*U)/Area;
    }
    if(T<=SpinSeconds-BrakeSeconds)return (T-.5f*AccelSeconds)/Area;
    const float U=(T-(SpinSeconds-BrakeSeconds))/BrakeSeconds;
    return (SpinSeconds-BrakeSeconds-.5f*AccelSeconds+
        BrakeSeconds*(U-U*U*U+.5f*U*U*U*U))/Area;
}
inline float Yaw(float Seconds)
{
    const float Wind=Ease(Seconds/ReadySeconds)*(1.f-Ease((Seconds-ReadySeconds-SpinSeconds)/RecoverSeconds));
    return WindDegrees*Wind+TurnDegrees*Phase(Seconds);
}
}
