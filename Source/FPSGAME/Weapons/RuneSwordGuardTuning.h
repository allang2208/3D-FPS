#pragma once
#include "CoreTypes.h"

// Base gamedev shield contract adapted to the two-handed sword (seconds/cm).
namespace RuneSwordGuardTuning
{
    inline constexpr uint8 ClovenAttackMeta=0x15; // heavy counter, distinct from uppercut 0x14
    inline constexpr float RaiseSeconds=.20f,LowerSeconds=.18f;
    inline constexpr float ParrySeconds=1.f,ParryHalfAngleDegrees=120.f;
    inline constexpr float DamageTakenRatio=.50f,BlockStamina=20.f,MoveMultiplier=.50f;
    inline constexpr float ParryStunSeconds=1.f,ParryKnockbackCM=100.f;
    inline constexpr float BreakStunSeconds=1.5f;
}
