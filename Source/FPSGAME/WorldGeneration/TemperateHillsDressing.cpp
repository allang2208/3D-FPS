#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"
#include "Engine/StaticMesh.h"

// Forest-floor deadwood and hillside cliffs ride the rock PCG layer (Layer 1) so
// they inherit its 120 m generation radius, collision and cleanup without a new
// streaming stage. Candidate IDs share the rock namespace shape (packed cell
// coordinates) with a dedicated high-bit tag so they never collide with
// harvestable stones: 0x2000.. deadwood tiles, 0x1000.. cliff tiles, 0x4000..
// already marks river stones. Mining stays safe through the existing resolver —
// ResolveProductionResource matches a candidate by position plus mesh path, and
// every piece here is either larger than the 500 cm instance-radius reject or
// resolves as generic stone for small snag-sized logs.
void ATemperateHillsWorld::GetForestFloorPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!Assets||(Assets->FallenLogs.IsEmpty()&&Assets->ForestRoots.IsEmpty()))return;
    using namespace TemperateHillsSurface;
    const double Coverage=FMath::Clamp(Assets->ForestFloorCoverage,0.f,1.f);
    const double Half=SizeMeters*50-500;
    const FVector2D Start(GetStartLocation());
    auto Smooth=[](double T){T=FMath::Clamp(T,0.0,1.0);return T*T*(3-2*T);};
    // One candidate per 36 m tile keeps deadwood occasional even under full canopy.
    constexpr double Tile=3600;
    for(int32 GY=FMath::FloorToInt(Bounds.Min.Y/Tile)-1;GY<=FMath::FloorToInt(Bounds.Max.Y/Tile);++GY)
    for(int32 GX=FMath::FloorToInt(Bounds.Min.X/Tile)-1;GX<=FMath::FloorToInt(Bounds.Max.X/Tile);++GX)
    {
        const uint32 K=Mix(Key(GX,GY,uint32(Seed),2511));
        const double X=(GX+.15+Unit(K+1)*.7)*Tile,Y=(GY+.15+Unit(K+2)*.7)*Tile;
        if(X<Bounds.Min.X||X>=Bounds.Max.X||Y<Bounds.Min.Y||Y>=Bounds.Max.Y)continue;
        if(FMath::Abs(X)>Half||FMath::Abs(Y)>Half)continue;
        if(FVector2D::DistSquared(FVector2D(X,Y),Start)<1800.0*1800.0)continue;
        if(PathDistance(X,Y)<700)continue;
        const auto Bank=RiverPlan?RiverPlan->Sample(X,Y):TemperateRiver::FSample();
        if(Bank.Bank>.05)continue;
        const FVector N=SurfaceNormal(X,Y);
        // Deadwood reads as dumped on flat ground; on slopes it slides visually.
        if(N.Z<.85)continue;
        // Under-canopy gate plus a small clearing chance: logs also sit where a
        // tree fell out of a gap, but never in open meadow density.
        const double Forest=ForestWeight(X,Y);
        if(Unit(K+3)>Coverage*(.08+.92*Smooth(Forest/.5)))continue;
        // Roots are the rarer member of the family.
        const bool Root=!Assets->ForestRoots.IsEmpty()&&(Assets->FallenLogs.IsEmpty()||Unit(K+6)<.30);
        const auto& Mesh=(Root?Assets->ForestRoots:Assets->FallenLogs)[K%(Root?Assets->ForestRoots:Assets->FallenLogs).Num()];
        const UStaticMesh* Loaded=Mesh.Get();
        if(!Loaded)continue;
        const FBox Box=Loaded->GetBoundingBox();
        const double Scale=.85+Unit(K+7)*.45;
        const FQuat Rotation=FQuat(N,Unit(K+4)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,N);
        // Sink the base so contact shadows do not float above the canopy litter.
        const FVector Location=FVector(X,Y,Height(X,Y)-(Box.Min.Z+8)*Scale);
        const uint64 CandidateId=((uint64(uint32(GX))<<32)|uint32(GY))^0x2000000000000000ULL;
        if(IsProductionDepleted(1,CandidateId))continue;
        FTemperatePlacement& P=Out.Emplace_GetRef();
        P.Transform=FTransform(Rotation,Location,FVector(Scale));
        P.Mesh=Mesh.ToSoftObjectPath();P.Key=K;
        P.CandidateId=CandidateId;
    }
}

void ATemperateHillsWorld::GetCliffPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!Assets||Assets->Cliffs.IsEmpty())return;
    using namespace TemperateHillsSurface;
    const double Coverage=FMath::Clamp(Assets->CliffCoverage,0.f,1.f);
    const double Half=SizeMeters*50-500;
    const FVector2D Start(GetStartLocation());
    auto Smooth=[](double T){T=FMath::Clamp(T,0.0,1.0);return T*T*(3-2*T);};
    // A 52 m tile limits how often a massive rock wall can compete for a slope.
    constexpr double Tile=5200;
    for(int32 GY=FMath::FloorToInt(Bounds.Min.Y/Tile)-1;GY<=FMath::FloorToInt(Bounds.Max.Y/Tile);++GY)
    for(int32 GX=FMath::FloorToInt(Bounds.Min.X/Tile)-1;GX<=FMath::FloorToInt(Bounds.Max.X/Tile);++GX)
    {
        const uint32 K=Mix(Key(GX,GY,uint32(Seed),2517));
        const double X=(GX+.5+(Unit(K+1)-.5)*.8)*Tile,Y=(GY+.5+(Unit(K+2)-.5)*.8)*Tile;
        if(X<Bounds.Min.X||X>=Bounds.Max.X||Y<Bounds.Min.Y||Y>=Bounds.Max.Y)continue;
        if(FMath::Abs(X)>Half||FMath::Abs(Y)>Half)continue;
        if(FVector2D::DistSquared(FVector2D(X,Y),Start)<2600.0*2600.0)continue;
        if(PathDistance(X,Y)<1200)continue;
        const auto Bank=RiverPlan?RiverPlan->Sample(X,Y):TemperateRiver::FSample();
        if(Bank.Bank>.02)continue;
        const FVector N=SurfaceNormal(X,Y);
        // Steep-enough-to-need-a-face band: below ~38 deg a wall is pointless,
        // above ~66 deg the heightfield never produces real cliffs anyway.
        if(N.Z>.78||N.Z<.40)continue;
        // Concentrate on the same stony ground the material paints pale/dry so a
        // cliff face arrives where the soil already reads rocky.
        const double WX=X+Noise(X*.0004,Y*.0004,1411)*650;
        const double WY=Y+Noise(X*.0004,Y*.0004,1417)*650;
        const double Patch=Noise(WX*.0000405,WY*.0000405,1459)*.5+.5;
        const double Dry=Smooth((.58-Patch)/.40);
        const double Chance=Coverage*(.25+.75*Dry)*Smooth((.78-N.Z)/.20);
        if(Unit(K+3)>Chance)continue;
        const auto& Mesh=Assets->Cliffs[K%Assets->Cliffs.Num()];
        const UStaticMesh* Loaded=Mesh.Get();
        if(!Loaded)continue;
        const FBox Box=Loaded->GetBoundingBox();
        const double Scale=.9+Unit(K+5)*.5;
        // Face the wall downhill (terrain normal XY points down-gradient) with a
        // little yaw jitter so repeated modules do not line up like a wall chain.
        const double Yaw=FMath::Atan2(N.Y,N.X)+(Unit(K+4)-.5)*.7;
        const FVector Size=Box.GetSize();
        // Bury the base and a share of the height so the face grows out of the
        // slope instead of resting on it like a prop.
        const FVector Location=FVector(X,Y,Height(X,Y)-(Box.Min.Z)*Scale-Size.Z*Scale*.14);
        const uint64 CandidateId=((uint64(uint32(GX))<<32)|uint32(GY))^0x1000000000000000ULL;
        if(IsProductionDepleted(1,CandidateId))continue;
        FTemperatePlacement& P=Out.Emplace_GetRef();
        P.Transform=FTransform(FRotator(0,FMath::RadiansToDegrees(Yaw),0),Location,FVector(Scale));
        P.Mesh=Mesh.ToSoftObjectPath();P.Key=K;
        P.CandidateId=CandidateId;
    }
}
