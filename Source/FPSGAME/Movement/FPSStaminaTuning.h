#pragma once
#include "CoreMinimal.h"

struct FColdSteelStaminaTuning
{
    float BaseMaximum=100.f, PerConstitution=0.f;
    float SprintPerSecond=12.f, MeleeCost=15.f, HarvestCost=10.f, DodgeCost=25.f;
    float RecoveryPerSecond=20.f, RecoveryDelay=1.f, SprintRestartRatio=.2f;
};

struct FColdSteelMeleeStaminaReadout
{
    int32 AvailableAttacks=0;
    bool bUnlimitedAttacks=false;
    float FullRecoverySeconds=0.f;
    bool bRecoveryPaused=false;
    bool bRecoveryDisabled=false;
};
