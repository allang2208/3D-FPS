#include "DungeonRoomSubsystem.h"
#include "../FPSGAMEPlayerController.h"
#include "../Building/VoxelBuildComponent.h"
#include "Components/SceneComponent.h"
#include "Components/LightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/AudioComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/SkyLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"

void UDungeonRoomSubsystem::RefreshPresentation()
{
    if(GetWorld()->GetNetMode()==NM_DedicatedServer)return;
    auto* PC=Cast<AFPSGAMEPlayerController>(UGameplayStatics::GetPlayerController(GetWorld(),0));
    if(!PC||!PC->IsLocalController())return;
    const bool Dungeon=IsDungeonPawn(PC->GetPawn());
    if(!bPresentationInitialized||bPresentationDungeon!=Dungeon)
    {
        bPresentationInitialized=true;bPresentationDungeon=Dungeon;NextEnvironmentScan=0.;
        PC->RefreshRegionMusic();
        if(Dungeon)if(auto* Build=PC->FindComponentByClass<UVoxelBuildComponent>())Build->SetBuildMode(false);
    }
    UpdateEnvironment(Dungeon);
}

void UDungeonRoomSubsystem::UpdateEnvironment(bool Dungeon)
{
    const double Now=GetWorld()->GetRealTimeSeconds();
    if(Now>=NextEnvironmentScan)
    {
        NextEnvironmentScan=Now+2.;
        auto Register=[this](AActor* Actor)
        {
            if(!IsValid(Actor))return;
            EnvironmentActors.Add(Actor);
            const bool InDungeon=IsDungeonActor(Actor);
            if(auto* PP=Cast<APostProcessVolume>(Actor);PP&&PP->bUnbound)
            {
                if(!EnvironmentVolumes.ContainsByPredicate([PP](const auto& Row){return Row.Volume==PP;}))
                    EnvironmentVolumes.Add({PP,PP->bEnabled!=0,InDungeon});
                return;
            }
            TInlineComponentArray<USceneComponent*> Components(Actor);
            for(auto* Component:Components)
            {
                if(!Component->IsRegistered())continue;
                if(EnvironmentComponents.ContainsByPredicate([Component](const auto& Row){return Row.Component==Component;}))continue;
                // HiddenInGame is local and does not compete with UDS' day/night visibility changes.
                EnvironmentComponents.Add({Component,Component->bHiddenInGame!=0,InDungeon});
                if(auto* PP=Cast<UPostProcessComponent>(Component))EnvironmentPostProcess.Add({PP,PP->bEnabled!=0,InDungeon});
                if(auto* Sound=Cast<UAudioComponent>(Component))EnvironmentAudio.Add({Sound,Sound->VolumeMultiplier,InDungeon});
            }
        };
        // Typed actor iterators avoid scanning every generated mesh/prop on the scheduler.
        for(TActorIterator<ADirectionalLight> It(GetWorld());It;++It)Register(*It);
        for(TActorIterator<ASkyLight> It(GetWorld());It;++It)Register(*It);
        for(TActorIterator<AExponentialHeightFog> It(GetWorld());It;++It)Register(*It);
        for(TActorIterator<ASkyAtmosphere> It(GetWorld());It;++It)Register(*It);
        for(TActorIterator<AVolumetricCloud> It(GetWorld());It;++It)Register(*It);
        for(TActorIterator<APostProcessVolume> It(GetWorld());It;++It)Register(*It);
        // UDS/UDW embed their sky, lights, clouds and rain inside Blueprint actors.
        for(AActor* Actor:GetWorld()->PersistentLevel->Actors)
            if(IsValid(Actor)&&(Actor->GetClass()->GetName().Contains(TEXT("Ultra_Dynamic_Sky"))
                ||Actor->GetClass()->GetName().Contains(TEXT("Ultra_Dynamic_Weather"))))Register(Actor);
        EnvironmentComponents.RemoveAll([](const auto& Row){return !Row.Component.IsValid();});
        EnvironmentVolumes.RemoveAll([](const auto& Row){return !Row.Volume.IsValid();});
        EnvironmentPostProcess.RemoveAll([](const auto& Row){return !Row.Component.IsValid();});
        EnvironmentAudio.RemoveAll([](const auto& Row){return !Row.Component.IsValid();});
        for(auto It=EnvironmentActors.CreateIterator();It;++It)if(!It->IsValid())It.RemoveCurrent();
    }
    for(auto& Row:EnvironmentComponents)if(auto* Component=Row.Component.Get())
    {
        if(Row.Dungeon!=Dungeon)
        {
            if(!Row.Suppressed){Row.Hidden=Component->bHiddenInGame;Row.Suppressed=true;}
            if(!Component->bHiddenInGame)Component->SetHiddenInGame(true,false);
        }
        else if(Row.Suppressed){Component->SetHiddenInGame(Row.Hidden,false);Row.Suppressed=false;}
    }
    for(auto& Row:EnvironmentVolumes)if(auto* Volume=Row.Volume.Get())
    {
        if(Row.Dungeon!=Dungeon){if(!Row.Suppressed)Row.Enabled=Volume->bEnabled;Row.Suppressed=true;Volume->bEnabled=false;}
        else if(Row.Suppressed){Volume->bEnabled=Row.Enabled;Row.Suppressed=false;}
    }
    for(auto& Row:EnvironmentPostProcess)if(auto* PP=Row.Component.Get())
    {
        if(Row.Dungeon!=Dungeon){if(!Row.Suppressed)Row.Enabled=PP->bEnabled;Row.Suppressed=true;PP->bEnabled=false;}
        else if(Row.Suppressed){PP->bEnabled=Row.Enabled;Row.Suppressed=false;}
    }
    for(auto& Row:EnvironmentAudio)if(auto* Sound=Row.Component.Get())
    {
        if(Row.Dungeon!=Dungeon){if(!Row.Suppressed)Row.Volume=Sound->VolumeMultiplier;Row.Suppressed=true;Sound->SetVolumeMultiplier(0.f);}
        else if(Row.Suppressed){Sound->SetVolumeMultiplier(Row.Volume);Row.Suppressed=false;}
    }
}
void UDungeonRoomSubsystem::RestoreEnvironment()
{
    for(const auto& Row:EnvironmentComponents)if(auto* Component=Row.Component.Get();Component&&Row.Suppressed)Component->SetHiddenInGame(Row.Hidden,false);
    for(const auto& Row:EnvironmentVolumes)if(auto* Volume=Row.Volume.Get();Volume&&Row.Suppressed)Volume->bEnabled=Row.Enabled;
    for(const auto& Row:EnvironmentPostProcess)if(auto* PP=Row.Component.Get();PP&&Row.Suppressed)PP->bEnabled=Row.Enabled;
    for(const auto& Row:EnvironmentAudio)if(auto* Sound=Row.Component.Get();Sound&&Row.Suppressed)Sound->SetVolumeMultiplier(Row.Volume);
    EnvironmentComponents.Reset();EnvironmentVolumes.Reset();EnvironmentPostProcess.Reset();EnvironmentAudio.Reset();EnvironmentActors.Reset();
}
