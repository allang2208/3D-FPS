#pragma once
#include "CoreMinimal.h"
#include "VoxelBuildTypes.h"
#include "DynamicMesh/DynamicMesh3.h"
#include "PhysicsEngine/AggregateGeom.h"

struct FVoxelGeometry
{
    UE::Geometry::FDynamicMesh3 Mesh;
    FKAggregateGeom Collision;
    float MassKg=0;
    FVector MassCenter=FVector::ZeroVector;
};

struct FVoxelChunkSnapshot
{
    FIntVector Origin;
    FVector Offset;
    TMap<FIntVector,int32> Slots;
};

namespace VoxelGeometry
{
    // All inputs are owned snapshots; no UObject or mutable world reads.
    TSharedPtr<FVoxelGeometry> Chunk(FIntVector Origin,TMap<FIntVector,int32> Slots,double Radius);
    TSharedPtr<FVoxelGeometry> Batch(TArray<FVoxelChunkSnapshot> Chunks,double Radius);
    TSharedPtr<FVoxelGeometry> Fragment(const TArray<FVoxelDebrisCell>& Cells,
        const TMap<FName,int32>& Slots,const TMap<FName,float>& Densities,double Radius);
    TArray<FVoxelFragmentSave> Split(const FVoxelFragmentSave& Source,
        const TSet<FVoxelBrokenBond>& Broken,int32 MaxShapes=64);
}
