#pragma once
#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "VoxelSurfaceMesher.generated.h"

class UDynamicMesh;
namespace UE::Geometry { class FDynamicMesh3; }

namespace VoxelSurface
{
    // SampleSlot reads the complete world, including the one-cell chunk halo.
    void Build(UE::Geometry::FDynamicMesh3& Mesh,FIntVector Origin,int32 Side,double Radius,
        TFunctionRef<int32(FIntVector)> SampleSlot);
}

/** Asset authoring uses the same surface generator as placed buildings. */
UCLASS()
class FPSGAME_API UVoxelSurfaceLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()
public:
    UFUNCTION(BlueprintCallable,Category="Building|Authoring")
    static UDynamicMesh* CreateExampleMesh(float EdgeRadiusCm=1.4f);
};
