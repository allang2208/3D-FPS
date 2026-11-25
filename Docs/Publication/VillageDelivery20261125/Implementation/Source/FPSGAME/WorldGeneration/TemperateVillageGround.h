#pragma once

#include "CoreMinimal.h"
#include "UObject/SoftObjectPath.h"

struct FTemperateVillageSite;
struct FTemperatePlacement;
class ATemperateHillsWorld;
namespace UE::Geometry { class FDynamicMesh3; }

namespace TemperateVillageGround
{
double Offset(const FTemperateVillageSite& Village, double X, double Y);
void ShapeCell(const FTemperateVillageSite& Village, FVector2D Origin, double CellSize, UE::Geometry::FDynamicMesh3& Mesh);
void AddMeshPaths(TArray<FSoftObjectPath>& Paths);
void GatherStrip(const ATemperateHillsWorld& Hills, const FBox& Bounds, TArray<FTemperatePlacement>& Out);
}
