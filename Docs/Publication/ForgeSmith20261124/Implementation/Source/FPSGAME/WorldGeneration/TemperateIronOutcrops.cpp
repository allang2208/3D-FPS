#include "TemperateIronOutcrops.h"
#include "TemperateHillsWorld.h"
#include "TemperateHillsSurface.h"
#include "../Production/ProductionOreRocks.h"
#include "Engine/StaticMesh.h"

namespace TemperateIronOutcrops
{
    constexpr double Spacing=15400., Reach=1550.;
    // An exposed main seam, a short parallel ledge, and two pieces of downhill float (cm).
    const FVector2D Seam[]={{-1050,-85},{-790,-20},{-510,32},{-245,25},{35,90},{325,130},{615,220},{895,290},
        {-630,480},{-320,510},{-25,555},{310,598},{670,-360},{1050,-500}};

    FVector2D Centre(int32 X,int32 Y,uint32 K)
    {
        return {(X+.5+.43*(TemperateHillsSurface::Unit(K+1)-.5))*Spacing,
                (Y+.5+.43*(TemperateHillsSurface::Unit(K+2)-.5))*Spacing};
    }

    void Gather(const ATemperateHillsWorld& Hills,const FBox& Bounds,TArray<FTemperatePlacement>& Out)
    {
        const double Edge=Hills.SizeMeters*50.-200.;
        const int32 Limit=FMath::CeilToInt(Edge/Spacing);
        const int32 MinX=FMath::Max(-Limit,FMath::FloorToInt((Bounds.Min.X-Reach)/Spacing));
        const int32 MinY=FMath::Max(-Limit,FMath::FloorToInt((Bounds.Min.Y-Reach)/Spacing));
        const int32 MaxX=FMath::Min(Limit-1,FMath::FloorToInt((Bounds.Max.X+Reach)/Spacing));
        const int32 MaxY=FMath::Min(Limit-1,FMath::FloorToInt((Bounds.Max.Y+Reach)/Spacing));
        for (int32 Y=MinY;Y<=MaxY;++Y)
        for (int32 X=MinX;X<=MaxX;++X)
        {
            const uint32 K=TemperateHillsSurface::Key(X,Y,Hills.Seed,41713);
            const FVector2D Site=Centre(X,Y,K);
            if (!Bounds.ExpandBy(Reach).IsInsideOrOnXY(FVector(Site,0))) continue;
            const double Angle=360.*TemperateHillsSurface::Unit(K+3);
            for (int32 I=0;I<UE_ARRAY_COUNT(Seam);++I)
            {
                const uint32 Key=TemperateHillsSurface::Mix(K+593*I);
                const FVector2D Jitter((TemperateHillsSurface::Unit(Key+1)-.5)*58.,(TemperateHillsSurface::Unit(Key+2)-.5)*95.);
                const FVector2D P=Site+(Seam[I]+Jitter).GetRotated(Angle);
                if (P.X<Bounds.Min.X || P.X>=Bounds.Max.X || P.Y<Bounds.Min.Y || P.Y>=Bounds.Max.Y ||
                    FMath::Abs(P.X)>Edge || FMath::Abs(P.Y)>Edge || Hills.SampleRiver(P.X,P.Y).Bank>.025 ||
                    Hills.SampleForestWater(P.X,P.Y).Wet) continue;
                const FVector N=Hills.SurfaceNormal(P.X,P.Y);
                if (N.Z<.89) continue;
                const auto Path=ProductionOreRocks::Mesh(TEXT("iron_ore"),ProductionOreRocks::Shape(Key));
                const auto* Mesh=Cast<UStaticMesh>(Path.ResolveObject());
                if (!Mesh) continue;
                auto& Rock=Out.AddDefaulted_GetRef();
                Rock.Mesh=Path;
                Rock.Key=Key;
                Rock.CandidateId=(0x4956ULL<<48)|(uint64(uint16(X))<<24)|(uint64(uint16(Y))<<8)|uint64(I);
                Rock.Transform=ProductionOreRocks::Placement(*Mesh,Key,FVector(P,Hills.Height(P.X,P.Y)),N);
                if (I<12)
                {
                    // Broad, partly buried ribs follow the seam. The two loose rocks retain their tumble.
                    const bool LongX=Mesh->GetBoundingBox().GetSize().X>=Mesh->GetBoundingBox().GetSize().Y;
                    const double Strike=Angle+12.+(LongX ? 0. : 90.)+24.*(TemperateHillsSurface::Unit(Key+4)-.5);
                    const FQuat Orient=FQuat(N,FMath::DegreesToRadians(Strike))*FQuat::FindBetweenNormals(FVector::UpVector,N);
                    Rock.Transform.SetRotation(Orient);
                    const double Length=I<8 ? 1.22 : 1.08;
                    Rock.Transform.SetScale3D(Rock.Transform.GetScale3D()*FVector(LongX ? Length : .9,LongX ? .9 : Length,I<8 ? .96 : .77));
                }
                else Rock.Transform.SetScale3D(Rock.Transform.GetScale3D()*.74);
            }
        }
    }
}

bool ATemperateHillsWorld::FindNearestIronOutcrop(const FVector2D& From,TemperateIronOutcrops::FSearch& Search,FVector& OutPoint,uint64& OutRock) const
{
    using namespace TemperateIronOutcrops;
    if (IsForestVillage() || !bReady || !Assets || !ProductionOreRocks::Mesh(TEXT("iron_ore"),0).ResolveObject()) return false;
    const double Edge=SizeMeters*50.;
    if (Search.Edge!=Edge || Search.Seed!=Seed || Search.From!=From)
    {
        Search.Next=0;
        Search.From=From;
        Search.Seed=Seed;
        Search.Edge=Edge;
        Search.Sites.Reset();
        const int32 Limit=FMath::CeilToInt(Edge/Spacing);
        for (int32 Y=-Limit;Y<Limit;++Y)
        for (int32 X=-Limit;X<Limit;++X)
        {
            const auto C=Centre(X,Y,TemperateHillsSurface::Key(X,Y,Seed,41713));
            if (FMath::Abs(C.X)<Edge+Reach && FMath::Abs(C.Y)<Edge+Reach) Search.Sites.Add(C);
        }
        Search.Sites.Sort([&](const FVector2D& A,const FVector2D& B){return FVector2D::DistSquared(A,From)<FVector2D::DistSquared(B,From);});
    }
    const auto& Sites=Search.Sites;
    int32& NextSite=Search.Next;
    // Continue over map refreshes so a depleted world cannot query all rock cells in one frame.
    const int32 End=FMath::Min(NextSite+2,Sites.Num());
    for (;NextSite<End;++NextSite)
    {
        const auto& C=Sites[NextSite];
        TArray<FTemperatePlacement> Rocks;
        const FVector Extent(Reach,Reach,HALF_WORLD_MAX);
        GetRockPlacements(FBox(FVector(C,0)-Extent,FVector(C,0)+Extent),Rocks);
        double Best=DBL_MAX;
        for (const auto& Rock:Rocks)
        {
            if (!IsVeinRock(Rock.CandidateId)) continue;
            const FVector At=Rock.Transform.GetLocation();
            const double Dist=FVector2D::DistSquared(FVector2D(At),C);
            if (Dist<Best) { Best=Dist; OutPoint=At; OutRock=Rock.CandidateId; }
        }
        if (Best<DBL_MAX) return true;
    }
    if (NextSite>=Sites.Num()) NextSite=INDEX_NONE;
    return false;
}
