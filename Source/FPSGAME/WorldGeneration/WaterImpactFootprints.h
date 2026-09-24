#pragma once
#include "CoreMinimal.h"

class UStaticMesh;
struct FWaterImpactPatch
{
    double Z=0;
    TArray<FVector2D> Polygon;
    FBox2D Bounds=FBox2D(ForceInit);
};
struct FWaterImpactFootprint
{
    FString MeshPath;
    float StrengthScale=1.f;
    TArray<FWaterImpactPatch> Patches;
};
// Baked from saved source LOD0; no runtime mesh readback or CPU mesh residency.
const FWaterImpactFootprint* FindWaterImpactFootprint(const UStaticMesh* Mesh);
