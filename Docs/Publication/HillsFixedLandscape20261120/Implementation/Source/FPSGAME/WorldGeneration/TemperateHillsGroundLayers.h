#pragma once

#include "TemperateForestHabitat.h"
#include "TemperateForestWater.h"
#include "TemperateChapelSite.h"
#include "TemperateVillageSite.h"
#include "TemperateWoodlandFloor.h"
#include "TemperateShoreHabitat.h"
#include "TemperateQuarryYard.h"
#include "TemperateHillsLandform.h"

namespace TemperateHillsGround
{
// The terrain material reads UV0 (world projection), UV1 (habitat), UV2 (upland)
// and RGBA (bank, dampness, pebbles, inverse litter) on both meshes. UV3 is
// present on the quarry approach and carries its coverage and trapped moisture.
struct FLayers
{
    FVector2f UV, Habitat, Upland;
    FVector4f Color;
    FVector2f SlopeDrainage{4.f,0.f};
};

// Join the authored street ends to their own gates and the surveyed feeder.
// Work in village coordinates so the wear follows the road on rotated sites.
inline double VillageTrack(const FTemperateVillageSite& V,double X,double Y,int32 Seed)
{
    if(!V.bPlaced||!V.bHilltop||!V.Near(X,Y))return 0.;
    const FVector2D P=V.Local(X,Y);
    const double Along=FMath::Abs(P.X)-TemperateVillageLayout::HalfX;
    const double Length=V.ApproachLength(P.X);
    if(Length<=0.||Along< -240.||Along>Length)return 0.;
    const double Across=P.Y-V.GateY(P.X);
    if(FMath::Abs(Across)>630.)return 0.;
    const double Edge=TemperateHillsSurface::Noise(X*.0011,Y*.0011,Seed,4621);
    const double Bend=65.*TemperateHillsSurface::Noise(X*.00028,Y*.00028,Seed,4619);
    const double Width=230.+40.*Edge;
    return (1.-FMath::SmoothStep(Width-100.,Width+170.,FMath::Abs(Across-Bend)))*
        FMath::SmoothStep(-240.,10.,Along)*FMath::SmoothStep(0.,600.,Length-Along)*(.89+.08*Edge);
}

inline FLayers Layers(double X, double Y, double Z, const FVector& Normal, int32 Seed,
    const TemperateRiver::FSample& Bank, double Region, const TemperateEcology::FProfile& Ecology,
    bool VillageBiomes,const FTemperateVillageSite& Village,const TemperateRiver::FPlan* River)
{
    const double Trail = FMath::Abs(Y - TemperateHillsSurface::ValleyY(X, Seed));
    const double Grove=TemperateForestGroves::Sample(X,Y,Seed).Cover;
    const double Forest = TemperateForestHabitat::CanopyFromGrove(X, Y, Seed, Region,
        Region > 0 ? TemperateForestHabitat::RainforestOpening(X, Y, Seed, Ecology) : 0., Ecology,Grove);
    const double FloorPatch=TemperateWoodlandFloor::Patch(X,Y,Seed);
    const double WoodlandFinish=(1.-FMath::SmoothStep(0.,.02,Bank.Bank))*(1.-Bank.CliffWeight);
    const double Dry=VillageBiomes?(1.-Region)*WoodlandFinish:0.;
    const double Deposit=Dry>0.?TemperateWoodlandFloor::DryDeposit(X,Y,Seed,Normal,FloorPatch):1.;
    const double Litter = TemperateForestHabitat::Litter(X, Y, Seed, Normal.Z, Bank.Bank, Forest,Grove,Ecology)
        *FMath::Lerp(FMath::Lerp(1.,FMath::Lerp(.40,1.,FloorPatch),WoodlandFinish),Deposit,Dry);
    const double GroundShade=Forest*FMath::Lerp(1.,Deposit,Dry);
    const auto Site = TemperateForestHabitat::Upland(Normal, GroundShade,
        TemperateForestHabitat::Moisture(X, Y, Seed, Region, Ecology), Region, Ecology);
    const double Verge = TemperateForestHabitat::UplandSurfaceWeight(Trail, Bank.Bank, Normal.Z);
    // Encode scuffed ground below the neutral UV2.x value; higher values carry meadow.
    const double Patch = .5 + .5 * FMath::PerlinNoise2D(FVector2D(X/690. + Seed%257, Y/690.));
    const double RoadWear = 1. - FMath::SmoothStep(240., 760., Trail);
    const double BankWear = FMath::SmoothStep(.02, .15, Bank.Bank) * (1. - FMath::SmoothStep(.25, .62, Bank.Bank));
    const double NaturalWear = FMath::Max(RoadWear, BankWear*.6) * Patch * (1.-Region);
    const double Track=VillageBiomes?VillageTrack(Village,X,Y,Seed)*(1.-Bank.Bank):0.;
    const auto& Coast=Bank.LocalShore;
    // Expose the scanned soil underneath the gravel material in the wet seams.
    const double Wear = FMath::Max3(NaturalWear,Track,double(Coast.Silt)) * FMath::SmoothStep(.83, .96, Normal.Z);
    const double Above=Z-Bank.WaterZ;
    const double Wet = Bank.Bank > 0 ? Bank.Bank * (1 - FMath::SmoothStep(-8., 48., Above)) : 0.;
    const double Damp=FMath::Max3(Wet*(1.-.50*Coast.Bar),Coast.Runnel*(1.-FMath::SmoothStep(12.,55.,Above)),
        Coast.Silt*(1.-FMath::SmoothStep(45.,130.,Above)));
    // V3's shared mask already reserves the yellow approach. Do not cut a second
    // world-wide yellow valley band through the surrounding rainforest floor.
    const double Gravel=TemperateRiver::PebbleCover(X,Y,Seed,Bank);
    const auto Margin=TemperateShore::Margin(X,Y,Seed,Bank,Gravel);
    const double ShoreRock=FMath::Max(Bank.ShoreRock*Bank.Bank*(1.-FMath::SmoothStep(.82,.97,Normal.Z)),Margin.Ledge*.76);
    const double MineralCover=Bank.Bank*(1.-.88*Margin.Turf)*(1.-.30*Margin.Ledge)*(1.-.60*Coast.Silt);
    const double ForestSurface=(VillageBiomes?Region:Region*FMath::SmoothStep(1400.,2000.,Trail))*(1.-Bank.CliffWeight)*(1.-ShoreRock)*(1.-Coast.Silt);
    FLayers Result={FVector2f(X/400, Y/400), FVector2f(ForestSurface, 0),
        FVector2f(2. + Site.Meadow*Verge*(1.-Wear)*(1.-Bank.CliffWeight)*(1.-ShoreRock) - Wear,
            2. + FMath::Max(FMath::Max(Site.Stony*Verge,Bank.CliffWeight),ShoreRock)),
        FVector4f(MineralCover, Damp, Gravel, 1-Litter*(1.-Wear)*(1.-Bank.CliffWeight))};
    if(River && TemperateHillsLandform::HasSurveyedRunoff(Seed,River->GenerationVersion,River->WorldHalf))
    {
        const auto Run=TemperateHillsLandform::SurveyedRunoff(X,Y);
        const float Stones=float(FMath::Max(.44*Run.Shoulder,.66*Run.Apron)*(.62+.38*Patch));
        Result.Habitat.X*=1.f-Stones*.56f;
        Result.Upland.X=FMath::Lerp(Result.Upland.X,1.54f,float(Run.Hollow*(.43+.18*Patch)));
        Result.Upland.Y=FMath::Max(Result.Upland.Y,2.f+Stones);
        Result.Color.X=FMath::Max(Result.Color.X,Stones*.57f);
        Result.Color.Z=FMath::Max(Result.Color.Z,float(Run.Apron*(.34+.30*Patch)));
    }
    if(Seed==TemperateHillsMap::Seed && Village.bPlaced && Village.bHilltop && Village.Near(X,Y))
    {
        const auto Apron=TemperateVillageApron::Sample(Village.Local(X,Y),Village.PadHalfX,Village.PadHalfY,Village.Shoulder);
        // Retain islands of the existing turf across the wash; the foot picks
        // up mineral soil and gravel while the narrower upper cut shows earth.
        const double Cut=Apron.Wash*(.51+.31*Patch);
        Result.Upland.X=FMath::Lerp(Result.Upland.X,1.27f,float(Cut));
        Result.Color.X=FMath::Max(Result.Color.X,float(Apron.Gravel*(.37+.24*Patch)));
        Result.Color.Z=FMath::Max(Result.Color.Z,float(Apron.Gravel*(.48+.31*Patch)));
    }
    if(River && Bank.CliffWeight>0.)
    {
        const FVector2D Local=River->WhiteCliffs.Local(X,Y);
        const auto Q=TemperateQuarry::Finish(Local,Normal.Z,Patch);
        const float Blend=float(Bank.CliffWeight);
        // UV2.x below 2 exposes the excavated-soil family; above 2 is meadow.
        // UV2.y carries stony cover on both the near mesh and the map.
        const double Dust=(.29+.20*Patch)*(1.-Q.Bed)*(1.-Q.Talus)*(1.-Q.Turf);
        Result.Upland.X=FMath::Lerp(Result.Upland.X,float(2.+.72*Q.Turf-FMath::Max(Dust,Q.Wear)),Blend);
        Result.Upland.Y=FMath::Lerp(Result.Upland.Y,float(2.+FMath::Max(Q.Bed,.83*Q.Talus)*(1.-Q.Wear)),Blend);
        // Use the scanned mineral ground under loose rock and along the wheel track.
        // Dampness stays in its own channel; dry quarry gravel never implies water.
        const double Wheel=FMath::Abs(FMath::Abs(Local.X-TemperateQuarry::RoadX(Local.Y))-110.);
        const double WheelGrit=Q.Wear*(.40+.27*(1.-FMath::SmoothStep(16.,74.,Wheel)));
        const float Mineral=Blend*float(FMath::Max3(.92*Q.Talus,.78*Q.Bed,WheelGrit)*(.80+.20*Patch));
        Result.Color.X=FMath::Max(Result.Color.X,Mineral);
        Result.Color.Z=FMath::Max(Result.Color.Z,Mineral*float(.65+.29*Patch));
    }
    if(River)
    {
        const auto S=River->QuarryLakeSlope.Sample(X,Y);
        if(S.Coverage>0.f)
        {
            // Meadow islands on stable soil, exposed rock on the spurs, coarse
            // mineral at each foot, dark excavated earth along the wet thalwegs.
            const float Stone=FMath::Max(S.Ledge,.66f*S.Gravel);
            Result.SlopeDrainage=FVector2f(4.f+S.Coverage,S.Damp);
            Result.Habitat.X*=1.f-FMath::Max3(.93f*S.Gully,.86f*Stone,.49f*S.Turf);
            Result.Upland.X=FMath::Lerp(Result.Upland.X,2.f,S.Coverage)+.92f*S.Turf-.89f*S.Gully-.34f*S.Gravel;
            Result.Upland.Y=FMath::Lerp(Result.Upland.Y,2.f,S.Coverage)+.98f*Stone;
            Result.Color.X=FMath::Max(Result.Color.X,.75f*S.Gravel);
            Result.Color.Y=FMath::Max(Result.Color.Y,.51f*S.Damp);
            Result.Color.Z=FMath::Max(Result.Color.Z,.83f*S.Gravel);
            Result.Color.W=FMath::Lerp(Result.Color.W,1.f,FMath::Max(Stone,S.Gully));
        }
    }
    return Result;
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
        return Chapel.Grade(X,Y,Village.Grade(X,Y,Floor,Seed)) + TemperateHillsSurface::TerrainEditOffset(Edits,X,Y);
    }
};
}
