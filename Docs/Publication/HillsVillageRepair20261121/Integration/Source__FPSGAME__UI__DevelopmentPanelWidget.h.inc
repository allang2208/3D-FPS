// Source/FPSGAME/UI/DevelopmentPanelWidget.h
// Merge each excerpt at the named target and scope. Line numbers locate the 2026-11-21 production source.

// Lines 117-117 | class FPSGAME_API UDevelopmentPanelWidget : public UWeatherControlWidget
    UFUNCTION() void ResetVillageUpgradesClicked();

// Lines 145-145 | class FPSGAME_API UDevelopmentPanelWidget : public UWeatherControlWidget
    UPROPERTY(Transient) TObjectPtr<UTextBlock> VillageResetHelp;

// Lines 192-192 | class FPSGAME_API UDevelopmentPanelWidget : public UWeatherControlWidget
    UPROPERTY(Transient) TObjectPtr<UButton> ResetVillageButton;
