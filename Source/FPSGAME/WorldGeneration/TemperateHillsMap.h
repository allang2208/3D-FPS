#pragma once

#include "CoreTypes.h"

// The authored hills geography is shared by new playthroughs. WorldId still
// identifies the individual save, its settlements, harvests and encounters.
namespace TemperateHillsMap
{
inline constexpr int32 Seed = 1518277816;
inline constexpr int32 GeneratorVersion = 3;

// Centres recorded from the six woodland pools on the original fixed map,
// in metres and in their existing allocation order.
struct FPoolSite { int32 X, Y; };
inline constexpr FPoolSite WoodlandPools[] = {
    {-272,24}, {80,-480}, {-336,464}, {360,-120}, {104,400}, {456,504}
};
}
