// Source/FPSGAME/Building/ColdSteelCampfire.cpp

void AColdSteelCampfire::SetPresentationActive(bool bActive)
{
    bPresentationRequested=bActive;
    if(CookingPresentation)CookingPresentation->Update(bActive);
    bActive=bActive&&IsProvidingWarmth()&&GetNetMode()!=NM_DedicatedServer&&FlameSystem!=nullptr;
    if(!bActive)
    {
        if(Flame){Flame->DeactivateImmediate();Flame->DestroyComponent();Flame=nullptr;}
        if(FireLight){FireLight->DestroyComponent();FireLight=nullptr;}
        return;
    }
    if (!FireLight)
    {
        FireLight=NewObject<UPointLightComponent>(this,NAME_None,RF_Transient);
        FireLight->SetupAttachment(GetRootComponent());
        FireLight->SetMobility(EComponentMobility::Movable);
        FireLight->SetRelativeLocation(FVector(0,0,55));
        FireLight->SetIntensityUnits(ELightUnits::Lumens);
        FireLight->SetIntensity(350.f);
        FireLight->SetLightColor(FLinearColor(1.f,.60f,.26f));
        FireLight->SetAttenuationRadius(500.f);
        FireLight->SetSourceRadius(12.f);
        FireLight->SetCastShadows(false);
        FireLight->SetVolumetricScatteringIntensity(.08f);
        FireLight->RegisterComponent();
    }

    const FVector Center = GetActorTransform().TransformPosition(FVector(0,0,20));
    auto* Fluid = GetWorld()->GetSubsystem<UFluidPresentationSubsystem>();
    const auto Detail = Fluid ? Fluid->FireViews.Classify(*GetWorld(), Center, 130.f, 50.f,
        1600.f, 3500.f, Flame, bFullFlame) : EFireParticleDetail::Full;
    if (Detail == EFireParticleDetail::Off)
    {
        if (Flame && Flame->IsActive()) Flame->DeactivateImmediate();
        return;
    }
    if (!Flame)
    {
        Flame=NewObject<UNiagaraComponent>(this,NAME_None,RF_Transient);
        Flame->SetupAttachment(GetRootComponent());
        Flame->SetAutoActivate(false);
        Flame->SetAutoDestroy(false);
        Flame->SetAsset(FlameSystem);
        Flame->SetRelativeLocation(FVector(0,0,20));
        Flame->SetRelativeScale3D(FVector(1.0f));
        Flame->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Flame->SetCanEverAffectNavigation(false);
        Flame->SetCastShadow(false);
        Flame->bAffectDistanceFieldLighting=false;
        Flame->RegisterComponent();
        bFullFlame = true;
    }
    if (bFullFlame != (Detail == EFireParticleDetail::Full))
    {
        bFullFlame = Detail == EFireParticleDetail::Full;
        Flame->SetEmitterEnable(TEXT("Smoke"), bFullFlame);
        Flame->SetEmitterEnable(TEXT("Sparks"), bFullFlame);
    }
    if (!Flame->IsActive()) Flame->Activate(true);
}
