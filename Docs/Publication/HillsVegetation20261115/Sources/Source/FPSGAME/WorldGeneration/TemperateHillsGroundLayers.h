#pragma once

#include "TemperateForestHabitat.h"
#include "TemperateForestWater.h"
#include "TemperateChapelSite.h"
#include "TemperateVillageSite.h"

namespace TemperateHillsGround
{
// The terrain material reads UV0 (world projection), UV1 (habitat), UV2 (upland)
// and RGBA (bank, dampness, pebbles, inverse litter) on both meshes.
struct FLayers
{
    FVector2f UV, Habitat, Upland;
    FVector4f Color;
};

inline FLayers Layers(double X, double Y, double Z, const FVector& Normal, int32 Seed,
    const TemperateRiver::FSample& Bank, double Region, const TemperateEcology::FProfile& Ecology)
{
    const double Trail = FMath::Abs(Y - TemperateHillsSurface::ValleyY(X, Seed));
    const double Forest = TemperateForestHabitat::Canopy(X, Y, Seed, Region,
        Region > 0 ? TemperateForestHabitat::RainforestOpening(X, Y, Seed, Ecology) : 0., Ecology);
    const double Litter = TemperateForestHabitat::Litter(X, Y, Seed, Normal.Z, Bank.Bank, Forest, Ecology);
    const auto Site = TemperateForestHabitat::Upland(Normal, Forest,
        TemperateForestHabitat::Moisture(X, Y, Seed, Region, Ecology), Region, Ecology);
    const double Verge = TemperateForestHabitat::UplandSurfaceWeight(Trail, Bank.Bank, Normal.Z);
    // Encode scuffed ground below the neutral UV2.x value; higher values carry meadow.
    const double Patch = .5 + .5 * FMath::PerlinNoise2D(FVector2D(X/690. + Seed%257, Y/690.));
    const double RoadWear = 1. - FMath::SmoothStep(240., 760., Trail);
    const double BankWear = FMath::SmoothStep(.02, .15, Bank.Bank) * (1. - FMath::SmoothStep(.25, .62, Bank.Bank));
    const double Wear = FMath::Max(RoadWear, BankWear*.6) * Patch * (1.-Region) * FMath::SmoothStep(.83, .96, Normal.Z);
    const double Wet = Bank.Bank > 0 ? Bank.Bank * (1 - FMath::SmoothStep(-8., 48., Z - Bank.WaterZ)) : 0.;
    return {FVector2f(X/400, Y/400), FVector2f(Region * FMath::SmoothStep(1400., 2000., Trail), 0),
        FVector2f(2. + Site.Meadow*Verge*(1.-Wear) - Wear, 2. + Site.Stony*Verge),
        FVector4f(Bank.Bank, Wet, TemperateRiver::PebbleCover(X, Y, Seed, Bank), 1-Litter*(1.-Wear))};
}

inline float SurfaceMoisture(double Mean, double Z, double Step, float Region,
    const TemperateForestWater::FPlanPtr& Water, double X, double Y)
{
    const double Concavity = FMath::SmoothStep(.08, 1.8, (Mean-Z)*FMath::Square(200./Step));
    return Region > 0 && Water ? FMath::Max(Concavity, Water->ShoreMoistureAt(X,Y)) : Concavity;
}

// Immutable input for a full-area map, including cells outside the streaming radius.
struct FMapSource
{
    int32 Seed, Version;
    FBox2D Bounds;
    TemperateRiver::FPlanPtr River;
    TemperateForestWater::FPlanPtr Water;
    FTemperateChapelSite Chapel;
    FTemperateVillageSite Village;
    TArray<TemperateHillsSurface::FTerrainEdit> Edits;

    double Height(double X, double Y) const
    {
        const double Base = River ? River->Height(X,Y,Seed) : TemperateHillsSurface::Height(X,Y,Seed,Version);
        const double Floor = Water ? Water->ShapeGround(X,Y,Base) : Base;
        return Chapel.Grade(X,Y,Village.Grade(X,Y,Floor)) + TemperateHillsSurface::TerrainEditOffset(Edits,X,Y);
    }
};
}
