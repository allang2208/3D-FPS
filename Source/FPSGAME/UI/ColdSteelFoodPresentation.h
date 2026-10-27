#pragma once
#include "CoreMinimal.h"
#include "ColdSteelUIStyle.h"

/** Display only: durations are game days supplied by the authoritative food model. */
namespace ColdSteelFoodUI
{
/** Consumed lifetime: 0 fresh, 1 expired. Data and audits keep this direction. */
inline float Progress(double RemainingDays,double LifetimeDays)
{
    return LifetimeDays>0?float(FMath::Clamp(1.-RemainingDays/LifetimeDays,0.,1.)):0.f;
}
/** Bar fill direction: 1 full/fresh, 0 empty/expired. */
inline float Remaining(float SpoilProgress)
{
    return 1.f-FMath::Clamp(SpoilProgress,0.f,1.f);
}
inline FLinearColor Color(float SpoilProgress)
{
    // Inventory and both tooltip modes share explicit, recognizable stages.
    // The bar shrinks by Remaining(); these colors still key off consumed lifetime.
    return SpoilProgress<.5f?ColdSteelUI::Success:
        SpoilProgress<.8f?ColdSteelUI::Warning:ColdSteelUI::Danger;
}
}
