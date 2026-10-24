#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "ApartmentDeviceControl.generated.h"

class UBoxComponent;
class UStaticMeshComponent;
class APlayerController;

/** Physical power control, reached through the standard aim/E interaction. */
UCLASS()
class FPSGAME_API AApartmentDeviceControl : public AActor
{
    GENERATED_BODY()
public:
    AApartmentDeviceControl();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    bool ToggleFrom(APlayerController* Controller);
    FString GetPrompt() const;
    bool IsPowered() const { return bPowered; }
    float GetPoweredSeconds() const;
    void SetPresentationActive(bool bActive) { bPresentationActive=bActive; }
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Apartment") FText DeviceName;
    UPROPERTY(EditAnywhere,BlueprintReadWrite,Category="Apartment") bool bWorkout=false;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Apartment") TObjectPtr<UBoxComponent> UseBounds;
    UPROPERTY(VisibleAnywhere,BlueprintReadOnly,Category="Apartment") TObjectPtr<UStaticMeshComponent> Panel;
private:
    UPROPERTY(Replicated) bool bPowered=false;
    UPROPERTY(Replicated) float PowerStartedAt=0.f;
    bool bPresentationActive=false;
};
