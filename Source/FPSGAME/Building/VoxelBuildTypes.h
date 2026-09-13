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

USTRUCT()
struct FVoxelBrokenBond
{
    GENERATED_BODY()
    UPROPERTY() FVoxelBuildKey A;
    UPROPERTY() FVoxelBuildKey B;
    bool operator==(const FVoxelBrokenBond& O) const {return (A==O.A&&B==O.B)||(A==O.B&&B==O.A);}
    friend uint32 GetTypeHash(const FVoxelBrokenBond& B){return GetTypeHash(B.A)^GetTypeHash(B.B);}
};

USTRUCT()
struct FVoxelDebrisCell
{
    GENERATED_BODY()
    UPROPERTY() FVoxelBuildKey Key;
    UPROPERTY() FVector Min=FVector::ZeroVector;
    UPROPERTY() FName Material;
    UPROPERTY() float Damage=0;
};

USTRUCT()
struct FVoxelFragmentSave
{
    GENERATED_BODY()
    UPROPERTY() FGuid Id;
    UPROPERTY() FTransform Transform;
    UPROPERTY() TArray<FVoxelDebrisCell> Cells;
    UPROPERTY() TSet<FVoxelBrokenBond> BrokenBonds;
    UPROPERTY() FVector Velocity=FVector::ZeroVector;
    UPROPERTY() FVector AngularVelocity=FVector::ZeroVector;
    UPROPERTY() bool bSleeping=false;
};
