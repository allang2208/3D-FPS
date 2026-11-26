#pragma once

#include "TemperateLakeShoreDetail.h"

namespace TemperateRiver::LakeShoreDetail::CoveOutlet
{
// A shallow diagonal drainage from the grass foot to the back of the surveyed
// cove. S follows the bank, Edge follows the actual (curved) waterline, in cm.
inline bool Near(double X,double Y,int32 Seed)
{
    return Seed==SurveySeed && X>-25150. && X<-20900. && Y>-29450. && Y<-24900.;
}

struct FDeposit
{
    double Silt=0.,Gravel=0.,Stones=0.,Grass=0.;
};

inline FDeposit Section(double S,double Edge)
{
    if(S<=95. || S>=2680. || Edge<=-980. || Edge>=1290.)return {};
    const double Ends=FMath::SmoothStep(95.,330.,S)*(1.-FMath::SmoothStep(2240.,2680.,S))
        *FMath::SmoothStep(-195.,-55.,Edge)*(1.-FMath::SmoothStep(960.,1290.,Edge));
    const auto Band=[](double D,double Core,double Radius){return 1.-FMath::SmoothStep(Core,Radius,FMath::Abs(D));};
    const double Fan=1.-FMath::SmoothStep(5.,630.,Edge);
    const double Axis=480.+1.25*Edge+105.*FMath::Sin((Edge-60.)/215.);
    const double Across=S-Axis;
    const double Rill=Band(Across,72.+32.*Fan,220.+85.*Fan);
    // The two gravel lobes split around a low silt pocket. One dies out
    // short of the grass; the other carries coarse lag up the drainage.
    const double Ridge=200.+210.*Fan+38.*FMath::Sin(Edge/147.);
    const double Bar=Band(Across-Ridge,58.+40.*Fan,215.+70.*Fan);
    const double Spur=Band(Across+250.+125.*Fan,36.,163.)*(1.-FMath::SmoothStep(180.,650.,Edge));
    const double Toe=FMath::SmoothStep(105.,455.,Edge);
    const double Pocket=.32+.68*Band(Edge-620.,75.,300.);
    FDeposit P;
    P.Silt=Ends*FMath::Max(Rill,.55*Fan*Band(Across-Ridge-370.,130.,440.));
    P.Gravel=Ends*FMath::Max(Bar,.82*Spur);
    P.Stones=Ends*Band(Across-Ridge-80.,40.,175.)*FMath::SmoothStep(-55.,100.,Edge)
        *(.30+.70*Band(Edge-380.,85.,320.));
    P.Grass=Ends*Toe*FMath::Max(Band(Across-Ridge-208.,40.,190.)*Pocket,
        .76*Band(Across+267.,38.,178.)*Band(Edge-827.,95.,350.));
    if(Edge<65.)
    {
        // The broad pink shelf visible from the bank is already under water.
        // A shallow thalweg turns alongshore, leaving unequal gravel tails on
        // its rims. Only the higher, proximal parts carry emergent stones.
        const double Inward=FMath::Max(0.,-Edge);
        const double Mouth=FMath::SmoothStep(-980.,-635.,Edge)*(1.-FMath::SmoothStep(-58.,65.,Edge))
            *FMath::SmoothStep(95.,245.,S)*(1.-FMath::SmoothStep(1810.,2200.,S));
        const double Center=473.+.41*Inward+89.*FMath::Sin(Inward/196.);
        const double Current=S-Center;
        const double LongRim=Current-(344.+.27*Inward);
        const double ShortRim=Current+258.+.13*Inward;
        const double Short=1.-FMath::SmoothStep(288.,617.,Inward);
        const double LongBed=Band(LongRim,78.,239.);
        P.Silt=FMath::Max(P.Silt,Mouth*Band(Current,85.,270.));
        P.Gravel=FMath::Max(P.Gravel,Mouth*FMath::Max(LongBed,Short*Band(ShortRim,58.,164.)));
        const double Pockets=FMath::Max(.93*Band(Inward-255.,75.,217.),.61*Band(Inward-596.,43.,146.));
        P.Stones=FMath::Max(P.Stones,Mouth*FMath::Max(Pockets*Band(LongRim-76.,46.,162.),
            Short*.63*Band(ShortRim+38.,35.,129.)));
    }
    return P;
}

inline FDeposit Sample(double X,double Y,int32 Seed,double Edge)
{
    if(!Near(X,Y,Seed))return {};
    return Section(FVector2D::DotProduct(FVector2D(X,Y)-Cove.Anchor,Cove.Along()),Edge);
}
}
