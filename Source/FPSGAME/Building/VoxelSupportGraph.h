#pragma once
#include "CoreMinimal.h"
#include "VoxelBuildTypes.h"

struct FVoxelSupportNode
{
    FVoxelBuildKey Key;
    FVector Min;
    bool bAnchor=false;
    bool bBearing=true;
};

struct FVoxelSupportEdge
{
    int32 Target;
    float SpanCm;
};

/** Game support rules, not a mass/stress simulation. Both lattice and free cells use world-space contacts. */
struct FVoxelSupportGraph
{
    TArray<FVoxelSupportNode> Nodes;
    TArray<float> Cost;
    TMap<FVoxelBuildKey,int32> Indices;
    float MaxSpanCm=200;
    void Add(const FVoxelSupportNode& Node);
    void Solve();
    bool IsSupported(int32 Index) const;
    bool Overlaps(const FVector& Min) const;
private:
    TMap<FIntVector,TArray<int32>> Buckets;
    TArray<TArray<FVoxelSupportEdge>> Edges;
    TArray<int32> Near(const FVector& Min) const;
    static float ContactSpan(const FVector& From,const FVector& To);
};
