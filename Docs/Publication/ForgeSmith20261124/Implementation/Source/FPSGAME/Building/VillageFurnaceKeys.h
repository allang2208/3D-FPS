#pragma once
#include "CoreMinimal.h"

namespace VillageFurnaceKeys
{
    // These two level-owned stations can stream in after voxel save loading. Each world
    // keeps their jobs in two permanent keys outside the playable construction lattice.
    inline FIntVector ForBay(int32 Bay) { return FIntVector(0, Bay, -1000000); }
    inline bool Contains(FIntVector Cell) { return Cell == ForBay(0) || Cell == ForBay(1); }
}
