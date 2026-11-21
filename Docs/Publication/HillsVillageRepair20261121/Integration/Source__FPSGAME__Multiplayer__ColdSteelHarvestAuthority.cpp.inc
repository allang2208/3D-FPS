// Source/FPSGAME/Multiplayer/ColdSteelHarvestAuthority.cpp
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 97-97 | bool UColdSteelSharedInventorySubsystem::WorldAction(UColdSteelStatusModel* M,AColdSteelPlayerState* Guest,const FColdSteelInventoryRequest& R,FString& Reason)
    TOptional<FVoxelBuildUndoHistory> UndoBefore;

// Lines 101-102 | bool UColdSteelSharedInventorySubsystem::WorldAction(UColdSteelStatusModel* M,AColdSteelPlayerState* Guest,const FColdSteelInventoryRequest& R,FString& Reason)
        if(Building->ApplyNetworkSnapshot(BuildingBefore)&&UndoBefore.IsSet())
            Building->UndoHistory=MoveTemp(UndoBefore.GetValue());

// Lines 111-111 | bool UColdSteelSharedInventorySubsystem::WorldAction(UColdSteelStatusModel* M,AColdSteelPlayerState* Guest,const FColdSteelInventoryRequest& R,FString& Reason)
                UndoBefore.Emplace(Building->UndoHistory);
