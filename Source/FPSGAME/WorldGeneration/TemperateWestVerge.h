#pragma once
#include "CoreMinimal.h"
class ATemperateHillsWorld;
struct FTemperatePlacement;

namespace TemperateWestVerge
{
void Gather(const ATemperateHillsWorld& Hills,const FBox& Bounds,TArray<FTemperatePlacement>& Out,bool Woody);
}
