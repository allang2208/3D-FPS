#pragma once
#include "CoreMinimal.h"
#include "TemperateHillsRiver.h"
#include "TemperateHillsSurface.h"

// Small closed depressions. The bounded, seed-stable shallow basin layer is
// applied before player edits, without moving rivers or rewriting save records.
namespace TemperateForestWater
{
constexpr double Step = 100.;
struct FPool
{
    double WaterZ=0,AreaM2=0,MaxDepth=0;
    FBox2D Bounds=FBox2D(ForceInit);
    TSet<FIntPoint> Cells;
};
struct FSample { bool Wet=false; double WaterZ=0,Depth=0; };
struct FBasin { FVector2D Center; double Radius=0,WaterZ=0,Depth=0; };
struct FPlan
{
    FVector2D Origin=FVector2D::ZeroVector;
    int32 Width=0,Height=0;
    TArray<double> Ground;
    TArray<float> ShoreMoisture;
    // Regional plans retain only selected 64 m hydrology tiles. Pools use the
    // parent's world-grid coordinates so village exclusion and tools agree.
    TArray<TSharedPtr<const FPlan,ESPMode::ThreadSafe>> Patches;
    TArray<FPool> Pools;
    TArray<FBasin> Basins;
    double ShapeGround(double X,double Y,double Original) const;
    bool HasBasin(double X,double Y) const;
    double GroundAt(int32 X,int32 Y) const;
    FSample Sample(double X,double Y) const;
    void RebuildShoreMoisture();
    double ShoreMoistureAt(double X,double Y) const;
    bool IntersectsCell(double X,double Y,double Size) const;
    void BuildWaterMesh(double X,double Y,double Size,UE::Geometry::FDynamicMesh3& Mesh) const;
    bool IntersectSegment(const FVector& Start,const FVector& End,FVector& Position) const;
};
using FPlanPtr=TSharedPtr<const FPlan,ESPMode::ThreadSafe>;
// Flood an existing metre grid without reshaping authored terrain.
void FindClosedPools(FPlan& Tile,const TArray<uint8>& Allowed);
FPlanPtr Generate(int32 Seed,double Half,TemperateRiver::FPlanPtr River,
    const TArray<TemperateHillsSurface::FTerrainEdit>& Edits,int32 Version);
}
