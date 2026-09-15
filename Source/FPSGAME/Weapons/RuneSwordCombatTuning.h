#pragma once

// Gameplay reach follows an extended blade sweep; the accepted viewmodel and
// one-metre player stride retain their own sizes. Saved item values remain base values.
namespace RuneSwordCombatTuning
{
    inline constexpr float RangeMultiplier=2.f;
    inline float ScaledReach(float ItemBaseReach,float AttackBonus=0.f)
    {
        return (ItemBaseReach+AttackBonus)*RangeMultiplier;
    }
}
