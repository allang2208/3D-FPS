// Source/FPSGAME/Building/VoxelBuildWorld.h
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 7-7 | file scope
#include "VoxelBuildUndoHistory.h"

// Lines 139-140 | class FPSGAME_API AVoxelBuildWorld : public AActor
    void OnVillageSupportChanged(const class AVillageDefenseSection& Section);
    void RefreshReplicatedVillagePiece(AVoxelBuildPrefabActor& Piece);

// Lines 169-169 | class FPSGAME_API AVoxelBuildWorld : public AActor
    UFUNCTION(BlueprintCallable,Category="Building|Prefab") bool PlacePrefab(FName Id,FIntVector Cell,int32 Yaw=0,bool bDocked=false,AActor* DockTarget=nullptr,int32 GroundYawDegrees=-1);

// Lines 218-219 | class FPSGAME_API AVoxelBuildWorld : public AActor
    bool CanPlacePrefab(FName Id,FIntVector Cell,int32 Yaw,FString& Reason,bool bSurfaceBacked=false,bool bDocked=false,
        const AActor* DockTarget=nullptr,FTransform* OutPlacementPose=nullptr,int32 GroundYawDegrees=INDEX_NONE) const;

// Lines 239-240 | class FPSGAME_API AVoxelBuildWorld : public AActor
    bool CanBearLoadAt(FIntVector Anchor,FIntVector Cell) const;
    bool FindWallBacking(const FVoxelBuildPrefabInstance& Piece,FHitResult& Surface) const;

// Lines 277-278 | class FPSGAME_API AVoxelBuildWorld : public AActor
    FVoxelBuildUndoHistory UndoHistory;
    APlayerState* UndoPlayer=nullptr; // Scoped only while handling a server build request.

// Lines 297-300 | class FPSGAME_API AVoxelBuildWorld : public AActor
    mutable TWeakObjectPtr<ATemperateHillsWorld> VillageConstructionWorld;
    ATemperateHillsWorld* FindVillageConstructionWorld() const;
    TSet<FGuid> RemovedVillageDefenses;
    void ForgetSavedDefenseRemovals();
