#pragma once
#include "CoreMinimal.h"

// Presentation follows the same deadline as the authored quick-melee clip.
// Settle the assembly during recovery, then hand the final pose to live idle.
namespace QuickCombatRecovery
{
    constexpr float FramingReturnStart = 0.60f;
    constexpr float IdleHandoffStart = 0.78f;

    inline float RemainingWeight(float Elapsed, float Duration, float StartFraction)
    {
        const float T = FMath::Clamp((Elapsed / Duration - StartFraction) / (1.f - StartFraction), 0.f, 1.f);
        // Zero velocity and acceleration at both ends of the handoff.
        return 1.f - T*T*T*(10.f + T*(-15.f + 6.f*T));
    }
}
