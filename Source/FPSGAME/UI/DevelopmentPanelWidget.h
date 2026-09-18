#pragma once
#include "WeatherControlWidget.h"
#include "ColdSteelStatusModel.h"
#include "Components/ComboBoxString.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "DevelopmentPanelWidget.generated.h"

class UDevelopmentSpawnComponent;
class UColdSteelHUDWidget;
class AFPSWeatherManager;
class UWidgetSwitcher;
class USpinBox;
class UCanvasPanelSlot;
class USizeBox;
class UBorder;
class UBackgroundBlur;
class UGridPanel;
class UHorizontalBox;
class UButton;

/** Unified developer shell for session tuning, weather and monster spawning. */
UCLASS()
class FPSGAME_API UDevelopmentPanelWidget : public UWeatherControlWidget
{
    GENERATED_BODY()
public:
    virtual void SetPanelOpen(bool bOpen) override;
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& Geometry, float DeltaSeconds) override;
    virtual FReply NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual void RefreshStatus() override;
private:
    UDevelopmentSpawnComponent* ResolveSpawner() const;
    UColdSteelStatusModel* ResolveModel() const;
    UColdSteelHUDWidget* ResolveHUD() const;
    void PopulateMonsters();
    void PopulateItems();
    void PopulateSkills();
    void SetPage(int32 Index);
    void UpdateLayout();
    void TickDrawer(float Delta);
    void StyleChoice(UComboBoxString* Combo, float Scale);
    void StyleCount(USpinBox* Spin, float Scale);
    void BuildTuningPage(UVerticalBox* Page);
    void UpdateTuningLayout(float ContentWidth, float Scale);
    void BuildFeatureRows(UVerticalBox* Page);
    void UpdateFeatureLayout(float ContentWidth, float Scale);
    void RefreshTuning();
    void RefreshFeatures();
    void RefreshTimeHelp();
    void SetFeatureMessage(const FString& Text, const FLinearColor& Color);
    void ToggleTuning(EDevelopmentTuningOption Option);
    AFPSWeatherManager* ResolveWeatherClock() const;
    const FColdSteelCatalogEntry* SelectedItem() const;
    UFUNCTION() void OpenDeveloper();
    UFUNCTION() void CloseDeveloper();
    UFUNCTION() void WeatherClicked();
    UFUNCTION() void MonstersClicked();
    UFUNCTION() void TuningClicked();
    UFUNCTION() void InvincibleClicked();
    UFUNCTION() void OneHitKillClicked();
    UFUNCTION() void InfiniteAmmoClicked();
    UFUNCTION() void InfiniteManaClicked();
    UFUNCTION() void NoCooldownClicked();
    UFUNCTION() void FreeBuildingClicked();
    UFUNCTION() void DisableTuningClicked();
    UFUNCTION() void GenerateItemClicked();
    UFUNCTION() void GrantLevelClicked();
    UFUNCTION() void RaiseSkillClicked();
    UFUNCTION() void MaxSkillClicked();
    UFUNCTION() void AdvanceHourClicked();
    UFUNCTION() void SpawnClicked();
    UFUNCTION() void ClearMonstersClicked();
    UFUNCTION() UWidget* GenerateMonsterOption(FString Item);
    UFUNCTION() UWidget* GenerateListOption(FString Item);
    UFUNCTION() void MonsterSelected(FString Name, ESelectInfo::Type Type);
    UFUNCTION() void ItemSelected(FString Name, ESelectInfo::Type Type);
    UFUNCTION() void SkillSelected(FString Name, ESelectInfo::Type Type);
    UPROPERTY(Transient) TObjectPtr<UWidgetSwitcher> Pages;
    UPROPERTY(Transient) TObjectPtr<UComboBoxString> MonsterChoice;
    UPROPERTY(Transient) TObjectPtr<UComboBoxString> ItemChoice;
    UPROPERTY(Transient) TObjectPtr<UComboBoxString> SkillChoice;
    UPROPERTY(Transient) TObjectPtr<USpinBox> CountBox;
    UPROPERTY(Transient) TObjectPtr<USpinBox> DistanceBox;
    UPROPERTY(Transient) TObjectPtr<USpinBox> ItemCountBox;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> SpawnStatus;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> SpawnCount;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> FeatureStatus;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> LevelHelp;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> SkillHelp;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> TimeHelp;
    UPROPERTY(Transient) TObjectPtr<UButton> WeatherTab;
    UPROPERTY(Transient) TObjectPtr<UButton> MonsterTab;
    UPROPERTY(Transient) TObjectPtr<UButton> TuningTab;
    UPROPERTY(Transient) TObjectPtr<UButton> Shortcut;
    UPROPERTY(Transient) TObjectPtr<UButton> GenerateItemButton;
    UPROPERTY(Transient) TObjectPtr<UButton> GrantLevelButton;
    UPROPERTY(Transient) TObjectPtr<UButton> RaiseSkillButton;
    UPROPERTY(Transient) TObjectPtr<UButton> MaxSkillButton;
    UPROPERTY(Transient) TObjectPtr<UButton> AdvanceHourButton;
    UPROPERTY(Transient) TObjectPtr<UButton> DisableTuningButton;
    UPROPERTY(Transient) TObjectPtr<UWidget> TuningActions;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> TuningStatus;
    UPROPERTY(Transient) TObjectPtr<UButton> SpawnButton;
    UPROPERTY(Transient) TObjectPtr<UButton> ClearButton;
    UPROPERTY(Transient) TObjectPtr<UWidget> SpawnActions;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> PanelSlot;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> ShortcutSlot;
    UPROPERTY(Transient) TObjectPtr<UBorder> Surface;
    UPROPERTY(Transient) TObjectPtr<UBorder> DrawerBackdrop;
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> Blur;
    TArray<FName> MonsterIds;
    FName SelectedMonster = TEXT("FatZombie");
    TArray<FColdSteelCatalogEntry> ItemOptions;
    FString SelectedItemDefinition;
    TArray<FName> SkillIds;
    FName SelectedSkill = NAME_None;
    /** 与背包装备同一抽屉动画：进度 0 收起、1 展开，速度 4.0/s。 */
    float DrawerProgress = 0.f;
    float DrawerSlide = 0.f;
    bool bHudYielded = false;
    FVector2D LastViewport = FVector2D::ZeroVector;
    float LastPixelScale = 0.f;
    int32 ActivePage = 2;
    struct FTuningRow
    {
        EDevelopmentTuningOption Option;
        TWeakObjectPtr<UBorder> Card;
        TWeakObjectPtr<UGridPanel> Grid;
        TWeakObjectPtr<UVerticalBox> Copy;
        TWeakObjectPtr<USizeBox> SwitchBox;
        TWeakObjectPtr<UButton> Button;
    };
    TArray<FTuningRow> TuningRows;
    struct FFeatureRow
    {
        TWeakObjectPtr<UBorder> Card;
        TWeakObjectPtr<UGridPanel> Grid;
        TWeakObjectPtr<UVerticalBox> Copy;
        TWeakObjectPtr<UWidget> Control;
        /** 宽布局下右对齐的下拉容器；窄布局占满整行剩余宽度。 */
        TWeakObjectPtr<USizeBox> FlexBox;
        float FlexPixels = 0.f;
        /** 按钮与数值框：固定像素宽度，两种布局共用。 */
        TArray<TPair<TWeakObjectPtr<USizeBox>, float>> FixedBoxes;
    };
    TArray<FFeatureRow> FeatureRows;
    TWeakObjectPtr<UDevelopmentTuningSubsystem> BoundTuning;
    FDelegateHandle TuningChangedHandle;
    bool bTuningAvailable = false;
};
