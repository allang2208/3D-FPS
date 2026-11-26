#pragma once
#include "CoreMinimal.h"

/** Passive HUD snapshots; no resource, focus or cooldown state is mutated. */
struct FColdSteelStaffManaReadout
{
    float Current=0.f,Maximum=0.f,RecoveryPerSecond=0.f,FullRecoverySeconds=0.f;
    float CooldownReductionPercent=0.f;
    bool bInfinite=false,bRecoveryPaused=false,bRecoveryDisabled=false;
};

enum class EColdSteelFocusReadout : uint8 { Ready,Opening,Empowered,Closing,Interrupted };

struct FColdSteelSpellbookReadout
{
    EColdSteelFocusReadout State=EColdSteelFocusReadout::Ready;
    float CastSpeedMultiplier=1.f,ManaCostMultiplier=1.f,MovementMultiplier=.67f,InterruptMaxManaFraction=.25f;
};
