#pragma once

#include "CoreMinimal.h"

class UStaticMesh;
class UWorld;

/** Local boxes are the same authored walk/collision hulls as the installed mesh. */
namespace VillageDefenseFootprint
{
    struct FShape
    {
        TArray<FBox> Boxes;
        FBox Bounds{ForceInit};
    };

    const FShape& Get(FName Id, UStaticMesh* Mesh);
    void Rasterize(const FShape& Shape,const FTransform& Pose,TArray<FIntVector>& Cells);
    /** Rotate the basic wall/gate's original closed placement envelope, measured in world-grid cells. */
    void RasterizeGridEnvelope(FIntVector Footprint,const FTransform& Pose,TArray<FIntVector>& Cells);
    bool IsClear(UWorld& World,const FShape& Shape,const FTransform& Pose,const AActor* Builder);
}
