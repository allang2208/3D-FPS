#pragma once

namespace MonsterCombatTuning
{
    // Apply once to the existing per-monster/instance distance bases, including
    // saved Blueprint values. HandBrain keeps its original unscaled ranges.
    inline constexpr float AttackDistanceScale = 1.5f;
    inline constexpr float DeathAnimationFraction = .6f;

    inline constexpr float AttackDistance(float BaseDistanceCM)
    {
        return BaseDistanceCM * AttackDistanceScale;
    }
}
