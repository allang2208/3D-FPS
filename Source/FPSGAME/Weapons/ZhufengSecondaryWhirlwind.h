#pragma once

#include "../Skills/WhirlwindTypes.h"

namespace ZhufengSecondaryWhirlwind
{
inline FWhirlwindTuning Resolve(FWhirlwindTuning T)
{
    // One turn at 150% of the active whirlwind's angular speed. Halving the
    // turn count also halves the travel time; /1.5 alone would slow the sweep.
    const float SourceDegrees=FMath::Max(1.f,FMath::Abs(T.TurnDegrees));
    T.SpinSeconds*=360.f/SourceDegrees/1.5f;
    T.TurnDegrees=T.TurnDegrees<0.f?-360.f:360.f;
    T.HitStopSeconds=T.HitStopBudget=0.f;
    return T;
}
}
