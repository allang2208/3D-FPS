// Source/FPSGAME/Building/BronzeTorch.cpp

void ABronzeTorch::UpdateBurningFlame()
{
    UWorld* World = GetWorld();
    const double Now = World->GetTimeSeconds();
    if (Now >= NextFlameViewAt)
    {
        NextFlameViewAt = Now + .1;
        auto* Fluid = World->GetSubsystem<UFluidPresentationSubsystem>();
        const float Range = TorchFlame->LDMaxDrawDistance > 0.f ? TorchFlame->LDMaxDrawDistance : 6000.f;
        const auto Detail = Fluid ? Fluid->FireViews.Classify(*World, TorchFlame->GetComponentLocation(),
            90.f, 25.f, FMath::Min(2200.f, Range), Range, TorchFlame, bFullFlame) : EFireParticleDetail::Full;
        bFlameInView = Detail != EFireParticleDetail::Off;
        if (bFlameInView && bFullFlame != (Detail == EFireParticleDetail::Full))
        {
            bFullFlame = Detail == EFireParticleDetail::Full;
            for (const auto& Emitter : TorchFlame->GetAsset()->GetEmitterHandles())
            {
                const FName Name = Emitter.GetName();
                if (Emitter.GetIsEnabled() && (Name == TEXT("NE_Flame_02") || Name == TEXT("NE_Ashes") || Name == TEXT("NE_Heat")))
                    TorchFlame->SetEmitterEnable(Name, bFullFlame);
            }
        }
    }
    const float Scale = FlameScale * FMath::Lerp(FlameIgnitionScaleFloor, 1.f, IgnitionAmount);
    if (TorchFlame->GetRelativeScale3D() != FVector(Scale))
        TorchFlame->SetRelativeScale3D(FVector(Scale));
    if (bFlameInView)
    {
        if (!TorchFlame->IsActive()) TorchFlame->Activate(true);
    }
    else if (TorchFlame->IsActive()) TorchFlame->DeactivateImmediate();
}

void ABronzeTorch::ConfigureSceneLight(float Lumens,float RadiusCm,bool bShadows)
{
    LightLumens=Lumens;LightRadiusCm=RadiusCm;bLightCastsShadows=bShadows;
    TorchLight->SetAttenuationRadius(LightRadiusCm);
    TorchLight->SetCastShadows(bLightCastsShadows);
    TorchLight->SetIntensity(LightLumens*IgnitionAmount);
}

void ABronzeTorch::UpdateDormantClock()
{
    if (!bClockDormant) return;
    FTimerManager& Timers = GetWorldTimerManager();
    if (ShouldBeLitNow())
    {
        Timers.ClearTimer(DormantClockTimer);
        bClockDormant = false;
        WokeAt = GetWorld()->GetTimeSeconds();
        SetActorTickEnabled(true);
    }
    else if (!bAutomaticIgnition)
    {
        Timers.ClearTimer(DormantClockTimer);
    }
    else if (!Timers.TimerExists(DormantClockTimer))
    {
        Timers.SetTimer(DormantClockTimer, this, &ThisClass::PollDormantClock, ClockRefreshSeconds, true);
    }
}
