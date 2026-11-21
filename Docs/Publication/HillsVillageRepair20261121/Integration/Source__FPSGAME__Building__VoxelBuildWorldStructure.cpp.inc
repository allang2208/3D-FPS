// Source/FPSGAME/Building/VoxelBuildWorldStructure.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 55-55 | void AVoxelBuildWorld::ApplyOverloadDamage(const TArray<FVoxelOverloadCell>& Overload,double Seconds)
    if(!Removed.IsEmpty()){UndoHistory.ClearVoxelBatches(UndoPlayer);ApplyChanges(Removed);}

// Lines 129-129 | void AVoxelBuildWorld::TickStructure()
        {++Revision;UndoHistory.ClearVoxelBatches(UndoPlayer);MarkSaveDirty();Runtime->NextIterations=256;}

// Lines 147-147 | void AVoxelBuildWorld::TickStructure()
            EnqueueFragment(MoveTemp(State),MoveTemp(Keys),{},bProtecting);UndoHistory.ClearVoxelBatches(UndoPlayer);

// Lines 172-174 | void AVoxelBuildWorld::TickStructure()
            Runtime->bFreshRolledBack=true;UndoHistory.ClearVoxelBatches(UndoPlayer);
        }
        else if(!Crushed.IsEmpty()){UndoHistory.ClearVoxelBatches(UndoPlayer);ApplyChanges(Crushed);}
