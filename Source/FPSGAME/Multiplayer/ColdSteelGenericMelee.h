#pragma once
#include "CoreMinimal.h"

// Gameplay intents, not presentation event IDs. Sword's ordinary overhead
// has a different authored clock from the stage-one horizontal slash.
namespace ColdSteelGenericMelee
{
    inline constexpr uint8 Sword=1,Tool=2,Unarmed=3,Staff=4,SwordOverhead=5,SwordDash=6;
    inline constexpr int32 MaxReceipts=64,MaxTargets=128;
    inline constexpr double ReportGrace=.9,ContactSlack=.12;
}
