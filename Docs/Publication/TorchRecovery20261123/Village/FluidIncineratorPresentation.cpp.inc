// Source/FPSGAME/WorldGeneration/FluidIncineratorPresentation.cpp

void UFluidPresentationSubsystem::UpdateIncinerator(FFurnaceSmoke& E,double Now,int32& Alive,float Rain)
{
    auto* Piece=E.Piece.Get();auto* Body=Piece?Piece->Body():nullptr;if(!Body)return;
    // Author model: exhaust (0,+.145,1.80)m, rain hood underside 2.045m.
    // FBX -Y forward / Z up -> imported mesh Y is negated. Emit inside the hood gap,
    // in mesh space, so snapped rotation and the asset's floor offset both apply.
    const FVector Mouth=Body->GetComponentTransform().TransformPosition(FVector(0,-14.5f,202.f));
    const double Remaining=Piece->IncinerationRemaining();
    const double Distance2 = FireViews.NearestDistanceSquared(*GetWorld(), Mouth);
    const bool Burning=Body->IsRegistered()&&Remaining>0.;
    UpdateSmokeView(E, Mouth, 800.f, 2500.f, 5000.f);
    const bool Visible = Burning && E.Detail != EFireParticleDetail::Off;
    const bool bFull = E.Detail == EFireParticleDetail::Full;
    const float Dt=FMath::Clamp(float(Now-E.LastSeen),0.f,.5f);E.LastSeen=Now;

    // Audio admission is independent of smoke allocation/loading, maximum four nearby loops.
    bool Audible=Burning&&Distance2<FMath::Square(1800.f);
    if(!E.IncineratorAudio.IsValid())E.bIncineratorAudible=false;
    if(Audible&&!E.bIncineratorAudible)
    {
        int32 Voices=0;for(const auto& Other:Furnaces)
            if(&Other!=&E&&Other.IncineratorAudio.IsValid()&&Other.IncineratorAudio->IsPlaying())++Voices;
        Audible=Voices<4;
    }
    if(Audible&&!E.IncineratorAudio.IsValid())
    {
        if(IncineratorSound)
        {
            auto* Audio=NewObject<UAudioComponent>(Piece,NAME_None,RF_Transient);
            Piece->AddInstanceComponent(Audio);Audio->SetupAttachment(Body);
            Audio->SetRelativeLocation(FVector(0,0,95));Audio->bAutoActivate=false;Audio->bAutoDestroy=false;
            Audio->bStopWhenOwnerDestroyed=true;Audio->bIsUISound=false;Audio->bAllowSpatialization=true;
            Audio->bOverrideAttenuation=true;
            Audio->AttenuationOverrides.bAttenuate=true;Audio->AttenuationOverrides.bSpatialize=true;
            Audio->AttenuationOverrides.AttenuationShapeExtents=FVector(120,0,0);
            Audio->AttenuationOverrides.FalloffDistance=1600.f;
            Audio->SetSound(IncineratorSound);Audio->RegisterComponent();E.IncineratorAudio=Audio;
        }
        else Audible=false;
    }
    if(auto* Audio=E.IncineratorAudio.Get())
    {
        if(Audible&&!E.bIncineratorAudible)Audio->FadeIn(.25f,.65f,float(8.-Remaining));
        else if(!Audible&&E.bIncineratorAudible)Audio->FadeOut(.55f,0.f);
        E.bIncineratorAudible=Audible;
        if(!Audible&&!Audio->IsPlaying())
        {Piece->RemoveInstanceComponent(Audio);Audio->DestroyComponent();E.IncineratorAudio.Reset();}
    }

    if (E.Detail == EFireParticleDetail::Off)
    {
        if (auto* FX = E.FX.Get(); FX && !Burning)
        {
            Piece->RemoveInstanceComponent(FX);
            FX->DestroyComponent();
            E.FX.Reset();
            --Alive;
        }
        return;
    }

    if(!E.FX.IsValid()&&Visible&&FurnaceAsset)
    {
        if(Alive>=6)
            for(auto& Other:Furnaces)if(Other.FX.IsValid()&&Other.Rate<=0.f&&!Other.FX->IsActive())
            {Other.FX->DestroyComponent();Other.FX.Reset();--Alive;break;}
        if(Alive<6)
        {
            auto* FX=NewObject<UNiagaraComponent>(Piece,NAME_None,RF_Transient);
            Piece->AddInstanceComponent(FX);FX->SetAutoActivate(false);FX->SetAutoDestroy(false);
            FX->SetAsset(FurnaceAsset);FX->SetCastShadow(false);FX->SetCanEverAffectNavigation(false);
            FX->SetWorldLocation(Mouth);FX->SetWorldScale3D(FVector(.72f));FX->RegisterComponent();
            E.FX=FX;E.NextConfigure=0.;++Alive;
        }
    }
    auto* FX=E.FX.Get();if(!FX)return;
    FX->SetWorldLocation(Mouth);
    const float Target = Visible ? (bFull ? 12.f : 6.f) : 0.f;
    E.Rate=FMath::FInterpConstantTo(E.Rate,Target,Dt,Visible?24.f:12.f);
    if(E.Rate<.05f)E.Rate=0.f;
    if(Visible&&Now>=E.NextConfigure)
    {
        ConfigureSmoke(FX,12,false,bFull);E.NextConfigure=Now+2.5;
        for(auto& SmokeEntry:Smoke)if(SmokeEntry.FX.Get()==FX)SmokeEntry.bOwnWind=true;
    }
    FX->SetVariableFloat(TEXT("User.SpawnRate"),E.Rate);
    FX->SetVariableFloat(TEXT("User.Heat"),Burning?1.f:.15f);
    FX->SetVariableFloat(TEXT("User.Ignition"),bFull ? FMath::Clamp(float((8.-Remaining)/1.25),0.f,1.f) : 1.f);
    FX->SetVariableFloat(TEXT("User.Puff"),bFull&&Burning?FMath::Clamp(float(Remaining-7.),0.f,1.f):0.f);
    FX->SetVariableFloat(TEXT("User.L1Gate"),bFull&&Scalability::GetQualityLevels().EffectsQuality>=1?1.f:0.f);
    FX->SetVariableVec3(TEXT("User.Wind"),FX->GetComponentTransform().InverseTransformVector(WindWithGustAt(Mouth)));
    FX->SetVariableFloat(TEXT("User.Rainfall"),Rain);
    if(E.Rate>0.f){if(!FX->IsActive())FX->Activate(true);E.LastFeed=Now;}
    else if(Now-E.LastFeed>3.9)
    {FX->DeactivateImmediate();Piece->RemoveInstanceComponent(FX);FX->DestroyComponent();E.FX.Reset();--Alive;}
}
