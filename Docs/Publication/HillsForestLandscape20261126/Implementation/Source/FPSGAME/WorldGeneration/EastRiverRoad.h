#pragma once

#include "CoreMinimal.h"

struct FTemperateVillageSite;
struct FTemperatePlacement;
class ATemperateHillsWorld;
class UPCGComponent;
class UMaterialInterface;

namespace EastRiverRoad
{
struct FSample
{
    FVector2D Center = FVector2D::ZeroVector;
    double Distance = MAX_dbl;
    double Along = 0.;
    double Width = 0.;
    double Elevation = 0.;
    double GradeWeight = 0.;
    FVector2f Paint = FVector2f::ZeroVector;
};
bool Enabled(int32 Seed, int32 Version, const FTemperateVillageSite& Village);
bool TouchesCell(double X, double Y, double Size);
FSample Sample(double X, double Y);
double Height(const FSample& Sample, TFunctionRef<double()> Native);
bool Owns(double X,double Y);
void ForLegacyBounds(const ATemperateHillsWorld& World,const FBox& Bounds,TFunctionRef<void(const FBox&)> Generate);
using FTreeKeys=TArray<FIntPoint,TInlineAllocator<5>>;
FTreeKeys TreeKeys(const ATemperateHillsWorld& World,int32 X,int32 Y);
bool IsExtraTree(int32 X);
int32 CanopyForm(const FSoftObjectPath& Mesh);
TArray<FIntPoint> ForestTiles();
bool Tree(const ATemperateHillsWorld& World,int32 GX,int32 GY,FVector2D Original,FTemperatePlacement& Out);
void AddSurfacePaths(TArray<FSoftObjectPath>& Out);
void AddTreePaths(TArray<FSoftObjectPath>& Out);
bool TreesLoaded();
UMaterialInterface* Material();
void GatherFloor(const ATemperateHillsWorld& World, const FBox& Bounds, TArray<FTemperatePlacement>& Out);
void ScatterDecals(ATemperateHillsWorld& World, UPCGComponent& Owner, const FBox& Bounds);
}
