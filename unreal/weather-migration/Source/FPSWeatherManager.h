#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FPSWeatherManager.generated.h"

class UAudioComponent;
class UDecalComponent;
class UMaterialInterface;
class UMaterialParameterCollection;
class UNiagaraComponent;
class UNiagaraSystem;
class UPointLightComponent;
class USceneComponent;
class USoundBase;

UENUM(BlueprintType)
enum class EFPSWeatherState : uint8
{
    Clear,
    Cloudy,
    LightRain,
    Rain,
    Storm
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FFPSWeatherChanged, EFPSWeatherState, PreviousState, EFPSWeatherState, NewState);

UCLASS(Blueprintable)
class FPSGAME_API AFPSWeatherManager : public AActor
{
    GENERATED_BODY()

public:
    AFPSWeatherManager();
    virtual void Tick(float DeltaSeconds) override;

    UFUNCTION(BlueprintCallable, Category="Weather")
    void SetWeatherState(EFPSWeatherState NewState, bool bDisableAutomaticSchedule = true);

    UFUNCTION(BlueprintCallable, Category="Weather")
    void ResumeAutomaticSchedule();

    UFUNCTION(BlueprintPure, Category="Weather")
    float GetEffectiveRainIntensity() const { return EffectiveRainIntensity; }

    UPROPERTY(BlueprintAssignable, Category="Weather")
    FFPSWeatherChanged OnWeatherChanged;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Clock", meta=(ClampMin="60.0"))
    float RealSecondsPerGameDay = 2160.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Clock")
    int32 WeatherSeed = 122;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Clock")
    bool bAutomaticSchedule = true;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Transition", meta=(ClampMin="0.1"))
    float TransitionSeconds = 8.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Rain")
    TObjectPtr<UNiagaraSystem> RainSystem;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Rain")
    TObjectPtr<UNiagaraSystem> SplashSystem;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Audio")
    TObjectPtr<USoundBase> LightRainSound;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Audio")
    TObjectPtr<USoundBase> RainSound;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Audio")
    TObjectPtr<USoundBase> HeavyRainSound;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Audio")
    TArray<TObjectPtr<USoundBase>> ThunderSounds;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Surface")
    TObjectPtr<UMaterialParameterCollection> WeatherParameters;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Surface")
    TObjectPtr<UMaterialInterface> PuddleDecalMaterial;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Surface", meta=(ClampMin="0", ClampMax="24"))
    int32 RuntimePuddleCount = 8;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Weather")
    EFPSWeatherState CurrentState = EFPSWeatherState::Clear;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Weather")
    float NormalizedDayTime = 0.25f;

protected:
    virtual void BeginPlay() override;

private:
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<USceneComponent> SceneRoot;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UNiagaraComponent> RainComponent;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UNiagaraComponent> SplashComponent;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UAudioComponent> LightRainAudio;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UAudioComponent> RainAudio;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UAudioComponent> HeavyRainAudio;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UAudioComponent> ThunderAudio;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UPointLightComponent> LightningLight;

    UPROPERTY(Transient)
    TArray<TObjectPtr<UDecalComponent>> RuntimePuddles;

    float WeatherClockSeconds = 540.0f;
    float LastSkyTimeUnits = -1.0f;
    int32 DaySerial = 0;
    float TargetRainIntensity = 0.0f;
    float EffectiveRainIntensity = 0.0f;
    float ShelterAmount = 0.0f;
    float ShelterCheckAccumulator = 0.0f;
    float PuddleRefreshAccumulator = 0.0f;
    float LightningCountdown = 8.0f;
    float LightningFlashTime = 0.0f;
    FRandomStream WeatherRandom;

    void ApplyState(EFPSWeatherState NewState);
    void UpdateSchedule();
    void UpdatePlayerFollowing();
    void UpdateShelter(float DeltaSeconds);
    void UpdateEffects(float DeltaSeconds);
    void UpdateLightning(float DeltaSeconds);
    void RefreshRuntimePuddles();
    bool TrySynchronizeWithSkyClock();
    EFPSWeatherState ResolveScheduledState() const;
    float StateIntensity(EFPSWeatherState State) const;
    void PlayDelayedThunder(float DelaySeconds);
};
