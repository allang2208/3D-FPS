#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"
#include "TemperateForestHabitat.h"
#include "Engine/StaticMesh.h"

// Forest-floor deadwood and hillside cliffs ride the rock PCG layer (Layer 1) so
// they inherit its 120 m generation radius, collision and cleanup without a new
// streaming stage. Candidate IDs share the rock namespace shape (packed cell
// coordinates) with a dedicated high-bit tag so they never collide with
// harvestable stones: 0x2000.. deadwood tiles, 0x1000.. cliff tiles, 0x4000..
// already marks river stones. Mining stays safe through the existing resolver —
// ResolveProductionResource matches a candidate by position plus mesh path, and
// the production resolver explicitly excludes FallenLogs/ForestRoots from ore.
void ATemperateHillsWorld::GetForestFloorPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!Assets)return;
    using namespace TemperateHillsSurface;
    if(ForestWaterPlan&&Assets->RainforestBankBoulder.IsValid())
    {
        for(int32 I=0;I<ForestWaterPlan->Pools.Num();++I)
        {
            const auto& Pool=ForestWaterPlan->Pools[I];
            if(!Pool.Bounds.ExpandBy(350.).Intersect(FBox2D(FVector2D(Bounds.Min),FVector2D(Bounds.Max))))continue;
            const FVector2D Center=Pool.Bounds.GetCenter();
            const uint32 K=Key(I,0,uint32(Seed),2537);
            const double Angle=I==0?-.68:Unit(K+1)*2*PI;
            const FVector2D Dir(FMath::Cos(Angle),FMath::Sin(Angle));
            const double Reach=Pool.Bounds.GetExtent().Size()+250.;
            // Approach from dry land. Irregular/concave pool outlines do not
            // necessarily contain their bounding-box centre.
            for(double R=Reach;R>=0;R-=40.)
            {
                const FVector2D Edge=Center+Dir*R;
                if(!ForestWaterPlan->Sample(Edge.X,Edge.Y).Wet)continue;
                const FVector2D At=Edge+Dir*75.;
                if(At.X<Bounds.Min.X||At.X>=Bounds.Max.X||At.Y<Bounds.Min.Y||At.Y>=Bounds.Max.Y||
                    PathDistance(At.X,At.Y)<420||SurfaceNormal(At.X,At.Y).Z<.88)break;
                FTemperatePlacement P;
                P.Mesh=Assets->RainforestBankBoulder.ToSoftObjectPath();P.Key=K;
                P.Transform=FTransform(FRotator(0,Unit(K+2)*360.,0),FVector(At,Height(At.X,At.Y)),FVector(.78+Unit(K+3)*.36));
                P.CandidateId=0x3000000000000000ULL|uint64(I);
                Out.Add(P);break;
            }
        }
    }
    if(Assets->FallenLogs.IsEmpty()&&Assets->ForestRoots.IsEmpty())return;
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
        const double Region=RainforestWeight(X,Y);
        const auto Site=TemperateForestHabitat::Upland(N,Forest,TemperateForestHabitat::Moisture(X,Y,Seed,Region, EcologyProfile()),Region, EcologyProfile());
        const double Deadwood=Coverage*(.08+.92*Smooth(Forest/.5))*
            (1.+.48*Site.Shelter-.68*Site.Meadow-.52*Site.Stony);
        if(Unit(K+3)>Deadwood)continue;
        // Roots are the rarer member of the family.
        const bool Root=!Assets->ForestRoots.IsEmpty()&&(Assets->FallenLogs.IsEmpty()||Unit(K+6)<.30);
        const auto& Mesh=(Root?Assets->ForestRoots:Assets->FallenLogs)[K%(Root?Assets->ForestRoots:Assets->FallenLogs).Num()];
        const UStaticMesh* Loaded=Mesh.Get();
        if(!Loaded)continue;
        const FBox Box=Loaded->GetBoundingBox();
        // The source pack includes an 18 m log. Normalize the selected mesh to
        // a modest 2.8-6.2 m fallen trunk instead of scattering giant set pieces.
        const double LongSide=FMath::Max(Box.GetSize().X,Box.GetSize().Y);
        const double Scale=Root?(.65+Unit(K+7)*.30):(280+Unit(K+7)*340)/FMath::Max(1.0,LongSide);
        const FQuat Rotation=FQuat(N,Unit(K+4)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,N);
        // Fit both ends and the middle to the generated surface. Reject a log
        // bridging a hollow, road or river instead of balancing it on one pivot.
        const FVector Center(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z);
        const FVector Axis=Box.GetSize().X>Box.GetSize().Y?FVector(1,0,0):FVector(0,1,0);
        double Low=DBL_MAX,High=-DBL_MAX;
        bool Supported=true;
        for(int32 I=-1;I<=1;++I)
        {
            const FVector Offset=Rotation.RotateVector((Center+Axis*(I*LongSide*.36))*Scale);
            const double PX=X+Offset.X,PY=Y+Offset.Y;
            if(FMath::Abs(PX)>Half||FMath::Abs(PY)>Half||PathDistance(PX,PY)<450||
                (RiverPlan&&RiverPlan->Sample(PX,PY).Bank>.08)){Supported=false;break;}
            const double Support=Height(PX,PY)-Offset.Z;
            Low=FMath::Min(Low,Support);High=FMath::Max(High,Support);
        }
        if(!Supported||High-Low>42)continue;
        const FVector Location(X,Y,(Low+High)*.5-6);
        const uint64 CandidateId=((uint64(uint32(GX))<<32)|uint32(GY))^0x2000000000000000ULL;
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
        if(Bank.Bank>.02 || Bank.CliffWeight>.25)continue;
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
        FTemperatePlacement& P=Out.Emplace_GetRef();
        P.Transform=FTransform(FRotator(0,FMath::RadiansToDegrees(Yaw),0),Location,FVector(Scale));
        P.Mesh=Mesh.ToSoftObjectPath();P.Key=K;
        P.CandidateId=CandidateId;
    }
}
