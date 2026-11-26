#pragma once
#include "CoreMinimal.h"

#if WITH_EDITOR
class AForestVillageRegion;
class UInstancedStaticMeshComponent;
class UStaticMesh;
class UMaterialInterface;

namespace ForestCourtyardShrubs
{
const TCHAR* LeafOverride(const UStaticMesh* Mesh);
bool Place(const AForestVillageRegion& Region, const TArray<UInstancedStaticMeshComponent*>& Study,
    TConstArrayView<uint8> CliffMask, const TMap<FIntPoint,FVector4f>& HarvestTrees,
    TArray<UStaticMesh*>& Meshes,TArray<TArray<FTransform>>& Hills,TArray<TArray<FTransform>>& Road);
}
#endif
