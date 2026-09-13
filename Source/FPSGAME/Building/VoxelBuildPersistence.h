#pragma once
#include "CoreMinimal.h"
#include "VoxelBuildTypes.h"
class UVoxelBuildSave;

/** Plain payload, safe to encode and write on a worker. */
struct FVoxelDiskSnapshot
{
    int32 Version=3,CellSizeCm=20;
    FString WorldKey;
    TArray<FVoxelSavedCell> Cells;
    TArray<FVoxelFreeVolume> FreeVolumes;
    TMap<FVoxelBuildKey,float> Damage;
    TSet<FVoxelBrokenBond> BrokenBonds;
    TArray<FVoxelFragmentSave> Fragments;
    TSet<FVoxelBuildKey> LegacyProtected;
};
namespace VoxelPersistence
{
    UVoxelBuildSave* Load(const FString& Slot);
    FVoxelDiskSnapshot Take(UVoxelBuildSave* Source);
    bool Write(FString Slot,FVoxelDiskSnapshot Snapshot);
}
