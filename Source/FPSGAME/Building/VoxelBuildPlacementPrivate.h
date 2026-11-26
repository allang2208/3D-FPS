#pragma once
#include "CoreMinimal.h"
#include "InputCoreTypes.h"
namespace VoxelBuildPlacementPrivate
{
extern TArray<FHitResult> AimScratch;
extern int32 ClippedPlayerCells;
int32 NumberKeyIndex(const FKey& Key);
}
