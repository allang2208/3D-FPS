#pragma once
#include "CoreMinimal.h"

// VideoRefV3 authoring contract: SourceAssets/DualPistolQuickCombat20260920/
// VideoRefV3/motion.json. Both anatomical hands share this single-hit clock.
namespace DualPistolQuickCombatMotion
{
    constexpr float Duration = .80f;
    constexpr float ReleaseFraction = .04f / Duration;
    constexpr float CockFraction = .10f / Duration;
    constexpr float ContactFraction = .18f / Duration;
    constexpr float FollowFraction = .32f / Duration;
    constexpr float IdleHandoffStart = .70f / Duration;

    // BeginAction increments the existing serial only for an accepted action.
    // No additional state is needed and rejected inputs cannot switch hands.
    inline int32 StrikingHand(uint32 Serial) { return (Serial & 1u) ? 0 : 1; }
}
