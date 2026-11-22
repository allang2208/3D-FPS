void URiverPilotFXSubsystem::OnWorldBeginPlay(UWorld& InWorld)
{
    Super::OnWorldBeginPlay(InWorld);
    if(InWorld.GetNetMode()==NM_DedicatedServer)return;
    BeginNativeOptics();
    LastBudgetTime=InWorld.GetTimeSeconds();
    SteamLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(SteamTemplate.ToSoftObjectPath(),
        FStreamableDelegate::CreateWeakLambda(this,[this](){PrepareSteamPool();SteamLoad.Reset();}));
    for(ULevel* Level:InWorld.GetLevels())RegisterLevelWater(Level,&InWorld);
    LevelAddedHandle=FWorldDelegates::LevelAddedToWorld.AddUObject(this,&URiverPilotFXSubsystem::RegisterLevelWater);
    FWorldDelegates::LevelRemovedFromWorld.AddUObject(this,&URiverPilotFXSubsystem::UnregisterLevelWater);
    SplashLoad=UAssetManager::GetStreamableManager().RequestAsyncLoad(ImpactTemplate.ToSoftObjectPath(),
        FStreamableDelegate::CreateWeakLambda(this,[this](){PrepareSplashPool(ImpactTemplate.Get());SplashLoad.Reset();}));
}

void URiverPilotFXSubsystem::RegisterLevelWater(ULevel* Level,UWorld* World)
{
    if(World!=GetWorld()||!Level||World->GetNetMode()==NM_DedicatedServer)return;
    // Once at level arrival, never a world scan on fire or Tick.
    for(AActor* Actor:Level->Actors)if(IsValid(Actor))
    {
        RegisterNativeWaterLight(Actor);
        TInlineComponentArray<UStaticMeshComponent*> Meshes(Actor);
        for(auto* Mesh:Meshes)RegisterWaterSurface(Mesh);
    }
}

void URiverPilotFXSubsystem::UnregisterLevelWater(ULevel* Level,UWorld* World)
{
    if(World!=GetWorld())return;
    StaticSurfaces.RemoveAll([Level](const FRegisteredWaterSurface& Surface)
    {
        const auto* Component=Surface.Component.Get();
        const auto* Owner=Component?Component->GetOwner():nullptr;
        return !Level||!Owner||Owner->GetLevel()==Level;
    });
}

void URiverPilotFXSubsystem::Deinitialize()
{
    EndNativeOptics();
    FWorldDelegates::LevelAddedToWorld.Remove(LevelAddedHandle);
    FWorldDelegates::LevelRemovedFromWorld.RemoveAll(this);
    if(SplashLoad){SplashLoad->CancelHandle();SplashLoad.Reset();}
    if(SteamLoad){SteamLoad->CancelHandle();SteamLoad.Reset();}
    for(auto& FX:SteamPool)if(FX)
    {
        FX->DeactivateImmediate();
        if(auto* Owner=FX->GetOwner())Owner->RemoveInstanceComponent(FX);
        FX->DestroyComponent();
    }
    SteamPool.Reset();
    UnbindRiver(nullptr);StaticSurfaces.Reset();
    for(auto& Owner:RippleOwners)Owner.Reset();
    for(auto& FX:SplashPool)if(FX)
    {
        FX->DeactivateImmediate();
        if(auto* Owner=FX->GetOwner())Owner->RemoveInstanceComponent(FX);
        FX->DestroyComponent();
    }
    SplashPool.Reset();Super::Deinitialize();
}
