#pragma once

#include "CoreMinimal.h"

namespace UE::Geometry { class FDynamicMesh3; }

/** Immutable numerical river data shared by terrain workers and PCG sampling.
 * Units are centimetres. No UObject, physics queries or editor dependencies.
 */
namespace TemperateRiver
{
struct FPoint
{
    FVector2D XY = FVector2D::ZeroVector;
    FVector2D Side = FVector2D(0, 1);
    double WaterZ = 0;
    double HalfWidth = 450;
    double Depth = 65;
    double Distance = 0;
};

struct FSample
{
    double Distance = DBL_MAX;
    double WaterZ = 0;
    double HalfWidth = 0;
    double Depth = 0;
    double Along = 0;
    double Bank = 0;
    double Wet = 0;
};

struct FPlan
{
    TArray<FPoint> Points;
    TMap<FIntPoint, TArray<int32>> Buckets;
    FSample Sample(double X, double Y) const;
    double Height(double X, double Y, int32 Seed) const;
    FVector Normal(double X, double Y, int32 Seed) const;
    bool IntersectsCell(double X, double Y, double Size) const;
    void BuildWaterMesh(double X, double Y, double Size, UE::Geometry::FDynamicMesh3& Mesh) const;
};

using FPlanPtr = TSharedPtr<const FPlan, ESPMode::ThreadSafe>;
FPlanPtr Generate(int32 Seed, double HalfSize, const FVector2D& ProtectedSpawn);
}
