#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "WeatherControlWidget.generated.h"

class AFPSWeatherManager;
class UBorder;
class UButton;
class UTextBlock;
class UVerticalBox;

UCLASS()
class FPSGAME_API UWeatherControlWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    virtual void SetPanelOpen(bool bOpen);
    bool IsPanelOpen() const { return bPanelOpen; }
    void SelectPreset(int32 State);
    void SelectAutomatic();
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeDestruct() override;
    virtual FReply NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual void RefreshStatus();
    void BuildWeatherContent(UVerticalBox* Stack);
    UTextBlock* CreatePanelText(const FString& Caption, float Pixels, FLinearColor Color);
    UButton* CreatePanelButton(const FString& Caption, FName Name);
    void RefreshPanelTypography();
    UButton* AddButton(UVerticalBox* Stack, const FString& Caption, const FName Name);
    UPROPERTY(Transient) TObjectPtr<UWidget> Panel;
    UPROPERTY(Transient) TObjectPtr<UButton> CloseButton;
    TArray<TPair<TWeakObjectPtr<UTextBlock>, float>> TextSizes;
private:
    AFPSWeatherManager* ResolveWeather();
    UFUNCTION() void OpenClicked();
    UFUNCTION() void CloseClicked();
    UFUNCTION() void ClearClicked();
    UFUNCTION() void CloudyClicked();
    UFUNCTION() void LightClicked();
    UFUNCTION() void RainClicked();
    UFUNCTION() void StormClicked();
    UFUNCTION() void AutoClicked();
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Status;
    UPROPERTY(Transient) TArray<TObjectPtr<UButton>> PresetButtons;
    UPROPERTY(Transient) TWeakObjectPtr<AFPSWeatherManager> Weather;
    FTimerHandle RefreshTimer;
    bool bPanelOpen = false;
};
