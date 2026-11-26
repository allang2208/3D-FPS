#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "UObject/WeakFieldPtr.h"
#include "FPSWeatherManager.h"
#include "FPSUDSBridgeComponent.generated.h"

class UFunction;
class ULevel;

/**
 * Ultra Dynamic Sky / Ultra Dynamic Weather presentation bridge.
 *
 * The weather manager stays the single authority for the clock, the weather
 * schedule and the network state. Only authority spawns UDS/UDW and submits
 * weather transitions; UDW replicates those transitions. FPS clock samples
 * drive Time Of Day on each peer, with UDS time replication explicitly off.
 *
 * Clock: UDS "Time Of Day" uses the same 0..2400 units as the retired
 * BP_FPS_DayNightManager clock, so the weather manager's NormalizedDayTime
 * maps 1:1 without conversion.
 *
 * Weather: FPS states map to UDS weather presets (Rain_Light/Rain/
 * Rain_Thunderstorm/Cloudy/Clear_Skies) through reflected Change Weather
 * parameters. Missing assets/interfaces retain the last valid presentation.
 */
UCLASS(ClassGroup=(Weather), meta=(BlueprintSpawnableComponent))
class FPSGAME_API UFPSUDSBridgeComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UFPSUDSBridgeComponent();

    virtual void BeginPlay() override;
    virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;

    /** Reflection state of the bridge for diagnostics panels. */
    bool IsClockConnected() const { return SkyActor.IsValid() && TimeProperty.IsValid(); }
    bool IsWeatherConnected() const { return WeatherActor.IsValid(); }
    EFPSWeatherState GetLastDrivenState() const { return LastDrivenState; }
    float GetLastDrivenClock() const { return LastDrivenClockUnits; }
    /** Shared global wind, not the listen host's local override-volume sample. */
    bool ReadGlobalWind(FVector& OutWind) const;
    bool ReadSunRays(FVector& Direction) const;
    /** UDW samples this actor's location, weather volumes and precipitation occlusion. */
    bool SampleActorRain(AActor* Actor,float& ExposedRain);

    UPROPERTY(EditAnywhere,Category="Weather|Thunder",meta=(ClampMin="0.0"))
    float CloseThunderSecondsPerKm=2.915f;
    UPROPERTY(EditAnywhere,Category="Weather|Thunder",meta=(ClampMin="0.0",ClampMax="1.0"))
    float ThunderRainReduction=.45f;

protected:
    /** Disable bridging entirely (perf kill switch; default on). */
    static bool IsBridgeEnabled();

private:
    TWeakObjectPtr<AFPSWeatherManager> Weather;
    TWeakObjectPtr<AActor> SkyActor;
    TWeakObjectPtr<AActor> WeatherActor;

    // UDS sky reflection handles.
    TWeakFieldPtr<FProperty> TimeProperty;
    TWeakFieldPtr<FProperty> AnimateProperty;
    TWeakFieldPtr<FProperty> DaySpeedProperty;

    // UDW reflection handles.
    UPROPERTY(Transient) TMap<int32, TObjectPtr<UObject>> PresetsByState;
    UPROPERTY(Transient) TObjectPtr<UClass> SkyClass;
    UPROPERTY(Transient) TObjectPtr<UClass> WeatherClass;
    TWeakObjectPtr<UFunction> ChangeWeatherFunction;
    TWeakFieldPtr<FProperty> WeatherPresetParameter;
    TWeakFieldPtr<FProperty> WeatherTimeParameter;
    // UDW's Test Actor for Weather Exposure reads camera-local rain/wind. Build
    // an independent settings object at the queried actor instead.
    UPROPERTY(Transient) TObjectPtr<UObject> ActorWeatherSample;
    TWeakObjectPtr<UFunction> ActorWeatherFunction;
    TWeakFieldPtr<FProperty> ActorWeatherLocation,ActorWeatherSettings,ActorWeatherConstruct;
    TWeakFieldPtr<FProperty> ActorRain,ActorWindIntensity,ActorWindDirection,WeatherBaseDirection;
    void BindActorWeatherQuery(AActor* Actor);
    TWeakFieldPtr<FProperty> NativeRainVolume,NativeThunderDelay,NativeLightningLocation,NativeFlashEvent;
    TWeakFieldPtr<FProperty> NativeSoundMaster,NativeSoundGlobal,NativeSoundDirectional,NativeSoundEnabled,NativeFlashActive;
    TWeakObjectPtr<class UAudioComponent> LastGlobalRainSound,LastDirectionalRainSound;
    TWeakObjectPtr<UFunction> NativeThunderDelayFunction;
    TWeakFieldPtr<FProperty> NativeThunderDelayResult;
    float OriginalThunderDelay=0.f,LastRainVolume=-1.f;
    bool bWeatherAudioConfigured=false,bOwnThunderDelay=false,bRainAudioOverride=false;
    TArray<FVector2D> ThunderDuckWindows;
    void ConfigureWeatherAudio();
    void UpdateWeatherAudio(float Delta);
    void ApplyRainAudioGain(float Amount);
    void RestoreWeatherAudio();
    UFUNCTION() void OnLightningFlashStarted();

    EFPSWeatherState LastDrivenState = static_cast<EFPSWeatherState>(255);
    float LastDrivenClockUnits = -1.0f;
    double ResolveRetryAfter = 0.0;
    bool bAllowAutoSpawn = false;
    bool bReportedPresentationFailure = false;
    bool bHillsAtmosphereConfigured = false;
    FDelegateHandle ActorSpawnedHandle;
    FDelegateHandle LevelAddedHandle;

    void ResolveActors();
    void RegisterActor(AActor* Actor);
    void RegisterLevel(ULevel* Level,UWorld* World);
    void BindSkyReflection(AActor* Sky);
    void ConfigureHillsAtmosphere();
    void ReleaseForestSampleLighting(ULevel* Level);
    void BindWeatherReflection(AActor* WeatherUDS);
    void CachePresets();
    void ApplyClock();
    void ApplyWeatherState(EFPSWeatherState NewState);
    bool CallChangeWeather(UObject* Preset, float TransitionSeconds);
};
