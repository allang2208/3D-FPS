FVector UFluidPresentationSubsystem::WindWithGustAt(const FVector& Position)
{
    if(GustFrame!=GFrameCounter)
    {
        GustFrame=GFrameCounter;
        const float Rain=Weather.IsValid()?FMath::Clamp(Weather->GetEffectiveRainIntensity(),0.f,1.f):0.f;
        SharedRainGust=Rain>.01f?RainGust(WeatherRainGust::SampleTime(*GetWorld()),Rain):FVector::ZeroVector;
    }
    float ShelterFactor=1.f;
    const FVector BaseWind=WindAt(Position,&ShelterFactor);
    return (BaseWind+SharedRainGust*ShelterFactor).GetClampedToMaxSize(260.f);
}
