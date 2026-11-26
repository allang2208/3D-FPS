#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "FPSWeatherManager.generated.h"

class UFPSUDSBridgeComponent;
class UMaterialParameterCollection;
class USceneComponent;
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

USTRUCT()
struct FFPSWeatherNetworkState
{
    GENERATED_BODY()
    UPROPERTY() double SampledAt=0.;
    UPROPERTY() float DayTime=.25f;
    UPROPERTY() int32 Day=0;
    UPROPERTY() float DaySeconds=2160.f;
    UPROPERTY() int32 Seed=122;
    UPROPERTY() EFPSWeatherState Weather=EFPSWeatherState::Clear;
    UPROPERTY() EFPSWeatherState Pending=EFPSWeatherState::Clear;
    UPROPERTY() bool Automatic=true;
    UPROPERTY() bool RainPending=false;
    UPROPERTY() float CloudyElapsed=0.f;
    UPROPERTY() float RainIntensity=0.f;
    UPROPERTY() float SurfaceWetness=0.f;
    UPROPERTY() float TransitionSeconds=8.f;
    UPROPERTY() float CloudLeadSeconds=30.f;
    UPROPERTY() FVector Wind=FVector(120.,40.,0.);
    UPROPERTY() bool Ready=false;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_TwoParams(FFPSWeatherChanged, EFPSWeatherState, PreviousState, EFPSWeatherState, NewState);

UCLASS(Blueprintable)
class FPSGAME_API AFPSWeatherManager : public AActor
{
    GENERATED_BODY()

public:
    AFPSWeatherManager();
    virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
    virtual void Tick(float DeltaSeconds) override;

    UFUNCTION(BlueprintCallable, Category="Weather")
    void SetWeatherState(EFPSWeatherState NewState, bool bDisableAutomaticSchedule = true);

    UFUNCTION(BlueprintCallable, Category="Weather")
    void ResumeAutomaticSchedule();

    /**
     * 开发面板用：把世界时钟整体前推 Hours 小时（正数）。
     * 时钟由本管理器唯一持有，UDS 表现层经 UDSBridge 跟随，不再有第二时钟。
     */
    UFUNCTION(BlueprintCallable, Category="Weather")
    void AdvanceGameTime(float Hours);

    UFUNCTION(BlueprintPure, Category="Weather")
    float GetEffectiveRainIntensity() const { return EffectiveRainIntensity; }
    float GetSurfaceWetness() const;
    float GetRainExposure() const { return 1.0f - ShelterAmount; }
    FVector GetWeatherWind() const { return WeatherWind; }
    bool SampleActorRain(AActor* Actor,float& ExposedRain) const;
    bool IsWeatherStateReady() const { return HasAuthority() || NetworkWeather.Ready; }

    bool IsSkyClockConnected() const;
    bool IsWeatherPresentationConnected() const;
    /** Kept for HUD/validation panels: the bridge now reports the live UDS clock. */
    bool IsSceneDayNightActive() const;
    /** Monotonic natural calendar progress on authority; manual jumps are excluded. */
    double GetNaturalDayProgress() const { return NaturalDayProgress; }
    double GetNaturalDayRate() const { return NaturalDayRate; }
    UFUNCTION(BlueprintPure, Category="Weather")
    bool IsRainPending() const { return bRainPending; }
    UFUNCTION(BlueprintPure, Category="Weather")
    float GetRainLeadInRemaining() const;
    EFPSWeatherState GetPendingRainState() const { return PendingRainState; }

    // Forecasts and rebuilt HUDs read the same calendar and schedule as the simulation.
    static constexpr int32 ScheduleSegmentsPerDay = 8;
    int32 GetScheduleDay() const { return DaySerial; }
    FFPSWeatherNetworkState CapturePersistentState() const;
    void RestorePersistentState(const FFPSWeatherNetworkState& Saved);
    EFPSWeatherState GetScheduledStateAt(int32 Day, int32 Segment) const;

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

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Weather|Surface")
    TObjectPtr<UMaterialParameterCollection> WeatherParameters;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Weather")
    EFPSWeatherState CurrentState = EFPSWeatherState::Clear;

    UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category="Weather")
    float NormalizedDayTime = 0.25f;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    friend struct FWeatherWorldAudit;
    UPROPERTY(ReplicatedUsing=OnRep_Weather) FFPSWeatherNetworkState NetworkWeather;
    UFUNCTION() void OnRep_Weather();
    void UpdateNetworkWeather(float Delta);
    float NetworkPublishLeft=0.f;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<USceneComponent> SceneRoot;

    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UWeatherSurfaceComponent> SurfaceEffects;

    /** Presentation bridge into Ultra Dynamic Sky / Ultra Dynamic Weather.
        The manager remains the clock and weather authority; this component
        forwards clock, weather state, wind and lightning into UDS. */
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<UFPSUDSBridgeComponent> UDSBridge;

    /** Weapon wet-material presentation driven by the gameplay rain values.
        Rain/sky visuals moved to Ultra Dynamic Weather via the bridge. */
    UPROPERTY(VisibleAnywhere)
    TObjectPtr<class UWeatherViewEffectsComponent> ViewEffects;

    float WeatherClockSeconds = 540.0f;
    double NaturalDayProgress=0.,NaturalDayRate=1./2160.;
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

    void ApplyState(EFPSWeatherState NewState);
    void RequestState(EFPSWeatherState NewState);
    void UpdateSchedule();
    void UpdatePlayerFollowing();
    void UpdateShelter(float DeltaSeconds);
    void AdvanceNaturalClock(float DeltaSeconds);
    friend class USurvivalClockAuditCommandlet;
    friend class UFoodSpoilageAuditCommandlet;
    EFPSWeatherState ResolveScheduledState() const;
    float StateIntensity(EFPSWeatherState State) const;
};
