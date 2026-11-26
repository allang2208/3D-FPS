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

// Dry grass survives between crowns. Shallow runnels collect more leaves than
// exposed faces; let grass and litter interleave across the whole stand edge.
inline double DryDeposit(double X,double Y,int32 Seed,const FVector& Normal,double FloorPatch)
{
    const double Along=(.82*X+.57*Y)/2400.,Across=(-.57*X+.82*Y)/660.;
    const double Drift=.5+.5*TemperateHillsSurface::Noise5(Along,Across,Seed,4663);
    const double Shelter=FMath::Clamp(.5-1.6*(Normal.X*.82+Normal.Y*.57),0.,1.);
    return FMath::Clamp(.12+.36*FloorPatch+.26*Drift+.13*Shelter,0.,1.);
}
}
