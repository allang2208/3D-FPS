// Source/FPSGAME/Building/VoxelBuildWorld.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 318-318 | bool AVoxelBuildWorld::Initialize(const FString& InWorldKey,UVoxelBuildPalette* InPalette)
        if(VillageBuildDefense::IsVillageRecipe(Piece.Id))SpawnPrefab(Piece);

// Lines 326-326 | bool AVoxelBuildWorld::Initialize(const FString& InWorldKey,UVoxelBuildPalette* InPalette)
        if(!VillageBuildDefense::IsVillageRecipe(Piece.Id))SpawnPrefab(Piece);

// Lines 604-606 | void AVoxelBuildWorld::ApplyChanges(const TArray<FVoxelEditCell>& Edit)
    // A removed/replaced cell is no longer the instance recorded in any player's undo batch.
    // Compare edit keys, not only materials: another player may rebuild the same material here.
    UndoHistory.InvalidateCells(Edit);

// Lines 662-663 | bool AVoxelBuildWorld::Commit(const TArray<FVoxelEditCell>& Edit,bool bRemember)
        if(bAnyRemoval)UndoHistory.For(UndoPlayer).Reset();
        else if(!Added.IsEmpty())UndoHistory.Remember(UndoPlayer,{MakeShared<TArray<FVoxelEditCell>>(MoveTemp(Added)),{},FIntVector::ZeroValue});
