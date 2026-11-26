#pragma once

#include "TemperateHillsSurface.h"
#include "TemperateHillsMap.h"

namespace TemperateHillsLandform
{
struct FRunoff
{
    double HeightCm = 0.;
    double Hollow = 0., Shoulder = 0., Apron = 0.;
    FVector2D Downstream = FVector2D::ZeroVector;
};

inline bool HasSurveyedRunoff(int32 Seed, int32 Version, double WorldHalf)
{
    return Seed==TemperateHillsMap::Seed && Version==TemperateHillsMap::GeneratorVersion && WorldHalf==51200.;
}
FRunoff SurveyedRunoff(double X, double Y);

inline double PoolClearance(double X,double Y)
{
    double Freedom=1.;
    for(const auto& Site:TemperateHillsMap::WoodlandPools)
    {
        const double DX=X-Site.X*100., DY=Y-Site.Y*100.;
        if(FMath::Abs(DX)<2800. && FMath::Abs(DY)<2800.)
            Freedom=FMath::Min(Freedom,FMath::SmoothStep(1200.*1200.,2800.*2800.,DX*DX+DY*DY));
    }
    return Freedom;
}

struct FSlopeSite
{
    double Shoulder,Swale;
};

inline FSlopeSite SlopeSite(double HeightOffsetCm)
{
    return {FMath::SmoothStep(25.,185.,HeightOffsetCm),FMath::SmoothStep(12.,98.,-HeightOffsetCm)};
}

// A finishing layer, applied only after the unchanged settlement and river
// survey. Broad hills remain readable; selected patches gain low shoulders and
// shallow drainage folds at scales the streamed terrain can actually represent.
inline double Relief(double X,double Y,int32 Seed,bool FixedCatchments)
{
    using namespace TemperateHillsSurface;
    const double Patch=FMath::SmoothStep(.22,.78,Noise5(X/15000.,Y/15000.,Seed,4401)*.5+.5);
    if(Patch<=0.)return 0.;
    const double WX=X+Noise5(X/6200.,Y/6200.,Seed,4409)*850.;
    const double WY=Y+Noise5(X/6200.,Y/6200.,Seed,4421)*850.;
    const double Shoulder=Noise5(WX/5600.,WY/5600.,Seed,4423)*230.;
    const double Fold=Noise5(WX/2600.,WY/3900.,Seed,4441);
    double Hollow=1.-FMath::SmoothStep(.06,.33,FMath::Abs(Fold));
    const double Detail=Noise5(WX/1150.,WY/1150.,Seed,4447)*24.;
    if(FixedCatchments && FMath::Abs(Fold+.09)<.56)
    {
        // Cutting the full zero contour of each noise lobe engraved closed
        // rings even across convex crests. Keep broad hollows in low ground
        // and let their shallow heads disappear as they reach the shoulders.
        const double Catchment=FMath::SmoothStep(-.08,.67,-Shoulder/230.+.16*Detail/24.);
        const double Valley=1.-FMath::SmoothStep(0.,.56,FMath::Abs(Fold+.09));
        const double Cut=(.13*Hollow+.87*Valley)*(.16+.84*Catchment);
        Hollow=FMath::Lerp(Hollow,Cut,PoolClearance(X,Y));
    }
    return Patch*(Shoulder-Hollow*105.+Detail);
}
}
