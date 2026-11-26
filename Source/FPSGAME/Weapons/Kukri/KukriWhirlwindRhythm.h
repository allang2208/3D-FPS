#pragma once
#include "../../Skills/WhirlwindTypes.h"

/** Kukri-only timing, shared by the local action and the server receipt window. */
namespace KukriWhirlwindRhythm
{
inline constexpr float SpinSpeedScale=1.5f;
inline constexpr float TurnDirection=1.f;
inline constexpr float ContactStopSeconds=.055f;
inline constexpr float ContactStopBudget=.13f;
inline constexpr float ContactKickScale=1.3f;

inline FWhirlwindTuning Resolve(FWhirlwindTuning T)
{
    T.SpinSeconds/=SpinSpeedScale;
    T.TurnDegrees=TurnDirection*FMath::Abs(T.TurnDegrees);
    T.HitStopSeconds=ContactStopSeconds;
    T.HitStopBudget=ContactStopBudget;
    return T;
}
}
