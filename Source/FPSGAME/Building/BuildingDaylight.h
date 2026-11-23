#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Engine/BlendableInterface.h"
#include "BuildingDaylight.generated.h"

class AFPSWeatherManager;
class UBoxComponent;
class UPostProcessComponent;

/** An authored window, doorway or roof breach. Local +X points into the room. */
USTRUCT(BlueprintType)
struct FBuildingDaylightOpening
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector Position = FVector::ZeroVector;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FRotator Direction = FRotator::ZeroRotator;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="1")) float Width = 80.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="1")) float Height = 110.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0", ClampMax="1")) float Transmission = 1.f;
};

/** Interior eye adaptation. Class identity retained for existing village level assets. */
UCLASS(meta=(DisplayName="Building Interior Eye Adaptation"))
class FPSGAME_API ABuildingDaylight : public AActor, public IBlendableInterface
{
    GENERATED_BODY()
public:
    ABuildingDaylight();
    virtual void Tick(float DeltaSeconds) override;
    virtual void OnConstruction(const FTransform& Transform) override;
    virtual void OverrideBlendableSettings(FSceneView& View, float Weight) const override;
    // Serialized migration data only. This actor no longer creates any lights.
    UPROPERTY() TArray<FBuildingDaylightOpening> Openings;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Interior Vision") FVector RoomMinimum = FVector(-300,-450,0);
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Interior Vision") FVector RoomMaximum = FVector(300,450,500);
    UPROPERTY() float SkyIlluminance = 750.f;
    UPROPERTY() float SunIlluminance = 350.f;
    UPROPERTY() float ActivationDistance = 2200.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Interior Vision", meta=(ClampMin="0",ClampMax="4")) float AdditionalDarkAdaptationStops = 2.25f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Interior Vision", meta=(ClampMin="0",ClampMax="2")) float ExposureCompensation = .6f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Interior Vision", meta=(ClampMin="20")) float EntranceTransitionCm = 120.f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Interior Vision", meta=(ClampMin=".4",ClampMax="1")) float ShadowContrast = .6f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Interior Vision", meta=(ClampMin=".4",ClampMax="1")) float HighlightContrast = .7f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Interior Vision") bool bFollowDaylight = true;
protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
private:
    UPROPERTY(VisibleAnywhere) TObjectPtr<UBoxComponent> RoomBounds;
    UPROPERTY(VisibleAnywhere) TObjectPtr<UPostProcessComponent> Vision;
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    double NextWeatherSearch = 0.;
    float DaylightStrength = 1.f;
    void BindWeather();
    void UpdateBounds();
};
