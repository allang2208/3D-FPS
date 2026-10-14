#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "GameFramework/PlayerInput.h"
#include "Styling/SlateTypes.h"
#include "ColdSteelGameMenuWidget.generated.h"

class SVerticalBox;
class SScrollBox;

/** Persistent corner entry and its modal pages. All settings use the local user's config. */
UCLASS()
class FPSGAME_API UColdSteelGameMenuWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void ShowMenu();
    void HideMenu();
    void GoBack();
    bool IsMenuOpen() const { return bOpen; }

protected:
    virtual void NativeOnInitialized() override;
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
    virtual FReply NativeOnPreviewKeyDown(const FGeometry&, const FKeyEvent&) override;

private:
    enum class EPage : uint8 { Main, Settings, Controls, Quit };
    EPage Page = EPage::Main;
    bool bOpen = false;
    bool bSettingsDirty = false;
    bool bHasMouseX = false, bHasMouseY = false;
    float MasterVolume = 1.f, MusicVolume = 1.f, MouseScale = 1.f;
    bool bInvertY = false;
    FInputAxisProperties BaseMouseX, BaseMouseY;
    FString QuitError;
    FSlateBrush PanelBrush, HeaderBrush, DimBrush;
    FButtonStyle ActionStyle;
    FSliderStyle SliderStyle;
    TSharedPtr<SVerticalBox> Body;
    TSharedPtr<SWidget> DefaultFocus;
    TSharedPtr<SScrollBox> VerticalScroll, HorizontalScroll;

    void SetPage(EPage NewPage);
    void BuildPage();
    void ApplyLocalSettings();
    void SaveSettings();
    void ConfirmQuit();
    float PanelWidth() const;
    FVector2D ViewportSize() const;
    TSharedRef<SWidget> Action(const FString& Label, TFunction<void()> Callback,
        const FString& Key = FString(), bool bDanger = false);
    void AddSection(const FString& Label);
    void AddSlider(const FString& Label, float Min, float Max, TAttribute<float> Value,
        TFunction<void(float)> Changed, TAttribute<FText> Formatted);
};
