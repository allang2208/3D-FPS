#pragma once

#include "CoreMinimal.h"

class UStaticMesh;
struct FTemperateChapelSite;

namespace ChapelCourtyardDressing
{
    void AddMeshPaths(TArray<FSoftObjectPath>& Paths);
    void ResolveMeshes(TMap<FName,UStaticMesh*>& Meshes);
    bool IsDetail(FName Role);
    using FPlaceOnSoil = TFunctionRef<void(FName,FVector2D,double,double,double,double)>;
    void Place(const FTemperateChapelSite& Chapel, int32 Seed, FPlaceOnSoil PlaceOnSoil);
}
