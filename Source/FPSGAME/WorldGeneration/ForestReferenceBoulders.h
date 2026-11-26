#pragma once
#include "CoreMinimal.h"

#if WITH_EDITOR
class AForestVillageRegion;
class UStaticMesh;

namespace ForestReferenceBoulders
{
bool IsReferenceMesh(const UStaticMesh* Mesh);
bool Place(const AForestVillageRegion& Region,TArray<UStaticMesh*>& Meshes,
           TArray<TArray<FTransform>>& Hills,TArray<TArray<FTransform>>& Road);
}
#endif
