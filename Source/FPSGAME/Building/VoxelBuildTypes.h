#pragma once
#include "CoreMinimal.h"
#include "VoxelBuildTypes.generated.h"

// An invalid Volume identifies the original world-aligned voxel lattice.
USTRUCT()
struct FVoxelBuildKey
{
    GENERATED_BODY()
    UPROPERTY() FGuid Volume;
    UPROPERTY() FIntVector Cell=FIntVector::ZeroValue;
    bool operator==(const FVoxelBuildKey& Other) const {return Volume==Other.Volume&&Cell==Other.Cell;}
    friend uint32 GetTypeHash(const FVoxelBuildKey& Key){return HashCombine(GetTypeHash(Key.Volume),GetTypeHash(Key.Cell));}
};

USTRUCT()
struct FVoxelSavedCell
{
    GENERATED_BODY()
    UPROPERTY() FIntVector Position=FIntVector::ZeroValue;
    UPROPERTY() FName Material;
};

USTRUCT()
struct FVoxelFreeVolume
{
    GENERATED_BODY()
    UPROPERTY() FGuid Id;
    UPROPERTY() FVector Origin=FVector::ZeroVector;
    UPROPERTY() TMap<FIntVector,FName> Cells;
};

struct FVoxelEditCell
{
    FIntVector Position;
    FName Before;
    FName After;
    FGuid Volume;
};
