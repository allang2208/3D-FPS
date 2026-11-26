#pragma once
#include "CoreMinimal.h"

class ATemperateHillsWorld;
struct FTemperatePlacement;

namespace TemperateVillagePlanting
{
inline constexpr double MaxSaplingHeight=500.;
bool Near(const ATemperateHillsWorld& Hills,const FBox& Bounds);
// Authored village-local clumps, emitted through the existing streamed plant layers.
void Gather(const ATemperateHillsWorld& Hills,int32 Layer,const FBox& Bounds,TArray<FTemperatePlacement>& Out);
}
