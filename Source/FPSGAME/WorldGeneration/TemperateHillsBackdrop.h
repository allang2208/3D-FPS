#pragma once

#include "CoreMinimal.h"
#include "TemperateHillsRiver.h"

namespace TemperateBackdrop
{
// Fixed topology: 64 x 64 playable-world proxy and two stitched outer rings.
constexpr int32 Grid = 64;
constexpr double OuterHalf = 512000.0;
double Height(double X, double Y, double PlayableHalf, int32 Seed, const TemperateRiver::FPlanPtr& River);
double CoreTriangleHeight(double X, double Y, double PlayableHalf, int32 Seed, const TemperateRiver::FPlanPtr& River);
}
