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
    // First-person guard V24 clip (2026-11-22, Kubold FPP two-handed sword 1:49-1:52): a 0.46 s raise, then one
    // 2.05 s breath of the hold that loops. Presentation only: RaiseSeconds/LowerSeconds keep the gameplay,
    // network and third-person timing (lowering still takes LowerSeconds, attacks wait for it). A clip shorter
    // than raise + breath is an older raise-and-hold clip.
    inline constexpr float ViewHoldStartSeconds=.46f,ViewBreathSeconds=2.05f;
}
