#pragma once

#include "CoreMinimal.h"
#include "TemperateHillsMap.h"

// Earthworks outside the fixed hilltop settlement. Stations follow the wall in
// village coordinates; depth runs from its reserved pad to the natural hill.
namespace TemperateVillageApron
{
enum class EFace : uint8 { West, East, North, South };

struct FFold
{
    EFace Face;
    double Head, Toe, Bend, Width, DepthCm;

    double Station(double T) const { return FMath::Lerp(Head, Toe, T) + Bend * (4. * T * (1. - T)); }
};

inline constexpr FFold Folds[] = {
    {EFace::West,  -3100., -4160.,  390.,  820., 105.},
    {EFace::West,   2450.,  3340., -340., 1180.,  72.},
    {EFace::North, -3220., -1600.,  250., 1450.,  96.},
    {EFace::North,  2080.,  2990., -610.,  910.,  67.},
    {EFace::East,  -1900., -3370.,  130., 1000.,  49.},
    {EFace::South, -2780., -4090., -290.,  780.,  56.}
};

inline FVector2D LocalPoint(const FFold& Fold, double Depth, double Along, double HalfX, double HalfY)
{
    switch (Fold.Face)
    {
    case EFace::West:  return {-HalfX - Depth, Along};
    case EFace::East:  return {HalfX + Depth, Along};
    case EFace::North: return {Along, HalfY + Depth};
    default:           return {Along, -HalfY - Depth};
    }
}

struct FSample { double Height = 0., Wash = 0., Gravel = 0.; };

inline FSample Sample(const FVector2D& P, double HalfX, double HalfY, double Shoulder)
{
    const double DX = FMath::Abs(P.X) - HalfX, DY = FMath::Abs(P.Y) - HalfY;
    const bool End = DX > DY;
    const double Depth = End ? DX : DY;
    if (Depth <= 0. || Depth >= Shoulder) return {};
    const EFace Face = End ? (P.X < 0. ? EFace::West : EFace::East)
                           : (P.Y > 0. ? EFace::North : EFace::South);
    const double T = Depth / Shoulder, Along = End ? P.Y : P.X;
    // Leave the gate approaches and the entire rectangular village datum intact.
    const double GateClear = End ? FMath::SmoothStep(850., 1500., FMath::Abs(Along - (Face == EFace::West ? 0. : 500.))) : 1.;
    const double HalfRun = End ? HalfY : HalfX;
    const double EndClear = 1. - FMath::SmoothStep(HalfRun - 390., HalfRun, FMath::Abs(Along));
    const double Envelope = GateClear * EndClear * FMath::SmoothStep(.04, .29, T) * (1. - FMath::SmoothStep(.80, .99, T));
    if (Envelope <= 0.) return {};
    FSample Out;
    for (const FFold& Fold : Folds)
    {
        if (Fold.Face != Face) continue;
        const double Width = Fold.Width * (.45 + .70 * T);
        const double Cross = (Along - Fold.Station(T)) / Width;
        if (FMath::Abs(Cross) >= 2.8) continue;
        const double Channel = 1. - FMath::SmoothStep(0., 1., FMath::Abs(Cross));
        const double Outer = Cross * (Fold.Toe > Fold.Head ? -1. : 1.);
        const double Spur = 1. - FMath::SmoothStep(0., 1.36, FMath::Abs(Outer - 1.38));
        const double Fan = FMath::SmoothStep(.52, .75, T) *
            (1. - FMath::SmoothStep(.06, 1.75, FMath::Abs(Cross + .16)));
        Out.Height += Envelope * Fold.DepthCm * (.66 * Spur - Channel + .64 * Fan);
        Out.Wash = FMath::Max(Out.Wash, Envelope * Channel * (1. - Fan * .65));
        Out.Gravel = FMath::Max(Out.Gravel, Envelope * Fan);
    }
    return Out;
}
}
