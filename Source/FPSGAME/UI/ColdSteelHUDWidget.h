#pragma once

#include "CoreMinimal.h"
#include "CommonActivatableWidget.h"
#include "ColdSteelHUDWidget.generated.h"

class UBorder;
class UBackgroundBlur;
class UButton;
class UCanvasPanel;
class UCanvasPanelSlot;
class UHorizontalBox;
class UImage;
class UProgressBar;
class USizeBox;
class UScrollBox;
class UTextBlock;
class UTexture2D;
class UVerticalBox;
class UWidget;
class UColdSteelDetailRow;
class UColdSteelStatusModel;

UCLASS()
class FPSGAME_API UColdSteelHUDWidget : public UCommonActivatableWidget
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = "Cold Steel UI")
    void ToggleInventory();
    bool HandlePanelShortcut(const FKey& Key, bool bRepeat = false);

    UFUNCTION(BlueprintPure, Category = "Cold Steel UI")
    bool IsInventoryOpen() const { return bInventoryOpen; }

    /** Deterministic compact / expanded / detail states used by the runtime UI audit. */
    void SetEventTimelineAuditState(int32 State);

    /** Deterministic status / equipment-card states used by the runtime UI audit. */
    void SetInventoryAuditState(int32 State);
    void RunUpgradeAudit();
    void RunInventoryAudit();
    void RunInventoryDragAudit();
    void RunItemTooltipAudit();
    void RunTopVitalsAudit();
    void ShowItemTooltip(const FString& Id,FVector2D ScreenAnchor,bool Pinned=false,UWidget* Source=nullptr);
    void HideItemTooltip(bool Force=false);
    bool HasPinnedItemTooltip()const;
    void FocusItemTooltip();
    void OpenStatus();
    void OpenWarehouse(class AColdSteelWarehouseChest* Chest);
    void CloseWarehouse();
    bool IsWarehouseOpen() const { return bWarehouseOpen; }
    void RunWarehouseAudit();
    void ShowWarehouseDetails(UWidget* Details);
    UFUNCTION() void HideWarehouseDetails();

protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;
    virtual FReply NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&) override;
    virtual UWidget* NativeGetDesiredFocusTarget() const override;

private:
    UPROPERTY() TObjectPtr<class UColdSteelItemTooltip> ItemTooltip;
    void BuildInterface();
    void BuildWarehouse(UCanvasPanel* Root);
    void TickWarehouse(const FGeometry& Geometry,float Delta);
    UPROPERTY() TObjectPtr<class UColdSteelWarehouseWidget> WarehouseWidget;
    UPROPERTY() TObjectPtr<UCanvasPanelSlot> WarehouseSlot;
    UPROPERTY() TObjectPtr<UBorder> WarehouseDetails;
    TWeakObjectPtr<class AColdSteelWarehouseChest> WarehouseChest;
    bool bWarehouseOpen=false;
    float WarehouseMotion=0,WarehouseStart=0,WarehouseElapsed=.3f;
    void BuildHotbar(UCanvasPanel* Root);
    void BuildAmmoReadout(UCanvasPanel* Root);
    void BuildInventory(UCanvasPanel* Root);
    UWidget* BuildStatusPage();
    UWidget* BuildEquipmentPage();
    void BuildStatusTooltip(UCanvasPanel* Root);
    void BuildEquipmentTooltip(UCanvasPanel* Root);
    void BuildEventTimeline(UCanvasPanel* Root);
    void SetInventoryOpen(bool bOpen);
    void SetInventoryTab(bool bStatusTab);
    void RefreshAmmo();
    void RefreshStatus();
    void RefreshCharacterSheet();
    void UpdateStatusTooltipPlacement();
    void BuildCharacterSummary(UCanvasPanel* Root);
    void BuildTopVitals(UCanvasPanel* Root);
    void RefreshTopVitals();
    UPROPERTY(Transient) TObjectPtr<UBorder> TopVitalsSurface;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> TopHealthValue;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> TopManaValue;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> TopLevelValue;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelResourceMeter> TopHealthMeter;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelResourceMeter> TopManaMeter;
    UColdSteelDetailRow* AddCharacterRow(UVerticalBox* Parent, const FString& Label, const FString& Key, const FString& Detail);
    UVerticalBox* AddCharacterCard(UVerticalBox* Parent, const FString& Title);
    void SetCharacterValue(const FString& Key, const FString& Value, bool bAvailable = true);
    void ShowStatusTooltip(const FString& Key);
    void HideStatusTooltip();
    void ShowEquipmentTooltip();
    void HideEquipmentTooltip();
    void UpdateEquipmentTooltipPlacement();
    UTextBlock* AddTooltipRow(UVerticalBox* Parent, const FString& Label, const FString& Value, const FLinearColor& ValueColor, bool bNumericValue = false);
    void AddTooltipSection(UVerticalBox* Parent, const FString& Title);
    void RefreshEventTimeline(bool bForce = false);
    void ApplyEventTimelineAuditFixture();
    void UpdateEventTimelineLayout();
    void UpdateEventTimelineFilterButtons();
    void RebuildEventDetails();
    void SetEventTimelineCompact(bool bCompact);

    UTextBlock* MakeText(const FString& Text, int32 Size, const FLinearColor& Color, bool bNumeric = false, bool bBold = false);
    UTextBlock* MakeReferenceText(const FString& Text, float PixelSize, const FLinearColor& Color, bool bNumeric = false, bool bBold = false);
    float ReferenceUnits(float PixelSize) const;
    UBorder* MakeSurface(const FLinearColor& Fill, float Radius, const FLinearColor& Outline, float OutlineWidth = 1.0f);
    UBorder* MakeHotbarSlot(const FString& KeyHint, const FString& Caption);
    UBorder* MakeEquipmentSlot(const FString& Caption, bool bEquipped = false);
    UBorder* MakeTab(const FString& Caption, bool bActive);
    UWidget* MakeAttributeRow(const FString& Label, const FString& Key, UTextBlock*& OutValue);
    UWidget* MakeInventoryGrid();
    UTexture2D* LoadUiTexture(const FString& Filename);

    UFUNCTION()
    void HandleCloseClicked();

    UFUNCTION() void HandleStatusTabClicked();
    UFUNCTION() void HandleEquipmentTabClicked();
    UFUNCTION() void HandleStrengthHovered();
    UFUNCTION() void HandleDexterityHovered();
    UFUNCTION() void HandleIntelligenceHovered();
    UFUNCTION() void HandleConstitutionHovered();
    UFUNCTION() void HandleWisdomHovered();
    UFUNCTION() void HandleLuckHovered();
    UFUNCTION() void HandleAttributeUnhovered();
    UFUNCTION() void HandleEquipmentHovered();
    UFUNCTION() void HandleEquipmentUnhovered();
    UFUNCTION() void HandleEquipmentClicked();
    UFUNCTION() void HandleEquipmentTooltipCloseClicked();

    UFUNCTION()
    void HandleTimelineToggleClicked();

    UFUNCTION()
    void HandleTimelineMarkerClicked();

    UFUNCTION()
    void HandleTimelineDetailsCloseClicked();

    UFUNCTION()
    void HandleTimelineFilterAllClicked();

    UFUNCTION()
    void HandleTimelineFilterWeatherClicked();

    UPROPERTY(Transient)
    TObjectPtr<UBorder> InventoryBackdrop;

    UPROPERTY(Transient)
    TObjectPtr<UBackgroundBlur> InventoryBlur;

    UPROPERTY(Transient)
    TObjectPtr<UBorder> InventoryPanel;

    UPROPERTY(Transient)
    TObjectPtr<UButton> CloseButton;
    UPROPERTY(Transient) TObjectPtr<UButton> EquippedItemButton;

    UPROPERTY(Transient)
    TObjectPtr<class UColdSteelAmmoReadout> AmmoReadout;

    UPROPERTY(Transient)
    TObjectPtr<UTextBlock> InventorySummaryText;

    UPROPERTY(Transient) TObjectPtr<UWidget> StatusPage;
    UPROPERTY(Transient) TObjectPtr<UScrollBox> StatusScroll;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> StatusModel;
    UPROPERTY(Transient) TMap<FString, TObjectPtr<UColdSteelDetailRow>> CharacterRows;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> CharacterNameText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> CharacterClassText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> CharacterLevelText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> AttributePointsText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> CharacterSummaryText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> WeaponNameText;
    TMap<FString, FString> CharacterDetails;
    TMap<FString, FString> CharacterTitles;
    FString ActiveStatusKey;
    FString StatusDetailSignature;
    FDelegateHandle StatusModelHandle;
    UPROPERTY(Transient) TObjectPtr<UWidget> EquipmentPage;
    UPROPERTY(Transient) TObjectPtr<UBorder> StatusTabSurface;
    UPROPERTY(Transient) TObjectPtr<UBorder> EquipmentTabSurface;
    UPROPERTY(Transient) TObjectPtr<UBorder> StatusTabUnderline;
    UPROPERTY(Transient) TObjectPtr<UBorder> EquipmentTabUnderline;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StatusTabText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EquipmentTabText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> InventoryTitleText;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> HealthBar;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> ManaBar;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> ExperienceBar;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> HotbarCounts;
    UPROPERTY(Transient) TArray<TObjectPtr<UImage>> HotbarImages;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> HealthValueText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> MoveSpeedValueText;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> AmmoStatusValueText;
    UPROPERTY(Transient) TObjectPtr<UBorder> StatusTooltip;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> StatusTooltipCanvasSlot;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StatusTooltipTitle;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StatusTooltipDescription;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StatusTooltipNote;
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> StatusTooltipRowsBox;
    UPROPERTY(Transient) TObjectPtr<UBorder> EquipmentTooltip;
    UPROPERTY(Transient) TObjectPtr<UScrollBox> EquipmentTooltipScroll;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> EquipmentTooltipCanvasSlot;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EquipmentDamageValue;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EquipmentCapacityValue;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EquipmentIntervalValue;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EquipmentReloadValue;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EquipmentAmmoValue;

    UPROPERTY(Transient)
    TObjectPtr<USizeBox> TimelineWidthBox;

    UPROPERTY(Transient)
    TObjectPtr<UBorder> TimelinePanel;

    UPROPERTY(Transient)
    TObjectPtr<UVerticalBox> TimelineExpandedContent;

    UPROPERTY(Transient)
    TObjectPtr<USizeBox> TimelineTrackSize;

    UPROPERTY(Transient)
    TObjectPtr<UCanvasPanel> TimelineTrack;

    UPROPERTY(Transient)
    TObjectPtr<UImage> TimelineGradient;

    UPROPERTY(Transient)
    TObjectPtr<UBorder> TimelineCursorLine;

    UPROPERTY(Transient)
    TObjectPtr<UBorder> TimelineEventLine;

    UPROPERTY(Transient)
    TObjectPtr<UButton> TimelineMarkerButton;

    UPROPERTY(Transient)
    TObjectPtr<UImage> TimelineMarkerImage;

    UPROPERTY(Transient)
    TObjectPtr<UTextBlock> TimelineMarkerTimeText;

    UPROPERTY(Transient)
    TObjectPtr<UTextBlock> TimelineNowText;

    UPROPERTY(Transient)
    TObjectPtr<UTextBlock> TimelineWindowText;

    UPROPERTY(Transient)
    TObjectPtr<UTextBlock> TimelineAllFilterText;

    UPROPERTY(Transient)
    TObjectPtr<UTextBlock> TimelineWeatherFilterText;

    UPROPERTY(Transient)
    TObjectPtr<UButton> TimelineAllFilterButton;

    UPROPERTY(Transient)
    TObjectPtr<UButton> TimelineWeatherFilterButton;

    UPROPERTY(Transient)
    TObjectPtr<UTextBlock> TimelineInvasionText;

    UPROPERTY(Transient)
    TObjectPtr<UButton> TimelineToggleButton;

    UPROPERTY(Transient)
    TObjectPtr<UBorder> TimelinePopover;

    UPROPERTY(Transient)
    TObjectPtr<UTextBlock> TimelinePopoverTitle;

    UPROPERTY(Transient)
    TObjectPtr<UVerticalBox> TimelineDetailContent;

    UPROPERTY(Transient)
    TObjectPtr<UTexture2D> TimelineGradientTexture;

    bool bInventoryOpen = false;
    float DrawerProgress = 0.0f;
    float AmmoRefreshAccumulator = 0.0f;
    float StatusRefreshAccumulator = 0.0f;
    bool bStatusTabActive = false;
    bool bEquipmentTooltipPinned = false;
    float TimelineRefreshAccumulator = 0.0f;
    float TimelinePulse = 0.0f;
    float TimelineEventFraction = 0.04f;
    float TimelineEventStart = 0.0f;
    float TimelineEventEnd = 0.0f;
    float TimelineDaySeconds = 1440.0f;
    float TimelineLastDayFraction = -1.0f;
    int32 TimelineDaySerial = 0;
    bool bTimelineCompact = true;
    bool bTimelineHasEvent = false;
    bool bTimelineEventActive = false;
    bool bTimelineManual = false;
    bool bTimelineContainsStorm = false;
    bool bTimelineWeatherFilter = false;
    FString TimelineEventLabel;
    FString TimelineIntensityLabel;
    FString TimelineStartLabel;
    FString TimelineEndLabel;
    FString TimelineDurationLabel;
    FString TimelineWarningLabel;
    FString TimelineDetailSignature;
    TArray<int32> TimelineStageStates;
    TArray<float> TimelineStageStarts;
    TArray<float> TimelineStageEnds;
    int32 WidgetSerial = 0;

    UPROPERTY(Transient)
    TArray<TObjectPtr<UTexture2D>> LoadedTextures;

    UPROPERTY(Transient)
    TMap<FString, TObjectPtr<UTexture2D>> LoadedTextureCache;
};
