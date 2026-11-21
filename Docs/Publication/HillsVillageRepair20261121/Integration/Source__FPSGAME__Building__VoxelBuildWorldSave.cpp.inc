// Source/FPSGAME/Building/VoxelBuildWorldSave.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 100-100 | void AVoxelBuildWorld::TickPersistence(bool bFlush)
        else if(!Runtime->bSaveDirty)ForgetSavedDefenseRemovals();

// Lines 105-109 | void AVoxelBuildWorld::TickPersistence(bool bFlush)
        if(Runtime->bSaveFailed)
        {
            UE_LOG(LogTemp,Error,TEXT("Voxel structure save failed at world shutdown: %s"),*SaveSlot);
        }
        else ForgetSavedDefenseRemovals();
