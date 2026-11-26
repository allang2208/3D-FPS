#pragma once
#include "CoreMinimal.h"

class UStaticMesh;

/** Shared ore shape/size contract for seeded hills and F6 test spawns. */
namespace ProductionOreRocks
{
    inline constexpr int32 ShapeCount=4;
    int32 Shape(uint32 Seed);
    FSoftObjectPath Mesh(const FString& Definition,int32 Shape);
    const TArray<FSoftObjectPath>& AllMeshes();
    FTransform Placement(const UStaticMesh& Mesh,uint32 Seed,const FVector& Ground,
        const FVector& Normal,bool River=false);
    /** Fit nine bottom-footprint samples to valid ground; retain the candidate XY.
     * Sample returns false for roads, water, voids or a different support surface. */
    bool FitToSurface(const UStaticMesh& Mesh,FTransform& Placement,
        TFunctionRef<bool(const FVector&,double&)> Sample,double BurialCm,double MaxReliefCm);
}
