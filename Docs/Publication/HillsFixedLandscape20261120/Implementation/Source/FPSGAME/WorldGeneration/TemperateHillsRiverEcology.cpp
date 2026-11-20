#include "TemperateHillsWorld.h"
#include "TemperateHillsMap.h"
#include "TemperateLakeCoveOutlet.h"
#include "TemperateHillsSurface.h"
#include "TemperateShoreHabitat.h"
#include "TemperateVegetationPlacement.h"
#include "TemperateEcologyConfig.h"
#include "Engine/StaticMesh.h"

namespace HillsRiverEcology
{
double Smooth(double T)
{
    T=FMath::Clamp(T,0.0,1.0);
    return T*T*(3-2*T);
}

uint32 Species(double X,double Y,int32 Seed,int32 Zone,uint32 K)
{
    using namespace TemperateHillsSurface;
    // Blend the dominant species between warped 7 m patches; occasional other
    // species break up monocultures without drawing straight patch boundaries.
    const double PX=(X+Noise(X*.001,Y*.001,Seed,2203)*250)/700;
    const double PY=(Y+Noise(X*.001,Y*.001,Seed,2207)*250)/700;
    int32 IX=FMath::FloorToInt(PX),IY=FMath::FloorToInt(PY);
    if(Unit(K+6)<Smooth(PX-IX))++IX;
    if(Unit(K+7)<Smooth(PY-IY))++IY;
    return Unit(K+8)<.20?Mix(K+29):Key(IX,IY,Seed,2213+Zone*19);
}
}

void ATemperateHillsWorld::GetRiverPlantPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!RiverPlan||!Assets||!RiverPlan->IntersectsCell(Bounds.Min.X,Bounds.Min.Y,
        FMath::Max(Bounds.Max.X-Bounds.Min.X,Bounds.Max.Y-Bounds.Min.Y)))return;
    using namespace TemperateHillsSurface;
    using HillsRiverEcology::Smooth;
    const auto& Ecology=EcologyProfile();
    const double Half=SizeMeters*50-500;
    const FVector2D Start(GetStartLocation());
    for(int32 Zone=0;Zone<4;++Zone)
    {
        // Low ground cover, emergent reeds, flowering/seed-head grasses, leaves.
        const auto& Meshes=Zone==0?Assets->RiverGroundCover:Zone==1?Assets->RiverReeds:
            Zone==2?Assets->RiverBankGrasses:Assets->RiverUnderstory;
        const auto& Rule=Zone==0?Ecology.RiverGroundCover:Zone==1?Ecology.RiverReeds:
            Zone==2?Ecology.RiverGrass:Ecology.RiverUnderstory;
        if(Meshes.IsEmpty()||Rule.Density<=0)continue;
        const double Spacing=Zone==0?FMath::Clamp(Assets->RiverGroundCoverSpacingCm,40.f,150.f):
            Zone==1?95:Zone==2?115:180;
        const double Tile=Spacing*2;
        const double Coverage=Rule.Density;
        for(int32 Y=FMath::FloorToInt(Bounds.Min.Y/Tile);Y<=FMath::FloorToInt(Bounds.Max.Y/Tile);++Y)
        for(int32 X=FMath::FloorToInt(Bounds.Min.X/Tile);X<=FMath::FloorToInt(Bounds.Max.X/Tile);++X)
        {
            using namespace TemperateRiver::LakeShoreDetail;
            const double CX=(X+.5)*Tile,CY=(Y+.5)*Tile;
            const bool SurveyTile=Zone==0&&(CoveOutlet::Near(CX,CY,Seed)||NearSurveyTile(CX,CY,Seed));
            const int32 Candidates=SurveyTile?12:Zone==0&&RiverPlan->Lake.HasBankTile(CX,CY)?8:4;
            for(int32 Index=0;Index<Candidates;++Index)
            {
                const uint32 K=Mix(Key(X,Y,Seed,2101+Zone*37)^uint32(Index+1)*0x9e3779b9U);
                const double PX=(X+Unit(K+1))*Tile,PY=(Y+Unit(K+2))*Tile;
                if(PX<Bounds.Min.X||PX>=Bounds.Max.X||PY<Bounds.Min.Y||PY>=Bounds.Max.Y||FMath::Abs(PX)>Half||FMath::Abs(PY)>Half)continue;
                if(FVector2D::DistSquared(FVector2D(PX,PY),Start)<2400*2400)continue;
                const auto R=RiverPlan->Sample(PX,PY);if(R.Bank<=.015)continue;
                if(Index>=4 && Unit(K+19)>=R.LocalShore.Roots)continue;
                const double Edge=R.Distance-R.HalfWidth;
                if(Edge<-180.||Edge>=R.BankExtent)continue;
                const double Z=Height(PX,PY),Above=Z-R.WaterZ;
                const double Outer=1-Smooth((Edge-950)/FMath::Max(300.0,R.BankExtent-950));
                // Keep the established dry path clear; its abstract corridor must
                // not erase the entire planted water edge where it meets the river.
                const double PathBlend=1-Smooth((Edge-650)/550)*(1-Smooth((PathDistance(PX,PY)-220)/220));
                double Habitat=0;
                if(Zone==0 && Above>-3 && Edge>-35)
                    Habitat=Smooth((Above+3)/10)*Outer;
                if(Zone==1 && Above>-22 && Above<155 && Edge>-180 && Edge<1150)
                {
                    Habitat=Smooth((Above+22)/24)*(1-Smooth((Above-85)/70))*(1-Smooth((Edge-550)/600));
                    // Fast flow discourages submerged stems, not dry-bank plants.
                    if(Above<0)Habitat*=1-.65*Smooth((R.Speed-65)/65);
                }
                if(Zone==2 && Above>2 && Edge>-5)
                    Habitat=Smooth((Above-2)/18)*Outer;
                if(Zone==3 && Above>18 && Edge>130)
                    Habitat=Smooth((Edge-130)/250)*Outer*(.48+.52*ForestWeight(PX,PY));
                if(Habitat<=0||PathBlend<=0)continue;
                const double Side=R.SignedDistance>=0?1:-1;
                const double Patch=(R.bLake?TemperateHillsSurface::Noise(PX/1360.,PY/1360.,Seed,2141+Zone):
                    TemperateHillsSurface::Noise(R.Along/1500.,Side*3.2,Seed,2141+Zone))*.5+.5;
                const double Clump=TemperateHillsSurface::Noise(PX/280,PY/280,Seed,2147+Zone)*.5+.5;
                const double Cluster=Smooth((Patch*.40+Clump*.60-.22)/.56);
                // A high floor connects the short grass; taller layers have separate
                // clumps and openings, with no product of several zero-density masks.
                const double Density=Zone==0?.80+.20*Cluster:Zone==1?.24+.76*Cluster:
                    Zone==2?.26+.68*Cluster:.18+.58*Cluster;
                const double Exposure=TemperateShore::Exposure(R);
                const double Gravel=TemperateRiver::PebbleCover(PX,PY,Seed,R);
                const auto Margin=TemperateShore::Margin(PX,PY,Seed,R,Gravel);
                if(Zone==0 || Zone==2)
                    Habitat=FMath::Max(Habitat*(1.-.92*R.LocalShore.Runnel)*(1.-.76*R.LocalShore.Spine),
                        R.LocalShore.Roots*FMath::SmoothStep(3.,18.,Above));
                // Reeds collect in sheltered pockets. Ground cover recedes on the
                // same mineral patches drawn by the ground shader and geometry.
                if(Zone==1)Habitat*=FMath::Lerp(.10,1.,(1.-Exposure)*Smooth((Patch-.22)/.50))*
                    (1.-.76*Margin.Ledge)*(1.-.68*Margin.Turf);
                const double StoneSpace=1.-(Zone==0?.86:Zone==1?.83:.60)*Gravel*(1.-R.LocalShore.Roots);
                if(Unit(K+3)>Coverage*Habitat*PathBlend*Density*StoneSpace)continue;
                const FVector N=SurfaceNormal(PX,PY);
                const double SlopeWeight=Rule.SlopeWeight(N.Z);
                if(SlopeWeight<=0||Unit(K+10)>SlopeWeight)continue;
                const bool Turf=Zone==0&&Above>8.&&Unit(K+12)<.78*Margin.Turf;
                const uint32 Group=HillsRiverEcology::Species(PX,PY,Seed,Zone,K);
                const auto* Palette=&Meshes;
                if(Turf)
                {
                    // Pools of woodland carpet overlap the drier grass at the
                    // forest margin. Keep the same species together within each patch.
                    const double Forest=RainforestWeight(PX,PY);
                    const bool WoodlandTurf=Seed==SurveySeed?Unit(Group^0x7304ce1dU)<FMath::SmoothStep(.28,.77,Forest):Forest>.55;
                    const auto& LandGrass=WoodlandTurf?Assets->RainforestCarpetGrass:Assets->Grass;
                    if(!LandGrass.IsEmpty())Palette=&LandGrass;
                }
                const auto& Mesh=(*Palette)[Group%Palette->Num()];
                // Streaming preloads all selected meshes. Height normalization makes
                // source pack variants share a deliberate plant layer in centimetres.
                const UStaticMesh* Loaded=Mesh.Get();if(!Loaded)continue;
                const FBox MeshBounds=HillsVegetation::BoundsOf(Loaded);
                const double PlantHeight=Zone==0?(Turf?20.+Unit(K+4)*22.:16.+Unit(K+4)*20.):
                    Zone==1?(48.+(42.+68.*Cluster)*(.35+.65*Unit(K+4)))*(1.-.28*Exposure):
                    Zone==2?48+Unit(K+4)*55:32+Unit(K+4)*32;
                const double Shorten=Zone==0?.32*R.LocalShore.ShortGrass:0.;
                const double Scale=PlantHeight*(1.-Shorten)/FMath::Max(1.0,MeshBounds.GetSize().Z);
                const FVector Up=FMath::Lerp(FVector::UpVector,N,Zone==1?.12:(Zone==0?.75:.55)).GetSafeNormal();
                const FQuat Rotation=FQuat(Up,Unit(K+5)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,Up);
                FTemperatePlacement& P=Out.Emplace_GetRef();
                P.Transform=FTransform(Rotation,FVector(PX,PY,Z-MeshBounds.Min.Z*Scale-2),FVector(Scale));
                P.Mesh=Mesh.ToSoftObjectPath();P.Key=K;
                P.CandidateId=(uint64(uint32(X)&0xffffffU)<<32)|(uint64(uint32(Y)&0xffffffU)<<8)|uint64(Index<4?0x40+Zone*4+Index:0x80+Index);
            }
        }
    }
}

void ATemperateHillsWorld::GetRiverShrubPlacements(const FBox& Bounds,TArray<FTemperatePlacement>& Out) const
{
    if(!RiverPlan||!Assets||Assets->Shrubs.IsEmpty()||!RiverPlan->IntersectsCell(Bounds.Min.X,Bounds.Min.Y,
        FMath::Max(Bounds.Max.X-Bounds.Min.X,Bounds.Max.Y-Bounds.Min.Y)))return;
    using namespace TemperateHillsSurface;
    using HillsRiverEcology::Smooth;
    const auto& Rule=EcologyProfile().RiverShrubs;
    if(Rule.Density<=0)return;
    constexpr double Tile=650;
    const double Half=SizeMeters*50-500;
    const FVector2D Start(GetStartLocation());
    for(int32 Y=FMath::FloorToInt(Bounds.Min.Y/Tile);Y<=FMath::FloorToInt(Bounds.Max.Y/Tile);++Y)
    for(int32 X=FMath::FloorToInt(Bounds.Min.X/Tile);X<=FMath::FloorToInt(Bounds.Max.X/Tile);++X)
    for(int32 Index=0;Index<3;++Index)
    {
        const uint32 K=Mix(Key(X,Y,Seed,2269)^uint32(Index+1)*0x9e3779b9U);
        const double PX=(X+Unit(K+1))*Tile,PY=(Y+Unit(K+2))*Tile;
        if(PX<Bounds.Min.X||PX>=Bounds.Max.X||PY<Bounds.Min.Y||PY>=Bounds.Max.Y||FMath::Abs(PX)>Half||FMath::Abs(PY)>Half)continue;
        if(FVector2D::DistSquared(FVector2D(PX,PY),Start)<2400*2400||PathDistance(PX,PY)<450)continue;
        const auto R=RiverPlan->Sample(PX,PY);
        const double Edge=R.Distance-R.HalfWidth;
        if(R.Bank<.02||Edge<450)continue;
        const double Z=Height(PX,PY);if(Z<R.WaterZ+40)continue;
        const double Patch=TemperateHillsSurface::Noise(PX/850,PY/850,Seed,2273)*.5+.5;
        const double Habitat=Smooth((Edge-450)/400)*(1-Smooth((Edge-1400)/1000));
        const double Chance=Rule.Density*Habitat*(.08+.52*Smooth((Patch-.28)/.48));
        if(Unit(K+3)>Chance)continue;
        const FVector N=SurfaceNormal(PX,PY);
        const double SlopeWeight=Rule.SlopeWeight(N.Z);
        if(SlopeWeight<=0||Unit(K+3)>Chance*SlopeWeight)continue;
        // Young alders occupy the damp, sheltered back of an existing shrub clump.
        // The exposed headland, active gravel and the top of the bank keep their hazel.
        bool bAlder=false;
        if(Seed==TemperateHillsMap::Seed&&GeneratorVersion==TemperateHillsMap::GeneratorVersion
            &&!Assets->WetBankSaplings.IsEmpty()&&Z-R.WaterZ<205.&&N.Z>.93)
        {
            const double Shelter=1.-Smooth((TemperateShore::Exposure(R)-.22)/.46);
            const double Moist=1.-Smooth((Z-R.WaterZ-90.)/115.);
            const double Copse=Smooth((Patch-.36)/.35);
            bAlder=Unit(K+31)<.52*Shelter*Moist*Copse;
        }
        const auto& Palette=bAlder?Assets->WetBankSaplings:Assets->Shrubs;
        const auto& Mesh=Palette[HillsRiverEcology::Species(PX,PY,Seed,4,K)%Palette.Num()];
        const UStaticMesh* Loaded=Mesh.Get();if(!Loaded)continue;
        const FBox MeshBounds=HillsVegetation::BoundsOf(Loaded);
        const double HeightCm=bAlder?145.+Unit(K+4)*115.:70.+Unit(K+4)*75.;
        const double Scale=HeightCm/FMath::Max(1.0,MeshBounds.GetSize().Z);
        const FVector Up=FMath::Lerp(FVector::UpVector,N,bAlder?.10:.25).GetSafeNormal();
        FTemperatePlacement& P=Out.Emplace_GetRef();
        P.Transform=FTransform(FQuat(Up,Unit(K+5)*2*PI)*FQuat::FindBetweenNormals(FVector::UpVector,Up),
            FVector(PX,PY,Z-MeshBounds.Min.Z*Scale-3),FVector(Scale));
        P.Mesh=Mesh.ToSoftObjectPath();P.Key=K;
        // The ordinary shrub grid uses CellId, whose high sign bits match.
        // These differing high bits reserve a separate, non-harvestable range.
        P.CandidateId=0x8000000000000000ULL|(uint64(uint32(X)&0xffffffU)<<32)|
            (uint64(uint32(Y)&0xffffffU)<<8)|uint64(Index);
    }
}
