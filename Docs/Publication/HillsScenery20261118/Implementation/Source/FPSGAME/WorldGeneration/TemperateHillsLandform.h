#pragma once

#include "TemperateHillsSurface.h"

namespace TemperateHillsLandform
{
// A finishing layer, applied only after the unchanged settlement and river
// survey. Broad hills remain readable; selected patches gain low shoulders and
// shallow drainage folds at scales the streamed terrain can actually represent.
inline double Relief(double X,double Y,int32 Seed)
{
    using namespace TemperateHillsSurface;
    const double Patch=FMath::SmoothStep(.22,.78,Noise5(X/15000.,Y/15000.,Seed,4401)*.5+.5);
    if(Patch<=0.)return 0.;
    const double WX=X+Noise5(X/6200.,Y/6200.,Seed,4409)*850.;
    const double WY=Y+Noise5(X/6200.,Y/6200.,Seed,4421)*850.;
    const double Shoulder=Noise5(WX/5600.,WY/5600.,Seed,4423)*230.;
    const double Fold=Noise5(WX/2600.,WY/3900.,Seed,4441);
    const double Hollow=1.-FMath::SmoothStep(.06,.33,FMath::Abs(Fold));
    const double Detail=Noise5(WX/1150.,WY/1150.,Seed,4447)*24.;
    return Patch*(Shoulder-Hollow*105.+Detail);
}
}
