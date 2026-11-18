#pragma once
#include "TemperateHillsSurface.h"

// Shared metre-scale floor communities, independent of PCG cells and load order.
// Mature tree candidates, the road and the landform are not changed by this field.
namespace TemperateWoodlandFloor
{
inline double Patch(double X,double Y,int32 Seed)
{
    using namespace TemperateHillsSurface;
    const double WX=X+Noise5(X/2200.,Y/2200.,Seed,4811)*260.;
    const double WY=Y+Noise5(X/2200.,Y/2200.,Seed,4817)*260.;
    const double Broad=.5+.5*Noise5(WX/1350.,WY/1350.,Seed,4823);
    const double Fine=.5+.5*Noise5(WX/310.,WY/310.,Seed,4831);
    return FMath::SmoothStep(.28,.70,.65*Broad+.35*Fine);
}
}
