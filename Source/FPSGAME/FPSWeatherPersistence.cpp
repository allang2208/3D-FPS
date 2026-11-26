#include "FPSWeatherManager.h"
#include "WeatherSurfaceComponent.h"

FFPSWeatherNetworkState AFPSWeatherManager::CapturePersistentState() const
{
    FFPSWeatherNetworkState Saved=NetworkWeather;
    Saved.SampledAt=0.;Saved.Day=DaySerial;Saved.DayTime=NormalizedDayTime;
    Saved.DaySeconds=RealSecondsPerGameDay;Saved.Seed=WeatherSeed;
    Saved.Weather=CurrentState;Saved.Pending=PendingRainState;Saved.Automatic=bAutomaticSchedule;
    Saved.RainPending=bRainPending;Saved.CloudyElapsed=CloudyElapsedSeconds;
    Saved.RainIntensity=EffectiveRainIntensity;Saved.SurfaceWetness=GetSurfaceWetness();
    Saved.Wind=WeatherWind;Saved.Ready=true;
    return Saved;
}

void AFPSWeatherManager::RestorePersistentState(const FFPSWeatherNetworkState& Saved)
{
    if(!HasAuthority()||!Saved.Ready||!FMath::IsFinite(Saved.DayTime)||!FMath::IsFinite(Saved.DaySeconds))return;
    DaySerial=FMath::Max(0,Saved.Day);NormalizedDayTime=FMath::Clamp(Saved.DayTime,0.f,.999999f);
    RealSecondsPerGameDay=FMath::Max(60.f,Saved.DaySeconds);
    WeatherClockSeconds=NormalizedDayTime*RealSecondsPerGameDay;
    WeatherSeed=Saved.Seed;bAutomaticSchedule=Saved.Automatic;
    ApplyState(Saved.Weather);PendingRainState=Saved.Pending;bRainPending=Saved.RainPending;
    CloudyElapsedSeconds=FMath::Max(0.f,Saved.CloudyElapsed);
    EffectiveRainIntensity=FMath::Clamp(Saved.RainIntensity,0.f,1.f);WeatherWind=Saved.Wind;
    SurfaceEffects->SetReplicatedWetness(FMath::Clamp(Saved.SurfaceWetness,0.f,1.f));
    // No offline time is added to the world or to hunger/thirst integration.
    NaturalDayRate=1./RealSecondsPerGameDay;
    NetworkPublishLeft=0.f;UpdateNetworkWeather(0.f);ForceNetUpdate();
}
