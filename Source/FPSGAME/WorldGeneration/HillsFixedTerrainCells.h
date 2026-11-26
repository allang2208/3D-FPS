#pragma once

#include "TemperateForestWater.h"
#include "TemperateVillageSite.h"

namespace HillsStreaming { struct FMeshResult; }

namespace HillsFixedTerrainCells
{
using FCellPtr = TSharedPtr<HillsStreaming::FMeshResult, ESPMode::ThreadSafe>;
// Zero means this world did not load the authored layout. A positive match
// identifies the actual layout file, independently of the player's save ID.
FCellPtr LoadOrGenerate(
    FIntPoint Key, bool Detailed, double Half, int32 Seed, TemperateRiver::FPlanPtr River,
    const TArray<TemperateHillsSurface::FTerrainEdit>& Edits, int32 Version,
    TemperateForestWater::FPlanPtr Water, FTemperateChapelSite Chapel, FTemperateVillageSite Village,
    uint32 LayoutChecksum);

#if WITH_EDITOR
void BuildBakeCell(FIntPoint Key, double Half, int32 Seed, int32 Version, TemperateRiver::FPlanPtr River,
    TemperateForestWater::FPlanPtr Water, FTemperateChapelSite Chapel, FTemperateVillageSite Village,
    FCellPtr& Near, FCellPtr& Far);
bool Bake(double Half, int32 Seed, int32 Version, TemperateRiver::FPlanPtr River,
    TemperateForestWater::FPlanPtr Water, FTemperateChapelSite Chapel,
    FTemperateVillageSite Village, uint32 LayoutChecksum);
#endif
}
