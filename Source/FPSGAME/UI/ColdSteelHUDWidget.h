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
class UOverlay;
class UColdSteelDetailRow;
class UColdSteelStatusModel;

UCLASS()
class FPSGAME_API UColdSteelHUDWidget : public UCommonActivatableWidget
{
    GENERATED_BODY()

public:
    UFUNCTION() void OpenAmmoPouch();
    void RequestAmmoChange(const FString& WeaponId,const FString& Target);
    UFUNCTION(BlueprintCallable, Category = "Cold Steel UI")
    void ToggleInventory();
    bool HandlePanelShortcut(const FKey& Key, bool bRepeat = false);
    bool HandleInventoryOutsideClick(FVector2D ScreenPosition);
    bool HandlePanelNavigationClick(FVector2D ScreenPosition);

    UFUNCTION(BlueprintPure, Category = "Cold Steel UI")
    bool IsInventoryOpen() const { return bInventoryOpen; }

    /** 开发面板等外部右侧抽屉与背包装备共享让位规则：打开期间入口列、世界时钟与武器详情一起收起。 */
    void SetExternalDrawerOpen(bool bOpen);
    bool IsExternalDrawerOpen() const { return bExternalDrawerOpen; }

    /** Deterministic compact / expanded / detail states used by the runtime UI audit. */
    void SetEventTimelineAuditState(int32 State);

    /** Deterministic status / equipment-card states used by the runtime UI audit. */
    void SetInventoryAuditState(int32 State);
    void RunUpgradeAudit();
    void RunInventoryAudit();
    void RunWeaponIconAudit();
    void RunInventoryVisualAudit();
    void RunSmeltingVisualAudit();
    void RunInventoryGlassAudit();
    void RunInventoryDragAudit();
    void RunDropHitchAudit();
    void BeginInventoryDrag(class UColdSteelItemDrag* Drag);
    void UpdateInventoryDrag(class UColdSteelItemDrag* Drag,FVector2D ScreenPosition);
    void EndInventoryDrag();
    class UColdSteelQuickDrag* StartQuickDrag(FName Skill,int32 From,const FSlateBrush* Icon,FVector2D Position);
    void UpdateQuickDrag(UColdSteelQuickDrag* Drag,FVector2D Position);
    bool DropQuickDrag(UColdSteelQuickDrag* Drag,int32 Target);
    bool DropInventoryOnQuickBar(UColdSteelItemDrag* Drag,int32 Target);
    void EndQuickDrag();
    void CancelQuickDrag();
    bool IsQuickDragging() const { return QuickDrag.IsValid(); }
    void RunItemTooltipAudit();
    void RunTopVitalsAudit();
    void ShowItemTooltip(const FString& Id,FVector2D ScreenAnchor,bool Pinned=false,UWidget* Source=nullptr);
    void HideItemTooltip(bool Force=false);
    bool HasPinnedItemTooltip()const;
    void FocusItemTooltip();
    void OpenStatus();
    UFUNCTION(BlueprintCallable,Category="Cold Steel UI") void OpenSkills();
    /** 图鉴：右侧抽屉第 4 页（武器／怪物档案），快捷键 K。 */
    UFUNCTION(BlueprintCallable,Category="Cold Steel UI") void OpenCodex();
    void OpenWarehouse(class AColdSteelWarehouseChest* Chest);
    void CloseWarehouse();
    bool IsWarehouseOpen() const { return bWarehouseOpen; }
    /** 冶炼高炉 E 交互：打开背包并把冶炼面板挂到背包左侧（同一开合生命周期）。
     *  参数是命中的占位构件 Actor（内部校验为 blast_furnace），无效时静默不响应。 */
    void OpenSmelting(AActor* Furnace);
    void CloseSmelting();
    bool IsSmeltingOpen() const { return bSmeltingOpen; }
    /** 工作台 E 交互：打开背包并把制作面板挂到背包左侧（格式大小复刻冶炼面板，
     *  Docs/UI/workbench-panel-plan-20260924.md）；与冶炼面板同贴位、互斥。 */
    void OpenWorkbench(AActor* Workbench);
    void CloseWorkbench();
    bool IsWorkbenchOpen() const { return bWorkbenchOpen; }
    void RunWarehouseAudit();
    void RunWarehouseGlassAudit();
    void ShowWarehouseDetails(UWidget* Details);
    UFUNCTION() void HideWarehouseDetails();

protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& MyGeometry, float InDeltaTime) override;
    virtual int32 NativePaint(const FPaintArgs&,const FGeometry&,const FSlateRect&,FSlateWindowElementList&,int32,const FWidgetStyle&,bool) const override;
    virtual FReply NativeOnKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry& InGeometry, const FKeyEvent& InKeyEvent) override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&) override;
    virtual FReply NativeOnPreviewMouseButtonDown(const FGeometry&,const FPointerEvent&) override;
    virtual bool NativeOnDragOver(const FGeometry&,const FDragDropEvent&,class UDragDropOperation*) override;
    virtual bool NativeOnDrop(const FGeometry&,const FDragDropEvent&,class UDragDropOperation*) override;
    virtual UWidget* NativeGetDesiredFocusTarget() const override;

private:
    friend struct FWeatherWorldAudit;
    UPROPERTY() TObjectPtr<class UColdSteelItemTooltip> ItemTooltip;
    void BuildInterface();
    void BuildPanelNavigation(UCanvasPanel* Root);
    void TickPanelNavigation(const FGeometry& Geometry,float Delta);
    void ActivatePanelNavigation(int32 Page);
    UFUNCTION() void HandleNavigationStatus();
    UFUNCTION() void HandleNavigationBackpack();
    UFUNCTION() void HandleNavigationSkills();
    UFUNCTION() void HandleNavigationCodex();
    UPROPERTY(Transient) TObjectPtr<UVerticalBox> PanelNavigation;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> PanelNavigationSlot;
    UPROPERTY(Transient) TArray<TObjectPtr<UButton>> PanelNavigationButtons;
    UPROPERTY(Transient) TArray<TObjectPtr<USizeBox>> PanelNavigationSizes;
    UPROPERTY(Transient) TArray<TObjectPtr<UImage>> PanelNavigationMarkers;
    UPROPERTY(Transient) TArray<TObjectPtr<UWidget>> PanelNavigationSubjects;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> PanelNavigationKeys;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> PanelNavigationFallbacks;
    UPROPERTY(Transient) TArray<TObjectPtr<UBorder>> PanelNavigationNames;
    float PanelNavigationElapsed=0.f,PanelNavigationScale=0.f;
    float PanelNavigationSize=0.f,PanelNavigationGap=0.f;
    struct FNavigationHover {float Value=0.f,From=0.f,Elapsed=.2f;bool Target=false;};
    TArray<FNavigationHover> PanelNavigationHover;
    TArray<uint8> PanelNavigationStates;
    void BuildWarehouse(UCanvasPanel* Root);
    void TickWarehouse(const FGeometry& Geometry,float Delta);
    UPROPERTY() TObjectPtr<class UColdSteelWarehouseWidget> WarehouseWidget;
    UPROPERTY() TObjectPtr<UCanvasPanelSlot> WarehouseSlot;
    UPROPERTY() TObjectPtr<UBorder> WarehouseDetails;
    TWeakObjectPtr<class AColdSteelWarehouseChest> WarehouseChest;
    bool bWarehouseOpen=false;
    float WarehouseMotion=0,WarehouseStart=0,WarehouseElapsed=.3f;
    // 冶炼面板：贴在背包抽屉左侧的半宽侧板（Docs/UI/smelting-panel-plan-20260923.md）。
    // 与抽屉共用同一条 DrawerProgress 滑入滑出；上下文（哪座炉子）在 E 交互时写入、关背包时清空。
    void BuildSmelting(UCanvasPanel* Root);
    UPROPERTY() TObjectPtr<class UColdSteelSmeltingWidget> SmeltingWidget;
    UPROPERTY() TObjectPtr<UCanvasPanelSlot> SmeltingSlot;
    TWeakObjectPtr<class AVoxelBuildWorld> SmeltingWorld;
    FIntVector SmeltingCell=FIntVector::ZeroValue;
    bool bSmeltingOpen=false;
    float SmeltWidth=0;
    float SmeltDock=0;   // 冶炼面板右缘到视口右缘的当前间距（背包开＝背包宽+12，关＝12），参与布局变化判定
    float SmeltMotion=0; // 冶炼面板滑入滑出进度（2026-09-24 用户要求与背包同动画：从左到右弹出，速率同 DrawerProgress）
    bool bSmeltRiding=false;   // 关闭相位：冶炼栏与背包刚体骑乘、同曲线整体向右缩回（2026-09-24 用户定稿）
    float SmeltSlidePx=0;      // 面板滑距＝面板宽+24（开着时记忆；关闭瞬间布局会把 SmeltWidth 清零）
    // 工作台制作面板：与冶炼面板同贴位（背包抽屉左侧半宽侧板）、同动画、互斥
    //（Docs/UI/workbench-panel-plan-20260924.md，成员命名逐一对应冶炼侧，方便对照审查）。
    void BuildWorkbench(UCanvasPanel* Root);
    UPROPERTY() TObjectPtr<class UColdSteelWorkbenchWidget> WorkbenchWidget;
    UPROPERTY() TObjectPtr<UCanvasPanelSlot> WorkbenchSlot;
    TWeakObjectPtr<class AVoxelBuildWorld> WorkbenchWorld;
    FIntVector WorkbenchCell=FIntVector::ZeroValue;
    bool bWorkbenchOpen=false;
    float WorkbenchWidth=0;
    float WorkbenchDock=0;     // 面板右缘到视口右缘的当前间距（同冶炼口径，参与布局变化判定）
    float WorkbenchMotion=0;   // 滑入滑出进度（同冶炼动画速率）
    bool bWorkbenchRiding=false;   // 关闭相位：与背包刚体骑乘向右缩回
    float WorkbenchSlidePx=0;      // 面板滑距＝面板宽+24（开着时记忆）
    /** 互斥瞬收：两面板共用同一贴位，开一个时另一个立即收起（不播骑乘动画）。 */
    void HideSmeltingInstantly();
    void HideWorkbenchInstantly();
    void BuildHotbar(UCanvasPanel* Root);
    void BuildQuickSlot(UOverlay* Overlay,int32 Index,FName FixedSkill=NAME_None);
    void RefreshQuickBar();
    int32 QuickBarDropIndex(FVector2D Position) const;
    void HighlightQuickBar(int32 Index,bool Valid);
    void HandleQuickDragActivation(bool Active);
    TWeakObjectPtr<UColdSteelQuickDrag> QuickDrag;
    FDelegateHandle QuickDragActivationHandle;
    bool bCloseAfterQuickDrag=false;
    UPROPERTY(Transient) TArray<TObjectPtr<class UColdSteelQuickSlot>> QuickSlots;
    UPROPERTY(Transient) TArray<TObjectPtr<UBorder>> QuickSlotSurfaces;
    // G 专属槽（环绕飞剑）：仅装备符文长剑时显示，卸下收起整格与分隔线。
    UPROPERTY(Transient) TObjectPtr<UBorder> RuneBladesSlotSurface;
    UPROPERTY(Transient) TObjectPtr<UBorder> RuneBladesDivider;
    void BuildStamina(UCanvasPanel* Root);
    void RefreshStamina();
    void UpdateStaminaLayout(const FGeometry& Geometry);
    FDelegateHandle StaminaHandle;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> StaminaSlot;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StaminaValue;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> DashAttackReadyText;
    UPROPERTY(Transient) TObjectPtr<USizeBox> StaminaMeterSize;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelResourceMeter> StaminaMeter;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> StaminaSheetBar;
    float StaminaLayoutScale=0;
    FVector2D StaminaLayoutView=FVector2D::ZeroVector;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> HotbarCanvasSlot;
    UPROPERTY(Transient) TArray<TObjectPtr<UBorder>> HotbarDropSlots;
    TWeakObjectPtr<class UColdSteelItemDrag> InventoryDrag;
    FSlateRect InventoryDragBounds;
    bool bInventoryDragOutside=false;
    FDelegateHandle InventoryDragActivationHandle;
    void HandleInventoryDragActivation(bool Active);
    int32 HotbarDropIndex(FVector2D ScreenPosition)const;
    bool CanDropOnHotbar(const class UColdSteelItemDrag* Drag)const;
    void BuildAmmoReadout(UCanvasPanel* Root);
    void BuildInventory(UCanvasPanel* Root);
    void UpdateInventoryLayout(const FGeometry& Geometry);
    UTextBlock* MakeInventoryText(const FString& Text,float Pixels,const FLinearColor& Color,bool Numeric=false,bool Medium=false);
    struct FInventoryLabel {TWeakObjectPtr<UTextBlock> Widget;float Pixels;bool Numeric,Medium;};
    TArray<FInventoryLabel> InventoryLabels;
    FVector2D InventoryLayoutSize=FVector2D::ZeroVector;
    float InventoryLayoutScale=0,InventoryWidth=0;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> InventoryPanelSlot;
    UPROPERTY(Transient) TObjectPtr<UBorder> InventoryHeaderSurface;
    UPROPERTY(Transient) TObjectPtr<class USizeBox> InventoryHeaderSize;
    TArray<TWeakObjectPtr<class USizeBox>> InventoryTabSizes;
    UPROPERTY(Transient) TObjectPtr<class UVerticalBoxSlot> InventoryFooterSlot;
    UWidget* BuildStatusPage();
    UWidget* BuildEquipmentPage();
    void BuildStatusTooltip(UCanvasPanel* Root);
    void BuildEquipmentTooltip(UCanvasPanel* Root);
    void BuildEventTimeline(UCanvasPanel* Root);
    void SetInventoryOpen(bool bOpen);
    void SetInventoryTab(bool bStatusTab);
    void SetInventoryPage(int32 Page);
    void RefreshAmmo();
    void RefreshStatus();
    void RefreshCharacterSheet();
    void UpdateStatusTooltipPlacement();
    void BuildCharacterSummary(UCanvasPanel* Root);
    void BuildTopVitals(UCanvasPanel* Root);
    void RefreshTopVitals();
    void UpdateTopHUDLayout(const FGeometry& Geometry);
    void RefreshWorldClock();
    UTextBlock* MakeTopHUDText(const FString& Text,float Pixels,const FLinearColor& Color,bool Numeric=false,bool Medium=false);
    TArray<FInventoryLabel> TopHUDLabels;
    FVector2D TopHUDViewport=FVector2D::ZeroVector;
    float TopHUDScale=0,TopHUDBottom=0;
    TWeakObjectPtr<class AFPSWeatherManager> HUDWeatherSource;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelWorldClock> WorldClock;
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> TopVitalsBlur;
    UPROPERTY(Transient) TObjectPtr<UBorder> TopVitalsTint;
    UPROPERTY(Transient) TObjectPtr<class UGridPanel> TopVitalsGrid;
    UPROPERTY(Transient) TArray<TObjectPtr<UBorder>> TopResourceCards;
    UPROPERTY(Transient) TArray<TObjectPtr<USizeBox>> TopMeterSizes;
    UPROPERTY(Transient) TObjectPtr<UBorder> TopLevelSurface;
    UPROPERTY(Transient) TObjectPtr<USizeBox> TopLevelSize;
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
    void TickEventTimelinePresentation(float Delta);
    void SetTimelineDetailsOpen(bool Open);
    UTextBlock* MakeTimelineText(const FString& Text,float Pixels,const FLinearColor& Color,bool Numeric=false,bool Medium=false);
    TArray<FInventoryLabel> TimelineLabels;
    void UpdateEventTimelineFilterButtons();
    void RebuildEventDetails();
    void SetEventTimelineCompact(bool bCompact);

    UTextBlock* MakeText(const FString& Text, int32 Size, const FLinearColor& Color, bool bNumeric = false, bool bBold = false);
    UTextBlock* MakeReferenceText(const FString& Text, float PixelSize, const FLinearColor& Color, bool bNumeric = false, bool bBold = false);
    /** 统一 E 交互小浮窗（2026-09-24）：准星下方，毛玻璃灰黑＋白字；替代一切模型上方世界空间名牌。 */
    void BuildInteractHint(UCanvasPanel* Root);
    void UpdateInteractHint();
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

    /** 统一 E 交互小浮窗：毛玻璃灰黑（真模糊＋GlassTint）＋白字，准星下方；替代一切模型上方名牌。 */
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> InteractHintBlur;
    UPROPERTY(Transient) TObjectPtr<class UTextBlock> InteractHintKey;
    UPROPERTY(Transient) TObjectPtr<class UTextBlock> InteractHintText;
    FString LastInteractHintText;
    bool bLastInteractHintAction=true;

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
    UPROPERTY(Transient) TObjectPtr<UHorizontalBox> EquipmentAmmoTabs;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelAmmoPouchWidget> AmmoPouchPage;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelSkillPage> SkillPage;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelCodexPage> CodexPage;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelProgressNotification> ProgressNotification;
    UPROPERTY(Transient) TObjectPtr<UBorder> SkillTabSurface;
    UPROPERTY(Transient) TObjectPtr<UBorder> SkillTabUnderline;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> SkillTabText;
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
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> TimelineShellBlur;
    UPROPERTY(Transient) TObjectPtr<UBorder> TimelineContentPadding;
    UPROPERTY(Transient) TObjectPtr<USizeBox> TimelineExpandedClip;
    UPROPERTY(Transient) TObjectPtr<UScrollBox> TimelineExpandedScroll;
    UPROPERTY(Transient) TObjectPtr<UScrollBox> TimelineDetailScroll;
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> TimelineDetailBlur;
    UPROPERTY(Transient) TObjectPtr<UBorder> TimelineDetailSurface;
    UPROPERTY(Transient) TObjectPtr<UBorder> TimelineTrackBackground;
    UPROPERTY(Transient) TObjectPtr<USizeBox> TimelineMarkerIconSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> TimelineToggleSize;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanel> TimelineToggleGlyph;
    UPROPERTY(Transient) TObjectPtr<USizeBox> TimelineToggleGlyphSize;
    UPROPERTY(Transient) TArray<TObjectPtr<USizeBox>> TimelineButtonSizes;
    UPROPERTY(Transient) TObjectPtr<UButton> TimelineDetailsClose;
    float TimelineExpansion=0,TimelineDetailMotion=0,TimelineScale=0;
    float TimelineShownEventFraction=.04f,TimelineEventMoveFrom=.04f,TimelineEventMoveTarget=.04f,TimelineEventMoveTime=.18f;
    float TimelineDetailWidth=0;
    bool bTimelineDetailsOpen=false;

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
    /** 外部抽屉（F6 开发面板）打开期间的同一让位标记。 */
    bool bExternalDrawerOpen = false;
    float DrawerProgress = 0.0f;
    float AmmoRefreshAccumulator = 0.0f;
    float StatusRefreshAccumulator = 0.0f;
    bool bStatusTabActive = false;
    bool bSkillsTabActive = false;
    bool bCodexTabActive = false;
    bool bEquipmentTooltipPinned = false;
    float TimelineRefreshAccumulator = 0.0f;
    float TimelinePulse = 0.0f;
    float TimelineEventFraction = 0.04f;
    float TimelineEventStart = 0.0f;
    float TimelineEventEnd = 0.0f;
    float TimelineDaySeconds = 1440.0f;
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
