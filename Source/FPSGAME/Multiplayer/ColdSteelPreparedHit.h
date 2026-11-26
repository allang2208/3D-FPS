#pragma once
#include "ColdSteelPlayerState.h"
#include "../Weapons/Kukri/KukriPairedHeavyHit.h"

// Synchronous server-only result of the existing equipment/action/geometry checks.
// Item copies survive inventory publication by damage and training callbacks.
struct FColdSteelPreparedHit
{
    FColdSteelNetHitReport Report;
    AFPSGAMECharacter* Shooter=nullptr;
    UColdSteelStatusModel* Model=nullptr;
    FHitResult Hit;
    float Damage=0.f;
    FColdSteelSkillShot Shot;
    FColdSteelItem Item;
    bool bHasItem=false,bFiredRound=false,NewMasteryTarget=false,MasteryEligible=false;
};
