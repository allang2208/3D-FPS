#pragma once
#include "WeatherControlWidget.h"
#include "Components/ComboBoxString.h"
#include "../Development/DevelopmentTuningSubsystem.h"
#include "DevelopmentPanelWidget.generated.h"

class UDevelopmentSpawnComponent;
class UWidgetSwitcher;
class USpinBox;
class UCanvasPanelSlot;
class USizeBox;
class UBorder;
class UBackgroundBlur;
class UGridPanel;

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
    void PopulateMonsters();
    void SetPage(int32 Index);
    void UpdateLayout();
    void BuildTuningPage(UVerticalBox* Page);
    void UpdateTuningLayout(float ContentWidth, float Scale);
    void RefreshTuning();
    void ToggleTuning(EDevelopmentTuningOption Option);
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
    UFUNCTION() void DisableTuningClicked();
    UFUNCTION() void SpawnClicked();
    UFUNCTION() void ClearMonstersClicked();
    UFUNCTION() UWidget* GenerateMonsterOption(FString Item);
    UFUNCTION() void MonsterSelected(FString Name, ESelectInfo::Type Type);
    UPROPERTY(Transient) TObjectPtr<UWidgetSwitcher> Pages;
    UPROPERTY(Transient) TObjectPtr<UComboBoxString> MonsterChoice;
    UPROPERTY(Transient) TObjectPtr<USpinBox> CountBox;
    UPROPERTY(Transient) TObjectPtr<USpinBox> DistanceBox;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> SpawnStatus;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> SpawnCount;
    UPROPERTY(Transient) TObjectPtr<UButton> WeatherTab;
    UPROPERTY(Transient) TObjectPtr<UButton> MonsterTab;
    UPROPERTY(Transient) TObjectPtr<UButton> TuningTab;
    UPROPERTY(Transient) TObjectPtr<UButton> DisableTuningButton;
    UPROPERTY(Transient) TObjectPtr<UWidget> TuningActions;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> TuningStatus;
    UPROPERTY(Transient) TObjectPtr<UButton> SpawnButton;
    UPROPERTY(Transient) TObjectPtr<UButton> ClearButton;
    UPROPERTY(Transient) TObjectPtr<UWidget> SpawnActions;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> PanelSlot;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanelSlot> ShortcutSlot;
    UPROPERTY(Transient) TObjectPtr<UBorder> Surface;
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> Blur;
    TArray<FName> MonsterIds;
    FName SelectedMonster = TEXT("FatZombie");
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
    TWeakObjectPtr<UDevelopmentTuningSubsystem> BoundTuning;
    FDelegateHandle TuningChangedHandle;
    bool bTuningAvailable = false;
};
