void AFPSWeatherManager::AdvanceNaturalClock(float DeltaSeconds)
{
    if(!FMath::IsFinite(DeltaSeconds)||DeltaSeconds<=0.f)return;
    const double Before=NaturalDayProgress;
    const float Previous=NormalizedDayTime;
    const float BeforeSeconds=WeatherClockSeconds;
    const float Advanced=WeatherClockSeconds+DeltaSeconds;
    WeatherClockSeconds=FMath::Fmod(Advanced,RealSecondsPerGameDay);
    NormalizedDayTime=WeatherClockSeconds/RealSecondsPerGameDay;
    if(NormalizedDayTime<Previous)++DaySerial;
    // Follow the same float calendar used by the existing schedule,
    // including its wrap rounding; do not create a competing day clock.
    NaturalDayProgress+=FMath::Max(0.,(double(WeatherClockSeconds)-BeforeSeconds)/RealSecondsPerGameDay
        +FMath::FloorToDouble(double(Advanced)/RealSecondsPerGameDay));
    const double WorldDelta=GetWorld()->GetDeltaSeconds();
    NaturalDayRate=(NaturalDayProgress-Before)/(WorldDelta>0.?WorldDelta:DeltaSeconds);
}
