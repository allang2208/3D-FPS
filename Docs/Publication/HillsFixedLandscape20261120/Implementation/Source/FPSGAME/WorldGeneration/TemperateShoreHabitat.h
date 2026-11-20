#pragma once

#include "TemperateHillsRiver.h"
#include "TemperateHillsSurface.h"

namespace TemperateShore
{
// Fitted river rocks use the signed grid pair XOR the river bit. Their
// decorative children pack the same coordinates into two 24-bit fields.
inline uint64 CompanionId(uint64 Parent,int32 Piece)
{
    return 0x7400000000000000ULL|((Parent>>32)&0xffffffULL)<<32|(Parent&0xffffffULL)<<8|uint64(Piece);
}
inline bool TouchesSupport(uint64 Id)
{
    const uint64 Piece=Id&0xff;
    return (Id>>56)==0x74 && (Piece<8 || (Piece>=9 && Piece<=11) || (Piece>=16 && Piece<23));
}
inline uint64 RiverParent(uint64 Child)
{
    const auto SignedCell=[](uint64 Bits)->uint32
    {
        const uint32 Low=uint32(Bits&0xffffff);
        return (Low&0x800000)?(Low|0xff000000):Low;
    };
    return ((uint64(SignedCell(Child>>32))<<32)|SignedCell(Child>>8))^0x4000000000000000ULL;
}
// The channel survey measures bend toward its left normal. Positive inside
// bend shelters a gravel bar; headlands use the lake landform's rock exposure.
inline double Exposure(const TemperateRiver::FSample& Water)
{
    if (Water.bLake) return Water.ShoreRock;
    const double InsideBend = Water.Bend * (Water.SignedDistance >= 0. ? 1. : -1.);
    const double Current = FMath::Clamp((Water.Speed - 60.) / 65., -1., 1.);
    return FMath::Clamp(.48 - .58 * InsideBend + .18 * Current, 0., 1.);
}

struct FMargin
{
    double Turf=0.;
    double Ledge=0.;
};

// Two overlapping margins: turf extends downslope in tongues and exposed
// shelves break the waterline only along selected stretches.
inline FMargin Margin(double X,double Y,int32 Seed,const TemperateRiver::FSample& Water,double Gravel)
{
    FMargin Result;
    if(Water.Bank<=0.)return Result;
    const double Edge=Water.Distance-Water.HalfWidth;
    if(Edge< -155.)return Result;
    const double ExposureWeight=Exposure(Water);
    const double Shape=TemperateHillsSurface::Noise5(X/800.,Y/800.,Seed,4823);
    const double Foot=130.+Shape*250.+Gravel*210.;
    Result.Turf=FMath::SmoothStep(Foot,Foot+240.,Edge)*(1.-.65*Gravel);
    const double Fractions=TemperateHillsSurface::Noise5(X/330.,Y/330.,Seed,4829);
    const double Crest=65.+Shape*100.+Fractions*65.;
    const double Width=FMath::Lerp(120.,270.,ExposureWeight);
    Result.Ledge=(1.-FMath::SmoothStep(Width*.25,Width,FMath::Abs(Edge-Crest)))*
        FMath::SmoothStep(-.48,.29,Shape+.45*Fractions)*(.28+.72*ExposureWeight);
    const auto& Local=Water.LocalShore;
    Result.Turf=FMath::Max(Result.Turf*(1.-Local.Runnel),double(Local.Roots)*.89);
    Result.Ledge=FMath::Max(Result.Ledge*(1.-Local.Runnel),double(Local.Spine));
    return Result;
}
}
