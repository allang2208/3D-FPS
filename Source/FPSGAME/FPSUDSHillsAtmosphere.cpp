#include "FPSUDSBridgeComponent.h"
#include "WorldGeneration/ForestVillageMap.h"
#include "Components/VolumetricCloudComponent.h"
#include "Components/ExponentialHeightFogComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyAtmosphereComponent.h"
#include "Components/SkyLightComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/ExponentialHeightFog.h"
#include "Engine/Level.h"
#include "Engine/PostProcessVolume.h"
#include "Engine/SkyLight.h"
#include "Engine/World.h"
#include "HAL/IConsoleManager.h"
#include "Kismet/GameplayStatics.h"
#include "UObject/UnrealType.h"

namespace HillsAtmosphere
{
FNumericProperty* Number(AActor* Sky,const TCHAR* Name)
{
    auto* P=CastField<FNumericProperty>(Sky->GetClass()->FindPropertyByName(Name));
    return P&&P->IsFloatingPoint()?P:nullptr;
}
void SetDefaultNumber(AActor* Sky,const TCHAR* Name,double Value)
{
    if(auto* P=Number(Sky,Name))
    {
        void* Address=P->ContainerPtrToValuePtr<void>(Sky);
        const double Default=P->GetFloatingPointPropertyValue(P->ContainerPtrToValuePtr<void>(Sky->GetClass()->GetDefaultObject()));
        if(FMath::IsNearlyEqual(P->GetFloatingPointPropertyValue(Address),Default,.000001))
            P->SetFloatingPointPropertyValue(Address,Value);
    }
}
void ApplyStudyFog(AActor* Sky, UExponentialHeightFogComponent* Active, const UExponentialHeightFogComponent* Study)
{
    // Set the clear-weather inputs that UDS itself uses for each time/weather update.
    auto SetInput=[Sky](const TCHAR* Name, double Value)
    {
        if(auto* P=Number(Sky,Name))
            P->SetFloatingPointPropertyValue(P->ContainerPtrToValuePtr<void>(Sky),Value);
    };
    // The streaming callback may arrive after the sky has already started. Use the
    // authored R3 values until the source is available, including its voxel range.
    const float Start=Study ? Study->StartDistance : 0.f;
    const float Range=Study ? Study->VolumetricFogDistance : 6000.f;
    const float Extinction=Study ? Study->VolumetricFogExtinctionScale : 1.f;
    SetInput(TEXT("Base Fog Density"),Study ? Study->FogDensity : .02f);
    SetInput(TEXT("Base Height Fog Falloff"),Study ? Study->FogHeightFalloff : .2f);
    SetInput(TEXT("Fog Density Daytime Mutliplier"),1.);
    SetInput(TEXT("Min Fog Start Distance"),Start);
    SetInput(TEXT("Max Fog Start Distance"),Start);
    SetInput(TEXT("Volumetric Fog Distance"),Range);
    SetInput(TEXT("Volumetric Fog Extinction"),Extinction);
    Active->SetStartDistance(Start);
    Active->SetVolumetricFogDistance(Range);
    Active->SetVolumetricFogExtinctionScale(Extinction);
    Active->SetVolumetricFogScatteringDistribution(Study ? Study->VolumetricFogScatteringDistribution : .2f);
    Active->SetVolumetricFogStartDistance(Study ? Study->VolumetricFogStartDistance : 0.f);
}
void SetBool(AActor* Sky,const TCHAR* Name,bool Value)
{
    if(auto* P=CastField<FBoolProperty>(Sky->GetClass()->FindPropertyByName(Name)))P->SetPropertyValue_InContainer(Sky,Value);
}

void ReleaseStudyLighting(AActor* Sky)
{
    // The seed-study map predates UDS. Its fixed sun and captured sky must not
    // continue illuminating midnight alongside UDS's sun/moon pair. Only touch
    // the three persistent actors created by build_temperate_hills.py.
    ULevel* Level=Sky->GetWorld()->PersistentLevel;
    auto Release=[Sky](AActor* Actor,USceneComponent* Component,const TCHAR* CustomField)
    {
        if(!Actor||!Component)return;
        if(CustomField)
            if(auto* Property=CastField<FObjectPropertyBase>(Sky->GetClass()->FindPropertyByName(CustomField)))
                if(Property->GetObjectPropertyValue_InContainer(Sky)==Actor)return;
        Component->SetVisibility(false,true);
        Component->SetHiddenInGame(true,true);
        UE_LOG(LogTemp,Display,TEXT("UDSBridge: retired hills study lighting %s"),*Actor->GetName());
    };
    if(auto* Sun=FindObject<ADirectionalLight>(Level,TEXT("DirectionalLight_0")))
        Release(Sun,Sun->FindComponentByClass<UDirectionalLightComponent>(),TEXT("Custom Sun Light Actor"));
    if(auto* Ambient=FindObject<ASkyLight>(Level,TEXT("SkyLight_0")))
        Release(Ambient,Ambient->GetLightComponent(),TEXT("Custom Sky Light Actor"));
    if(auto* Atmosphere=FindObject<ASkyAtmosphere>(Level,TEXT("SkyAtmosphere_0")))
        Release(Atmosphere,Atmosphere->FindComponentByClass<USkyAtmosphereComponent>(),nullptr);
}
}

void UFPSUDSBridgeComponent::ReleaseForestSampleLighting(ULevel* Level)
{
    if(!Level || !Level->GetOutermost()->GetName().EndsWith(TEXT("L_ForestPathForest"))) return;
    auto* Sky=SkyActor.Get();
    if(!Sky) return;
    const auto* Binding=CastField<FObjectPropertyBase>(Sky->GetClass()->FindPropertyByName(TEXT("Height Fog Component")));
    auto* Active=Binding?Cast<UExponentialHeightFogComponent>(Binding->GetObjectPropertyValue_InContainer(Sky)):nullptr;
    if(!Active) return;
    for(AActor* Actor:Level->Actors)
    {
        if(!IsValid(Actor)) continue;
        if(const auto* Study=Cast<AExponentialHeightFog>(Actor))
        {
            auto* Source=Study->GetComponent();
            if(Source && Actor->GetFName()==TEXT("ExponentialHeightFog_0"))
                HillsAtmosphere::ApplyStudyFog(Sky,Active,Source);
            if(Source==Active) continue;
        }
        if(auto* Post=Cast<APostProcessVolume>(Actor))
        {
            if(Post->GetFName()==TEXT("PostProcessVolume_0")) Post->bEnabled=false;
        }
        else if(Actor->IsA<ADirectionalLight>() || Actor->IsA<ASkyLight>() || Actor->IsA<ASkyAtmosphere>() ||
            Actor->IsA<AVolumetricCloud>() || Actor->IsA<AExponentialHeightFog>())
        {
            Actor->SetActorHiddenInGame(true);
            if(auto* Root=Actor->GetRootComponent()) Root->SetVisibility(false,true);
        }
    }
}

void UFPSUDSBridgeComponent::ConfigureHillsAtmosphere()
{
    if(bHillsAtmosphereConfigured)return;
    auto* Sky=SkyActor.Get();
    if(!Sky||!Sky->HasActorBegunPlay())return;
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    if(!ForestVillageMap::HasVillage(Map)) { bHillsAtmosphereConfigured=true; return; }
    if(!ForestVillageMap::Is(GetWorld())) HillsAtmosphere::ReleaseStudyLighting(Sky);

    auto* Custom=CastField<FObjectPropertyBase>(Sky->GetClass()->FindPropertyByName(TEXT("Custom Height Fog Actor")));
    auto* Component=CastField<FObjectPropertyBase>(Sky->GetClass()->FindPropertyByName(TEXT("Height Fog Component")));
    auto* Configure=Sky->FindFunction(TEXT("Configure Height Fog with Feature Toggle"));
    if(!Custom||!Component||!Configure||Configure->NumParms!=0)
    {
        bHillsAtmosphereConfigured=true; // The class has no compatible handoff function.
        UE_LOG(LogTemp,Warning,TEXT("UDSBridge: hills height-fog handoff interface unavailable; retaining native sky settings"));
        return;
    }
    auto* PreviousFog=Cast<UExponentialHeightFogComponent>(Component->GetObjectPropertyValue_InContainer(Sky));
    // This is the persistent actor authored by build_temperate_hills.py. Resolve
    // its stable level identity on each peer; do not pick an arbitrary fog actor
    // from streamed levels, local mist effects or iterator order.
    auto* FogActor=Cast<AExponentialHeightFog>(Custom->GetObjectPropertyValue_InContainer(Sky));
    if(!FogActor)
    {
        FogActor=FindObject<AExponentialHeightFog>(GetWorld()->PersistentLevel,TEXT("ExponentialHeightFog_0"));
        if(FogActor&&FogActor->IsA(Custom->PropertyClass))Custom->SetObjectPropertyValue_InContainer(Sky,FogActor);
    }
    // A restrained clear-weather forest baseline. UDS still owns weather and
    // day/night modulation; explicit authored UDS tuning takes precedence.
    HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Sun Light Intensity"),5.6);
    HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Sky Light Intensity"),.85);
    HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Sun Source Angle Scale"),1.15);
    HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Sun Source Angle Softness"),.65);
    HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Exposure Bias Day"),-.12);
    HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Exposure Bias Dawn/Dusk"),-.18);
    HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Exposure Bias Cloudy"),-.05);
    const bool bForestVillage=ForestVillageMap::Is(GetWorld());
    if(!bForestVillage)
    {
        HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Base Fog Density"),.0058);
        HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Base Height Fog Falloff"),.24);
        HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Fog Density Daytime Mutliplier"),.85);
        HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Max Fog Start Distance"),10000.);
        HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Volumetric Fog Distance"),60000.);
        HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Volumetric Fog Extinction"),.75);
    }
    HillsAtmosphere::SetDefaultNumber(Sky,TEXT("Fog Density Nighttime Multiplier"),1.10);
    HillsAtmosphere::SetBool(Sky,TEXT("Use Volumetric Fog"),true);

    // Release only the legacy seed-study fixed exposure, leaving custom grades
    // alone. UDS then adapts continuously between clearings and shaded woodland.
    if(auto* Post=FindObject<APostProcessVolume>(GetWorld()->PersistentLevel,TEXT("PostProcessVolume_0")))
    {
        auto& S=Post->Settings;
        if(S.bOverride_AutoExposureMinBrightness&&S.bOverride_AutoExposureMaxBrightness
            &&FMath::IsNearlyEqual(S.AutoExposureMinBrightness,1.f)&&FMath::IsNearlyEqual(S.AutoExposureMaxBrightness,1.f))
        {S.bOverride_AutoExposureMinBrightness=false;S.bOverride_AutoExposureMaxBrightness=false;}
    }

    // The native handoff updates Height Fog Component and hides the built-in fog
    // when using a custom actor. Do not call Static Properties - Height Fog:
    // it also writes global rendering CVars, outside this scene-only migration.
    Sky->ProcessEvent(Configure,nullptr);
    auto* Fog=Cast<UExponentialHeightFogComponent>(Component->GetObjectPropertyValue_InContainer(Sky));
    if(!Fog)return;
    bHillsAtmosphereConfigured=true;
    if(PreviousFog&&PreviousFog!=Fog)
    {
        Fog->SetFogInscatteringColor(PreviousFog->FogInscatteringLuminance);
        Fog->SetDirectionalInscatteringColor(PreviousFog->DirectionalInscatteringLuminance);
    }
    Fog->SetVolumetricFog(true);
    if(auto* P=HillsAtmosphere::Number(Sky,TEXT("Volumetric Fog Distance")))
        Fog->SetVolumetricFogDistance(P->GetFloatingPointPropertyValue(P->ContainerPtrToValuePtr<void>(Sky)));
    if(auto* P=HillsAtmosphere::Number(Sky,TEXT("Volumetric Fog Extinction")))
        Fog->SetVolumetricFogExtinctionScale(P->GetFloatingPointPropertyValue(P->ContainerPtrToValuePtr<void>(Sky)));
    Fog->SetFogCutoffDistance(1000000.f);
    Fog->SetVolumetricFogScatteringDistribution(.45f);
    Fog->SetVolumetricFogStartDistance(300.f);
    if(bForestVillage)
    {
        HillsAtmosphere::ApplyStudyFog(Sky,Fog,nullptr);
        for(ULevel* Level:GetWorld()->GetLevels()) ReleaseForestSampleLighting(Level);
    }
    const auto* CVar=IConsoleManager::Get().FindConsoleVariable(TEXT("r.VolumetricFog"));
    HillsAtmosphere::SetBool(Sky,TEXT("Volumetric Fog Active"),Fog->IsVisible()&&(!CVar||CVar->GetBool()));
    if(auto* Atmosphere=Sky->FindComponentByClass<USkyAtmosphereComponent>())Atmosphere->SetAerialPespectiveViewDistanceScale(.95f);
    UE_LOG(LogTemp,Display,TEXT("UDSBridge: hills atmosphere owned by UDS, fog=%s, volumetric distance=%.0f"),
        *Fog->GetPathName(),Fog->VolumetricFogDistance);
}
