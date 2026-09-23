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
class UPostProcessComponent;
class USceneComponent;
class USoundBase;
class UWeatherSurfaceComponent;

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

    /**
     * 开发面板用：把世界时钟整体前推 Hours 小时（正数）。
     * 由天空时钟驱动的关卡（场景里有 BP_FPS_DayNightManager 的 SunHeight）推它自己的时间，
     * 其余关卡推本管理器内部时钟；两条路径都维持"唯一权威时钟"的约定，不另建计时器。
     */
    UFUNCTION(BlueprintCallable, Category="Weather")
    void AdvanceGameTime(float Hours);

    UFUNCTION(BlueprintPure, Category="Weather")
    float GetEffectiveRainIntensity() const { return EffectiveRainIntensity; }
    float GetSurfaceWetness() const;
    float GetRainExposure() const { return 1.0f - ShelterAmount; }
    FVector GetWeatherWind() const { return WeatherWind; }
    // X = sky radiance, Y = cloud radiance; scaled to the current day/night sky.
    FVector2D GetLightningMaterialLuminance() const;
    class UWeatherPresentationAssets* GetPresentationAssets() const { return PresentationAssets; }

    bool IsSkyClockConnected() const { return bSkyClockConnected; }
    bool IsSceneDayNightActive() const { return bSceneDayNightActive; }
    UFUNCTION(BlueprintPure, Category="Weather")
    bool IsRainPending() const { return bRainPending; }
    UFUNCTION(BlueprintPure, Category="Weather")
    float GetRainLeadInRemaining() const;
    EFPSWeatherState GetPendingRainState() const { return PendingRainState; }

    // Forecasts and rebuilt HUDs read the same calendar and schedule as the simulation.
    static constexpr int32 ScheduleSegmentsPerDay = 8;
    int32 GetScheduleDay() const { return DaySerial; }
    EFPSWeatherState GetScheduledStateAt(int32 Day, int32 Segment) const;

    UPROPERTY(EditDefaultsOnly, Category="Weather|Presentation")
    TSoftObjectPtr<class UWeatherPresentationAssets> PresentationLibrary;

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

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Transition", meta=(ClampMin="1.0", Units="s"))
    float RainCloudLeadSeconds = 30.0f;

    // Hills lighting is applied to the authored clock baseline, never to the
    // previous frame's weather-attenuated intensity.
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Hills Lighting", meta=(ClampMin="1.0", ClampMax="4.0"))
    float HillsDaySkyLightScale = 1.8f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Hills Lighting", meta=(ClampMin="0.0", ClampMax="1.5"))
    float HillsShadeExposureAllowance = 0.75f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Hills Lighting", meta=(ClampMin="0.6", ClampMax="1.0"))
    float HillsDayShadowContrast = 0.65f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Rain")
    TObjectPtr<UNiagaraSystem> RainSystem;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Rain")
    TObjectPtr<UNiagaraSystem> SplashSystem;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Rain")
    TObjectPtr<UNiagaraSystem> MistSystem;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Rain")
    TObjectPtr<UNiagaraSystem> RoofDripSystem;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Audio")
    TObjectPtr<USoundBase> LightRainSound;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Audio")
    TObjectPtr<USoundBase> RainSound;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Audio")
    TObjectPtr<USoundBase> HeavyRainSound;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Audio")
    TArray<TObjectPtr<USoundBase>> ThunderSounds;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Lightning", meta=(ClampMin="0.0", Units="s"))
    float LightningHoldSeconds = 0.5f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Lightning", meta=(ClampMin="0.1", Units="s"))
    float LightningFadeSeconds = 1.5f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Lightning", meta=(Units="s"))
    FVector2D LightningIntervalSeconds = FVector2D(12.0, 25.0);

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Lightning", meta=(Units="s"))
    FVector2D FirstLightningDelaySeconds = FVector2D(3.0, 6.0);

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Lightning", meta=(Units="s"))
    FVector2D ThunderDelaySeconds = FVector2D(2.0, 5.0);

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Lightning", meta=(ClampMin="0.0", ClampMax="1.0"))
    float LightningStrength = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Lightning", meta=(ClampMin="0.0", ClampMax="200000.0"))
    float LightningFillLumens = 60000.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Audio", meta=(ClampMin="0.0", ClampMax="1.0"))
    float ThunderVolume = 1.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Surface")
    TObjectPtr<UMaterialParameterCollection> WeatherParameters;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Surface")
    TObjectPtr<UMaterialInterface> PuddleDecalMaterial;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Weather")
    EFPSWeatherState CurrentState = EFPSWeatherState::Clear;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Weather")
    float NormalizedDayTime = 0.25f;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    friend struct FWeatherWorldAudit;
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<USceneComponent> SceneRoot;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UNiagaraComponent> RainComponent;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UNiagaraComponent> MistComponent;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UWeatherSurfaceComponent> SurfaceEffects;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<class UStormCloudComponent> StormClouds;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<class UWeatherViewEffectsComponent> ViewEffects;

    UPROPERTY()
    TObjectPtr<class UWeatherPresentationAssets> PresentationAssets;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UAudioComponent> LightRainAudio;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UAudioComponent> RainAudio;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UAudioComponent> HeavyRainAudio;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UAudioComponent> ThunderAudio;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UAudioComponent> ThunderTailAudio;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UPointLightComponent> LightningLight;

    UPROPERTY(Transient)
    TObjectPtr<UPostProcessComponent> HillsExposure;

    float WeatherClockSeconds = 540.0f;
    float LastSkyTimeUnits = -1.0f;
    int32 DaySerial = 0;
    float TargetRainIntensity = 0.0f;
    float EffectiveRainIntensity = 0.0f;
    float CloudyElapsedSeconds = 0.0f;
    EFPSWeatherState PendingRainState = EFPSWeatherState::Clear;
    bool bRainPending = false;
    float ShelterAmount = 0.0f;
    float ShelterTarget = 0.0f;
    FVector WeatherWind = FVector(120.0, 40.0, 0.0);
    float ShelterCheckAccumulator = 0.0f;
    float LightningCountdown = 12.0f;
    float LightningFlashElapsed = -1.0f;
    float LightningPeak = 1.0f;
    float LightningAmount = 0.0f;
    float PublishedLightningAmount = -1.0f;
    float PendingThunderDelay = -1.0f;
    int32 PendingThunderSound = INDEX_NONE;
    int32 PendingThunderVoice = INDEX_NONE;
    int32 LastThunderSound = INDEX_NONE;
    float LastThunderGain = -1.0f;
    float LastThunderShelter = -1.0f;
    float AppliedLightningFill = -1.0f;
    float ThunderRainDuckSeconds = 0.0f;
    float ThunderRainMix = 1.0f;
    FRandomStream WeatherRandom;
    bool bSkyClockConnected = false;
    /** Cached sky-clock discovery result. The clock actor is level-static content,
        so the full world scan runs only until it resolves and again after it is gone. */
    TWeakObjectPtr<AActor> SkyClockActor;
    TWeakFieldPtr<class FProperty> SkyClockProperty;
    bool bSceneDayNightActive = false;
    float SceneLightingRefresh = 1.0f;
    TMap<TWeakObjectPtr<class ULightComponentBase>, float> SceneLightIntensities;
    TMap<TWeakObjectPtr<class ULightComponentBase>, FLinearColor> SceneLightColors;

    void UpdateSceneDayNight(float DeltaSeconds);
    void InitializeHillsLighting();

    void ApplyState(EFPSWeatherState NewState);
    void RequestState(EFPSWeatherState NewState);
    void UpdateSchedule();
    void UpdatePlayerFollowing();
    void UpdateShelter(float DeltaSeconds);
    void UpdateEffects(float DeltaSeconds);
    void UpdateLightning(float DeltaSeconds);
    bool TrySynchronizeWithSkyClock();
    EFPSWeatherState ResolveScheduledState() const;
    float StateIntensity(EFPSWeatherState State) const;
    bool QueueThunder(float DelaySeconds);
    void ResetLightning(bool bFadeThunder);
};
