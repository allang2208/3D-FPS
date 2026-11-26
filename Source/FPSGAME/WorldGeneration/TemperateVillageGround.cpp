#include "TemperateVillageGround.h"
#include "TemperateHillsWorld.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "DynamicMesh/DynamicMeshAttributeSet.h"
#include "Engine/StaticMesh.h"
#include "Algo/BinarySearch.h"

namespace TemperateVillageGround
{
namespace
{
struct FGravel
{
    int16 X, Y;
    uint8 Diameter, Yaw, Variant;
};
#include "TemperateVillageGroundData.inl"

const FSoftObjectPath Stones[] = {
    FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/VillageWindmill/Yard/Meshes/SM_MillFieldstoneB.SM_MillFieldstoneB")),
    FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/WhiteCliffs/Meshes/Fractures/SM_QuarryChip01.SM_QuarryChip01")),
    FSoftObjectPath(TEXT("/Game/WorldGeneration/TemperateHills/WhiteCliffs/Meshes/Fractures/SM_QuarryChip04.SM_QuarryChip04"))
};

int8 VertexHeight(int32 X,int32 Y,bool bRepaired)
{
    // Original village elevations in the smith's yard, starting at (-45,-12) metres.
    static constexpr int8 Ruined[][8]={
        {3,2,3,2,1,0,0,1},{1,2,2,3,2,1,1,1},{0,0,0,3,4,1,2,1},
        {0,0,0,0,2,1,2,3},{0,0,0,0,2,1,0,0},{0,0,0,0,3,1,0,0},{1,0,0,2,2,1,0,0}};
    const int32 U=X-(HalfX/100-45), V=Y-(HalfY/100-12);
    if (!bRepaired && U>=0 && U<UE_ARRAY_COUNT(Ruined[0]) && V>=0 && V<UE_ARRAY_COUNT(Ruined))
        return Ruined[V][U];
    return Relief[Y][X];
}

double LocalHeight(FVector2D P,bool bRepaired)
{
    if (FMath::Abs(P.X)>=HalfX || FMath::Abs(P.Y)>=HalfY) return 0.;
    const double X=(P.X+HalfX)*.01, Y=(P.Y+HalfY)*.01;
    const int32 I=FMath::Min(int32(X),Columns-2), J=FMath::Min(int32(Y),Rows-2);
    const double U=X-I, V=Y-J;
    return FMath::Lerp(FMath::Lerp(double(VertexHeight(I,J,bRepaired)),double(VertexHeight(I+1,J,bRepaired)),U),
                       FMath::Lerp(double(VertexHeight(I,J+1,bRepaired)),double(VertexHeight(I+1,J+1,bRepaired)),U),V);
}

bool Near(const FTemperateVillageSite& Village, double X, double Y, double MarginX=0., double MarginY=0.)
{
    // The circumscribed radius works at every village yaw and on the older valley sites.
    constexpr double Radius=8300.;
    return Village.bPlaced && FMath::Abs(X-Village.Ground.X)<=Radius+MarginX
                           && FMath::Abs(Y-Village.Ground.Y)<=Radius+MarginY;
}
}

double Offset(const FTemperateVillageSite& Village, double X, double Y)
{
    return Near(Village,X,Y) ? LocalHeight(Village.Local(X,Y),Village.bSmithYardRepaired) : 0.;
}

void ShapeCell(const FTemperateVillageSite& Village, FVector2D Origin, double CellSize, UE::Geometry::FDynamicMesh3& Mesh)
{
    const double Half=CellSize*.5;
    if (!Near(Village,Origin.X+Half,Origin.Y+Half,Half,Half) || Mesh.VertexCount()<4) return;
    // The serialized and procedural meshes have the same row-major surface,
    // followed by the bottom skirt. Only the shared top needs displacement.
    const double Step=Mesh.GetVertex(1).X;
    const int32 Side=FMath::RoundToInt(CellSize/Step)+1;
    auto* Normals=Mesh.Attributes()->PrimaryNormals();
    for (int32 I=0; I<Side*Side; ++I)
    {
        FVector3d Vertex=Mesh.GetVertex(I);
        const FVector2D P=Village.Local(Origin.X+Vertex.X, Origin.Y+Vertex.Y);
        if (FMath::Abs(P.X)>HalfX || FMath::Abs(P.Y)>HalfY) continue;
        Vertex.Z+=LocalHeight(P,Village.bSmithYardRepaired);
        Mesh.SetVertex(I,Vertex);
        // Central differences in the same world directions on both sides of each cell seam.
        const FVector2D DX(Village.Axis.X*50.,-Village.Axis.Y*50.);
        const FVector2D DY(Village.Axis.Y*50., Village.Axis.X*50.);
        const double GX=(LocalHeight(P+DX,Village.bSmithYardRepaired)-LocalHeight(P-DX,Village.bSmithYardRepaired))*.01;
        const double GY=(LocalHeight(P+DY,Village.bSmithYardRepaired)-LocalHeight(P-DY,Village.bSmithYardRepaired))*.01;
        const FVector3f N=Normals->GetElement(I);
        Normals->SetElement(I,FVector3f(N.X-N.Z*GX,N.Y-N.Z*GY,N.Z).GetSafeNormal());
    }
}

void AddMeshPaths(TArray<FSoftObjectPath>& Paths)
{
    for (const auto& Path : Stones) Paths.AddUnique(Path);
}

void GatherStrip(const ATemperateHillsWorld& Hills, const FBox& Bounds, TArray<FTemperatePlacement>& Out)
{
    const auto& Village=Hills.GetVillageSite();
    const FVector Center=Bounds.GetCenter(), Extent=Bounds.GetExtent();
    if (!Near(Village,Center.X,Center.Y,Extent.X,Extent.Y)) return;
    const FVector2D C=Village.Local(Center.X,Center.Y);
    const double RX=FMath::Abs(Village.Axis.X)*Extent.X+FMath::Abs(Village.Axis.Y)*Extent.Y;
    const double RY=FMath::Abs(Village.Axis.Y)*Extent.X+FMath::Abs(Village.Axis.X)*Extent.Y;
    if (FMath::Abs(C.X)>HalfX+RX || FMath::Abs(C.Y)>HalfY+RY) return;
    const auto Points=MakeArrayView(Gravel);
    const int32 First=Algo::LowerBoundBy(Points,C.Y-RY-0.01,&FGravel::Y);
    FBox Boxes[UE_ARRAY_COUNT(Stones)];
    bool Known[UE_ARRAY_COUNT(Stones)]={};
    const double Half=Hills.SizeMeters*50.;
    for (int32 I=First; I<Points.Num() && Points[I].Y<=C.Y+RY+.01; ++I)
    {
        const FGravel& G=Points[I];
        if (FMath::Abs(G.X-C.X)>RX+.01) continue;
        const FVector2D P=Village.World(G.X,G.Y);
        if (P.X<Bounds.Min.X || P.X>=Bounds.Max.X || P.Y<Bounds.Min.Y || P.Y>=Bounds.Max.Y) continue;
        const uint8 K=G.Variant;
        if (!Known[K])
        {
            const auto* Mesh=Cast<UStaticMesh>(Stones[K].ResolveObject());
            if (!Mesh) continue;
            Boxes[K]=Mesh->GetBoundingBox();
            Known[K]=true;
        }
        const FBox& Box=Boxes[K];
        const FVector Span=Box.GetSize();
        const uint32 ShapeKey=TemperateHillsSurface::Key(G.X,G.Y,11817,581);
        const double XY=G.Diameter/FMath::Max(1.,FMath::Max(Span.X,Span.Y));
        const double Thickness=G.Diameter*FMath::Lerp(.27,.46,TemperateHillsSurface::Unit(ShapeKey+1));
        const double Width=FMath::Lerp(.74,1.,TemperateHillsSurface::Unit(ShapeKey+2));
        const FVector Scale(XY,XY*Width,Thickness/FMath::Max(1.,Span.Z));
        const FQuat Rotation(FVector::UpVector,FMath::Atan2(Village.Axis.Y,Village.Axis.X)+G.Yaw*(2.*UE_PI/256.));
        // Same SW-to-NE diagonal as the village's 1 m collision mesh. An
        // embedded lower quarter hides the rounded underside of a loose chip.
        constexpr double Step=100.;
        const double X0=FMath::FloorToDouble((P.X+Half)/Step)*Step-Half;
        const double Y0=FMath::FloorToDouble((P.Y+Half)/Step)*Step-Half;
        const double U=(P.X-X0)/Step,V=(P.Y-Y0)/Step;
        const double A=Hills.Height(X0,Y0), D=Hills.Height(X0+Step,Y0+Step);
        const double Ground=U>V ? (1.-U)*A+(U-V)*Hills.Height(X0+Step,Y0)+V*D :
                                   (1.-V)*A+(V-U)*Hills.Height(X0,Y0+Step)+U*D;
        const FVector Pivot=FVector(P,Ground-Thickness*.25)-
            Rotation.RotateVector(Scale*FVector(Box.GetCenter().X,Box.GetCenter().Y,Box.Min.Z));
        auto& Point=Out.Emplace_GetRef();
        Point.Transform=FTransform(Rotation,Pivot,Scale);
        Point.Mesh=Stones[K];
        Point.Key=TemperateHillsSurface::Key(G.X,G.Y,Hills.Seed,11817);
        Point.CandidateId=0x5647523100000000ULL+I;
    }
}
}
