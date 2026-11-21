// Source/FPSGAME/Building/VoxelBuildWidget.h
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 80-80 | class FPSGAME_API UVoxelBuildWidget : public UUserWidget
    void SetVillageConstructionUnlocked(bool bUnlocked);

// Lines 123-123 | class FPSGAME_API UVoxelBuildWidget : public UUserWidget
    UPROPERTY() TObjectPtr<class UHorizontalBox> HeaderHints;

// Lines 133-133 | class FPSGAME_API UVoxelBuildWidget : public UUserWidget
    UPROPERTY() TObjectPtr<UButton> VillageTab;

// Lines 151-151 | class FPSGAME_API UVoxelBuildWidget : public UUserWidget
    TWeakObjectPtr<UTextBlock> MaterialTabLabel,ComponentTabLabel,VillageTabLabel;

// Lines 164-164 | class FPSGAME_API UVoxelBuildWidget : public UUserWidget
    enum class ECategory : uint8 { Materials, Other, Village };

// Lines 166-166 | class FPSGAME_API UVoxelBuildWidget : public UUserWidget
    bool bVillageConstructionUnlocked=false;

// Lines 197-197 | class FPSGAME_API UVoxelBuildWidget : public UUserWidget
    UFUNCTION() void ShowVillageCategory();
