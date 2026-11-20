#pragma once

#include "TemperateForestWater.h"
#include "TemperateVillageSite.h"

// Immutable layout for the authored hills. The save still owns edits, repairs,
// resources and world identity. It never contains a copy of this shared data.
namespace TemperateHillsFixedLayout
{
struct FLayout
{
    TemperateRiver::FPlanPtr River;
    TemperateForestWater::FPlanPtr Water;
    FTemperateVillageSite Village;
    uint32 Checksum = 0;
};

FLayout Load(int32 Seed, int32 GeneratorVersion, double HalfSize, const FVector2D& Anchor,
    const TemperateEcology::FProfile& Ecology);
#if WITH_EDITOR
bool Write(FLayout& Layout, int32 Seed, int32 GeneratorVersion, double HalfSize, const FVector2D& Anchor);
#endif
}
