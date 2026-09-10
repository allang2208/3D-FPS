#pragma once

#include "CoreMinimal.h"
#include "GameFramework/PlayerController.h"
#include "FPSGAMEPlayerController.generated.h"

class UColdSteelHUDWidget;
class UWeatherControlWidget;
struct FInputKeyEventArgs;

UCLASS()
class FPSGAME_API AFPSGAMEPlayerController : public APlayerController
{
    GENERATED_BODY()

public:
    AFPSGAMEPlayerController();
    void ToggleWeatherPanel();
    bool OpenGunsmith(const FString& Instance=TEXT(""));
    void CloseGunsmith();
    void RunM4GunsmithAudit();
    void RunM4DrumAudit();
    void RunGunsmithWorkbenchAudit();
    void RunGunsmithLayoutStress(TSharedPtr<FIntPoint> Counts);

protected:
    virtual void BeginPlay() override;
    virtual void SetupInputComponent() override;
    virtual bool InputKey(const FInputKeyEventArgs& Params) override;

private:
    UPROPERTY(Transient) TObjectPtr<class UM4GunsmithWidget> GunsmithPanel;
    void ToggleInventory();
    void BeginTimelineInteraction();
    void EndTimelineInteraction();
    void CaptureTimelineAudit(const FString& Filename, int32 State);
    void CaptureInventoryAudit(const FString& Filename, int32 State);

    UPROPERTY(Transient)
    TObjectPtr<UColdSteelHUDWidget> ColdSteelHUD;

    UPROPERTY(Transient)
    TObjectPtr<UWeatherControlWidget> WeatherPanel;
};
