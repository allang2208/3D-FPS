#pragma once

#include "TemperateHillsSurface.h"
#include "TemperateEcologyConfig.h"
#include "TemperateForestGroves.h"

// Visual habitat only. HeightV1/V2, river carving and harvest candidate coordinates
// stay frozen. Both worker-built terrain colours and PCG sample this same field.
namespace TemperateForestHabitat
{
inline double RainforestOpening(double X,double Y,int32 Seed, const TemperateEcology::FProfile& E)
{
    const double Scale=E.Rainforest.ClearingScaleCm;
    return FMath::SmoothStep(.56,.82,
        TemperateHillsSurface::Noise5(X/Scale,Y/Scale,Seed,3527)*.5+.5);
}

inline double LegacyCanopy(double X,double Y,int32 Seed,double GroveCover)
{
    const double Broad=FMath::SmoothStep(0.0,1.0,
        (TemperateHillsSurface::Noise(X*.00014,Y*.00014,Seed,173)+.45)/1.05);
    // This compatibility entry also feeds TreeCandidate's historical floor.
    // Group that floor as well, or it keeps planting trees between every grove.
    return GroveCover*(.74+.26*Broad);
}

inline double LegacyCanopy(double X,double Y,int32 Seed)
{
    return LegacyCanopy(X,Y,Seed,TemperateForestGroves::Sample(X,Y,Seed).Cover);
}

inline double CanopyFromGrove(double X,double Y,int32 Seed,double Region,double Opening,
    const TemperateEcology::FProfile& E,double Grove)
{
    const double Local=E.Rainforest.Canopy*(.025+.975*Grove)*(1.-.46*Opening);
    if(Region==1.)return Local;
    const double Woodland=E.Woodland.Weight(LegacyCanopy(X,Y,Seed,Grove));
    const double Gap=E.Gaps.Weight(
        TemperateHillsSurface::Noise5(X/E.GapScaleCm,Y/E.GapScaleCm,Seed,3101)*.5+.5);
    const double Base=Woodland*(1.0-E.GapStrength*Gap);
    if(Region<=0)return Base;
    // Wet forest remains denser inside each stand, with readable gaps between
    // stands. All undergrowth and ground shading consume this same canopy.
    return FMath::Lerp(Base,Local,Region);
}

inline double Canopy(double X,double Y,int32 Seed,double Region,double Opening,const TemperateEcology::FProfile& E)
{
    return CanopyFromGrove(X,Y,Seed,Region,Opening,E,TemperateForestGroves::Sample(X,Y,Seed).Cover);
}

inline double Canopy(double X,double Y,int32 Seed,double Region, const TemperateEcology::FProfile& E)
{
    return Canopy(X,Y,Seed,Region,Region>0?RainforestOpening(X,Y,Seed, E):0., E);
}

inline double Moisture(double X,double Y,int32 Seed,double Region, const TemperateEcology::FProfile& E)
{
    const double Scale=E.MoistureScaleCm;
    const double Base=FMath::SmoothStep(.20,.80,
        TemperateHillsSurface::Noise5(X/Scale,Y/Scale,Seed,3109)*.5+.5);
    return FMath::Lerp(Base,FMath::Max(Base,E.Rainforest.Moisture),Region);
}


inline double UnderstoryPatch(double X,double Y,int32 Seed, const TemperateEcology::FProfile& E)
{
    const double Scale=E.UnderstoryPatchScaleCm;
    return FMath::SmoothStep(.28,.73,
        TemperateHillsSurface::Noise5(X/Scale,Y/Scale,Seed,3119)*.5+.5);
}

// Continuous land-cover weights shared by the streamed terrain and PCG.
// The moisture field sets the broad stands; the slope normal separates warm,
// freely draining faces from sheltered grass and fern sites within a stand.
struct FUpland
{
    double Meadow = 0;
    double Stony = 0;
    double Shelter = 0;
};

inline FUpland Upland(const FVector& Normal, double Forest, double Moist, double Region, const TemperateEcology::FProfile& E)
{
    const double Land = 1.0 - Region;
    const double Slope = 1.0 - FMath::SmoothStep(.82, .994, Normal.Z);
    const double Aspect = FMath::Clamp(.50 + 1.15 * (Normal.X * .80 + Normal.Y * .60), 0., 1.);
    const double Exposure = FMath::Clamp(.46 * (1. - Moist) + Slope * (.34 + .46 * Aspect), 0., 1.);
    const double Open = 1. - FMath::SmoothStep(.15, .83, Forest);
    const auto& Profile = E;
    FUpland Site;
    Site.Stony = Profile.UplandStoneStrength * Land * (.24 + .76 * Open) * FMath::SmoothStep(.30, .82, Exposure);
    Site.Meadow = Profile.UplandMeadowStrength * Land * Open * FMath::SmoothStep(.87, .985, Normal.Z)
        * (.48 + .52 * Moist) * (1. - FMath::SmoothStep(.30, .78, Exposure));
    Site.Shelter = Profile.UplandShelterStrength * Land * FMath::SmoothStep(.15, .73, Forest) * Moist * (1. - .75 * Exposure);
    return Site;
}

inline double UplandSurfaceWeight(double TrailDistance, double Bank, double NormalZ)
{
    // Bare rock takes over below the last plausible soil-bearing slope.
    return FMath::SmoothStep(300.,900.,TrailDistance)*(1.-FMath::SmoothStep(.01,.32,Bank))
        * FMath::SmoothStep(.65,.83,NormalZ);
}

struct FUnderstory
{
    double Edge=0,Shade=0,Moist=0,Patch=0,Shrub=0,Fern=0,Sapling=0;
};

// One shared site description prevents every layer filling the same ground.
// Shrubs favour brighter, drier edges; fern colonies occupy the moist pockets
// between them. Pure seeded maths is also safe in terrain worker jobs.
inline FUnderstory Understory(double X,double Y,int32 Seed,double Forest,double Region,const FVector& Normal, const TemperateEcology::FProfile& E)
{
    FUnderstory S;
    S.Edge=E.EdgeEnter.Weight(Forest)*(1.0-E.EdgeLeave.Weight(Forest));
    S.Shade=E.Shade.Weight(Forest);
    S.Moist=Moisture(X,Y,Seed,Region, E);
    S.Patch=UnderstoryPatch(X,Y,Seed, E);
    const double FernPatch=FMath::SmoothStep(.30,.78,S.Patch);
    const double ShrubPatch=FMath::SmoothStep(.23,.65,1.0-S.Patch);
    S.Shrub=(.85*S.Edge+.20*S.Shade)*(.15+.85*ShrubPatch)*(1.0-.30*S.Moist);
    S.Fern=FMath::SmoothStep(.12,.68,Forest)*(.25+.75*S.Moist)*FernPatch*(1.0-.65*S.Shrub);
    S.Sapling=(.12*S.Shade+.36*S.Edge)*(.25+.75*(1.0-FernPatch))*(1.0-.45*S.Shrub);
    // Mid-storey saplings and shrubs occupy different patches from fern beds.
    S.Shrub=FMath::Max(S.Shrub,Region*.25*S.Shade*(.30+.70*ShrubPatch));
    S.Sapling=FMath::Max(S.Sapling,Region*S.Shade*(.12+.12*(1.0-FernPatch)));
    const FUpland U = Upland(Normal, Forest, S.Moist, Region, E);
    S.Fern *= 1. + .65 * U.Shelter - .78 * U.Stony;
    S.Shrub *= 1. + .26 * U.Meadow - .50 * U.Stony;
    S.Sapling *= 1. + .25 * U.Shelter - .55 * U.Stony;
    return S;
}

// Neighbouring plants share an age/form cohort without a visible cell seam.
inline uint32 Cohort(double X,double Y,int32 Seed,uint32 PlantKey,uint32 Salt, const TemperateEcology::FProfile& E)
{
    const auto Grove=TemperateForestGroves::Sample(X,Y,Seed);
    if(Grove.Cover>.12&&TemperateHillsSurface::Unit(PlantKey+59)<.72)
        return TemperateHillsSurface::Mix(Grove.Key^Salt);
    const double Scale=E.CohortScaleCm;
    const double PX=X/Scale,PY=Y/Scale;
    int32 IX=FMath::FloorToInt(PX),IY=FMath::FloorToInt(PY);
    if(TemperateHillsSurface::Unit(PlantKey+37)<FMath::SmoothStep(0.0,1.0,PX-IX))++IX;
    if(TemperateHillsSurface::Unit(PlantKey+41)<FMath::SmoothStep(0.0,1.0,PY-IY))++IY;
    return TemperateHillsSurface::Key(IX,IY,uint32(Seed),Salt);
}

// Alpha keeps its historical default of 1 outside woodland. RGB remain the
// bank / wetness / pebble contract. No extra runtime texture or GPU readback.
inline double Litter(double X,double Y,int32 Seed,double NormalZ,double Bank,double Forest,
    double Grove,const TemperateEcology::FProfile& E)
{
    const double Path=FMath::Abs(Y-TemperateHillsSurface::ValleyY(X,Seed));
    // Leaves extend past the densest canopy and remain in small gaps; their
    // thickness varies over the same patches as the understory.
    const double Cover=.85*Forest+.15*LegacyCanopy(X,Y,Seed,Grove);
    const double Deposit=.82+.18*UnderstoryPatch(X,Y,Seed, E);
    return FMath::SmoothStep(.04,.84,Cover)*Deposit*FMath::SmoothStep(.76,.95,NormalZ)
        *FMath::SmoothStep(450.0,1700.0,Path)*(1.0-FMath::SmoothStep(.02,.45,Bank));
}
}
