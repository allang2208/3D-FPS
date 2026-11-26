#pragma once
#include "VoxelBuildTypes.h"

class APlayerState;

// Session-only undo. Immutable voxel batches let a shared-inventory transaction
// checkpoint the histories without copying every player's individual cells.
struct FVoxelBuildUndoEntry
{
    TSharedPtr<const TArray<FVoxelEditCell>> Blocks;
    FGuid PrefabInstance;
    FIntVector Anchor=FIntVector::ZeroValue;
};

struct FVoxelBuildUndoHistory
{
    using FStack=TArray<FVoxelBuildUndoEntry>;
    FStack& For(APlayerState* Player);
    void Remember(APlayerState* Player,FVoxelBuildUndoEntry Entry);
    void InvalidateCells(const TArray<FVoxelEditCell>& Edits);
    void ClearVoxelBatches(APlayerState* Player);
    void ForgetDisconnected();
private:
    FStack Local;
    TMap<TWeakObjectPtr<APlayerState>,FStack> Players;
};
