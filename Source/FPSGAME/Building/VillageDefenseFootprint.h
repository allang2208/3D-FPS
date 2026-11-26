#pragma once

#include "CoreMinimal.h"

class UStaticMesh;
class UPrimitiveComponent;
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
    const FShape& Siege(FName Recipe);
    /** Ground-level footprint at the native pivot, excluding the moving assembly. */
    FBox2D SiegeBase(FName Recipe);
    /** Top walking slabs in mesh space, including the gaps around the stair opening. */
    const FShape* SiegeRoof(const UPrimitiveComponent* Surface);
    bool RoofOpening(const FShape& Deck,FBox2D& Opening);
    bool TrebuchetFitsDeck(const FShape& Deck,const FTransform& Frame,const FTransform& Pose);
    void Rasterize(const FShape& Shape,const FTransform& Pose,TArray<FIntVector>& Cells);
    /** Rotate the basic wall/gate's original closed placement envelope, measured in world-grid cells. */
    void RasterizeGridEnvelope(FIntVector Footprint,const FTransform& Pose,TArray<FIntVector>& Cells);
    bool IsClear(UWorld& World,const FShape& Shape,const FTransform& Pose,const AActor* Builder,TConstArrayView<AActor*> Replaced={},double GroundAllowance=20.01);
}
