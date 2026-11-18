#pragma once

#include "TemperateHillsSurface.h"

// Shared, world-space composition field. The 12 m harvest candidate lattice is
// unchanged; this field groups its survivors and their ground-cover communities.
namespace TemperateForestGroves
{
// Authoring dimensions are centimetres. Keep maximum reach below one sector so
// the fixed 3 x 3 neighbourhood covers every overlapping grove at cell borders.
constexpr double SectorCm=6400.;
constexpr double MinRadiusCm=2300.;
constexpr double RadiusVariationCm=1800.;

struct FSample
{
    double Cover=0.;
    uint32 Key=0;
};

inline FSample Sample(double X,double Y,int32 Seed)
{
    using namespace TemperateHillsSurface;
    // Warp both axes once, rather than drawing circular or rectangular borders.
    const double WX=X+Noise(X/4100.,Y/4100.,Seed,4301)*310.;
    const double WY=Y+Noise(X/4100.,Y/4100.,Seed,4309)*310.;
    const int32 GX=FMath::FloorToInt(WX/SectorCm),GY=FMath::FloorToInt(WY/SectorCm);
    FSample Result;
    for(int32 DY=-1;DY<=1;++DY)for(int32 DX=-1;DX<=1;++DX)
    {
        const uint32 K=Key(GX+DX,GY+DY,uint32(Seed),4327);
        const double CX=(GX+DX+.14+.72*Unit(K+1))*SectorCm;
        const double CY=(GY+DY+.14+.72*Unit(K+2))*SectorCm;
        const FVector2D Axis=FVector2D(Unit(K+3)-.5,Unit(K+4)-.5).GetSafeNormal();
        const FVector2D Delta(WX-CX,WY-CY);
        const double Along=FVector2D::DotProduct(Delta,Axis);
        const double Across=Delta.X*-Axis.Y+Delta.Y*Axis.X;
        const double Radius=MinRadiusCm+RadiusVariationCm*Unit(K+5);
        const double Aspect=.58+.38*Unit(K+6);
        const double D2=FMath::Square(Along/Radius)+FMath::Square(Across/(Radius*Aspect));
        const double Cover=1.-FMath::SmoothStep(.12,1.,D2);
        if(Cover>Result.Cover){Result.Cover=Cover;Result.Key=K;}
    }
    return Result;
}
}
