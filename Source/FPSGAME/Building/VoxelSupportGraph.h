#pragma once
#include "CoreMinimal.h"
#include "VoxelBuildTypes.h"
#include "VoxelBuildPalette.h"

struct FVoxelSupportNode
{
    FVoxelBuildKey Key;
    FVector Min;
    bool bAnchor=false;
    bool bBearing=true;
    FName Material;
    FVoxelPhysicalMaterial Physics;
    float Damage=0;
    float AddedMassKg=0;
};

struct FVoxelContact
{
    FVector Center,Normal;
    double Area=0,Width=0,Height=0; // SI units; center remains UE cm.
};

/** Incremental world-space face graph, including independently translated grids. */
struct FVoxelSupportGraph
{
    TMap<FVoxelBuildKey,FVoxelSupportNode> Nodes;
    TMap<FVoxelBuildKey,TSet<FVoxelBuildKey>> Edges;
    TSet<FVoxelBuildKey> Supported;
    TSet<FVoxelBrokenBond> Broken;
    void Add(const FVoxelSupportNode& Node);
    void Remove(FVoxelBuildKey Key);
    void Break(FVoxelBrokenBond Bond);
    void SolveConnectivity();
    bool Overlaps(const FVector& Min) const;
    TArray<FVoxelBuildKey> Near(const FVector& Min) const;
    TArray<FVoxelBuildKey> Within(FVector Point,float Radius) const;
    static bool Contact(const FVector& A,const FVector& B,FVoxelContact& Result);
private:
    TMap<FIntVector,TSet<FVoxelBuildKey>> Buckets;
};

struct FVoxelStressInput
{
    TArray<FVoxelSupportNode> Nodes;
    TSet<FVoxelBrokenBond> Broken;
    uint64 Revision=0;
    int32 Iterations=256;
    float GravityMS2=-9.81f;
};

struct FVoxelStressResult
{
    uint64 Revision=0;
    TSet<FVoxelBuildKey> Evaluated,Supported;
    TArray<FVoxelBrokenBond> Broken;
    TArray<FVoxelBuildKey> Crushed;
    TArray<TArray<FVoxelSupportNode>> Detached;
    TMap<FVoxelBuildKey,float> LoadRatios;
    bool bConverged=true;
    int32 Iterations=256;
};
namespace VoxelStress { FVoxelStressResult Solve(FVoxelStressInput Input); }
