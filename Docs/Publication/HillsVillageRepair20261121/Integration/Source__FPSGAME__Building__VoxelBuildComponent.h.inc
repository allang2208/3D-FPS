// Source/FPSGAME/Building/VoxelBuildComponent.h
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 56-56 | class FPSGAME_API UVoxelBuildComponent : public UActorComponent
    friend class UTemperateVillageCheckCommandlet;

// Lines 64-65 | class FPSGAME_API UVoxelBuildComponent : public UActorComponent
    bool CanBuildVillagePieces() const;
    void RefreshVillageConstructionAccess();

// Lines 68-69 | class FPSGAME_API UVoxelBuildComponent : public UActorComponent
    UPROPERTY() TArray<TObjectPtr<UStaticMeshComponent>> VillageGatePreviewParts;
    FName PreviewGateAssembly;

// Lines 112-116 | class FPSGAME_API UVoxelBuildComponent : public UActorComponent
    // Quarter turns for lattice/socket addressing. Free castle pieces use a separate exact angle.
    int32 PrefabPlanYaw=0;
    TWeakObjectPtr<class AVillageDefenseSection> DefenseDockTarget;
    TOptional<FTransform> DefenseDockPose;
    int32 DefenseDockSocket=INDEX_NONE;

// Lines 143-144 | class FPSGAME_API UVoxelBuildComponent : public UActorComponent
    int32 GroundYawDegrees=0;
    int32 PlannedGroundYaw() const;

// Lines 185-185 | class FPSGAME_API UVoxelBuildComponent : public UActorComponent
    void RefreshPlacementInput();
