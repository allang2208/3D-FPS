#include "StormCloudComponent.h"
#include "FPSWeatherManager.h"
#include "WeatherViewEffectsComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/MeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"

namespace
{
void SetStormLightIntensity(ULightComponentBase* Light,float Value)
{
    if(auto* Sun=Cast<UDirectionalLightComponent>(Light))Sun->SetIntensity(Value);
    else if(auto* Sky=Cast<USkyLightComponent>(Light))Sky->SetIntensity(Value);
}
}

UStormCloudComponent::UStormCloudComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PostUpdateWork;
    FallbackCloudMaterial=TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst.m_SimpleVolumetricCloud_Inst")));
}

void UStormCloudComponent::BeginPlay()
{
    Super::BeginPlay();
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    SetComponentTickEnabled(Map==TEXT("DayNight_Lighting")||Map==TEXT("L_Normandy_FPS_Test")||Map==TEXT("L_MilitaryTrench_FPS_Test")||Map==TEXT("L_TemperateHills_Initial"));
}

void UStormCloudComponent::Discover()
{
    for(TActorIterator<AActor> It(GetWorld());It;++It)
    {
        if(*It==GetOwner())continue;
        // The blueprint retains ownership of time, light rotation and its baseline.
        if(It->GetClass()->GetName().Contains(TEXT("FPS_DayNightManager"))) AddTickPrerequisiteActor(*It);
        if(!Cloud.IsValid()) for(auto* C:TInlineComponentArray<UVolumetricCloudComponent*>(*It)) {Cloud=C;break;}
        for(auto* C:TInlineComponentArray<ULightComponentBase*>(*It))
            if((Cast<UDirectionalLightComponent>(C)||Cast<USkyLightComponent>(C)) && !Lights.Contains(C))
            {
                FLightState S;S.Base=C->Intensity;
                if(auto* Sun=Cast<UDirectionalLightComponent>(C))S.Disk=Sun->AtmosphereSunDiskColorScale;
                Lights.Add(C,S);
            }
        if(!It->GetClass()->GetName().Contains(TEXT("FPS_DayNightManager")))continue;
        for(auto* M:TInlineComponentArray<UMeshComponent*>(*It))
        {
            if(SkyMeshes.ContainsByPredicate([M](const FStormSkyMesh& S){return S.Mesh==M;}))continue;
            float V=0;
            if(M->GetMaterial(0)&&M->GetMaterial(0)->GetScalarParameterValue(FMaterialParameterInfo(TEXT("Sky Intensity")),V))
            {FStormSkyMesh S;S.Mesh=M;S.Original=M->GetMaterial(0);S.Brightness=V;SkyMeshes.Add(S);}
        }
    }
    if(!Cloud.IsValid() && Blend>0)
    {
        auto* C=NewObject<UVolumetricCloudComponent>(GetOwner(),TEXT("WeatherStormCloudLayer"));
        C->SetMaterial(FallbackCloudMaterial.LoadSynchronous());
        C->SetVisibility(false);
        C->SetLayerBottomAltitude(2);C->SetLayerHeight(2);
        C->SetViewSampleCountScale(.7f);C->SetShadowViewSampleCountScale(.5f);
        C->RegisterComponent();Cloud=C;bCreatedCloud=true;
    }
    if(Cloud.IsValid()&&!CloudMaterial)
    {
        auto* C=Cloud.Get();OriginalMaterial=C->GetMaterial();
        if(!OriginalMaterial)return;
        bOriginalVisible=C->IsVisible();OriginalBottom=C->LayerBottomAltitude;OriginalHeight=C->LayerHeight;OriginalOcclusion=C->SkyLightCloudBottomOcclusion;
        CloudMaterial=UMaterialInstanceDynamic::Create(OriginalMaterial,this);
        OriginalMaterial->GetScalarParameterValue(FMaterialParameterInfo(TEXT("Cloud_GlobalCoverage")),Coverage);
        OriginalMaterial->GetScalarParameterValue(FMaterialParameterInfo(TEXT("Cloud_GlobalDensity")),Density);
        OriginalMaterial->GetScalarParameterValue(FMaterialParameterInfo(TEXT("StormClouds")),Storm);
        OriginalMaterial->GetVectorParameterValue(FMaterialParameterInfo(TEXT("Cloud_AlbedoColor")),Albedo);
        OriginalMaterial->GetVectorParameterValue(FMaterialParameterInfo(TEXT("Layout_GlobalTexturePlacement")),LayoutPlacement);
        UE_LOG(LogTemp,Display,TEXT("StormClouds: bound %s material=%s created=%d"),*C->GetPathName(),*OriginalMaterial->GetPathName(),bCreatedCloud);
    }
}

void UStormCloudComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    auto* Weather=Cast<AFPSWeatherManager>(GetOwner());if(!Weather)return;
    float Target=0.f;
    switch(Weather->CurrentState)
    {
        case EFPSWeatherState::Cloudy: Target=.30f;break;
        case EFPSWeatherState::LightRain: Target=.52f;break;
        case EFPSWeatherState::Rain: Target=.76f;break;
        case EFPSWeatherState::Storm: Target=1.f;break;
        default:break;
    }
    // Integrate wind displacement; multiplying world time by a changing wind
    // would make cloud patterns jump when a gust changes direction.
    const FVector Wind=Weather->GetWeatherWind();
    WindOffset+=FVector2D(Wind.X,Wind.Y)*Delta/18000000.f;
    Blend=FMath::FInterpConstantTo(Blend,Target,Delta,1.f/FMath::Max(.1f,Weather->TransitionSeconds));
    DiscoveryTime-=Delta;
    if(DiscoveryTime<=0 || (Blend>0&&!CloudMaterial)){Discover();DiscoveryTime=1;}
    if(Blend<=0){if(bOverride)Restore();return;}
    bOverride=true;
    if(auto* C=Cloud.Get();C&&CloudMaterial)
    {
        C->SetMaterial(CloudMaterial);C->SetVisibility(true);
        C->SetLayerBottomAltitude(FMath::Lerp(OriginalBottom,1.55f,Blend));
        C->SetLayerHeight(FMath::Lerp(OriginalHeight,1.1f,Blend));
        C->SetSkyLightCloudBottomOcclusion(FMath::Lerp(OriginalOcclusion,.22f,Blend));
        CloudMaterial->SetScalarParameterValue(TEXT("Cloud_GlobalCoverage"),FMath::Lerp(bOriginalVisible?Coverage:-.35f,.045f,Blend));
        CloudMaterial->SetScalarParameterValue(TEXT("Cloud_GlobalDensity"),FMath::Lerp(bOriginalVisible?Density:0.f,0.f,Blend));
        CloudMaterial->SetScalarParameterValue(TEXT("StormClouds"),FMath::Lerp(Storm,.22f,Blend));
        CloudMaterial->SetVectorParameterValue(TEXT("Cloud_AlbedoColor"),FMath::Lerp(Albedo,FLinearColor(.92f,.94f,.96f,Albedo.A),Blend));
        CloudMaterial->SetVectorParameterValue(TEXT("Storm_AlbedoColor"),FLinearColor(.58f,.62f,.67f,.333333f));
        CloudMaterial->SetVectorParameterValue(TEXT("Layout_WindControls"),WindControls);
        CloudMaterial->SetVectorParameterValue(TEXT("Layout_GlobalTexturePlacement"),LayoutPlacement+FLinearColor(WindOffset.X,WindOffset.Y,0.f,0.f));
        // Lightning remains owned by the weather manager, not a second material timer.
        CloudMaterial->SetVectorParameterValue(TEXT("Storm_LightningColor"),FLinearColor::Black);
    }
    for(auto& S:SkyMeshes) if(auto* M=S.Mesh.Get())
    {
        if(M->GetMaterial(0)!=S.Dynamic)
        {
            auto* Current=M->GetMaterial(0);if(!Current)continue;
            if(Current!=S.Original||!S.Dynamic)
            {
                S.Original=Current;
                S.Original->GetScalarParameterValue(FMaterialParameterInfo(TEXT("Sky Intensity")),S.Brightness);
                UMaterialInterface* Source=S.Original;
                if(auto* Assets=Weather->GetPresentationAssets())
                    for(UMaterialInterface* Candidate=Source;Candidate;)
                    {
                        if(auto* Replacement=Assets->SkyMaterials.Find(Candidate->GetPathName())){Source=*Replacement;break;}
                        if(auto* Instance=Cast<UMaterialInstance>(Candidate))Candidate=Instance->Parent;
                        else break;
                    }
                S.Dynamic=UMaterialInstanceDynamic::Create(Source,this);
                S.Dynamic->CopyMaterialUniformParameters(S.Original);
                UE_LOG(LogTemp,Display,TEXT("WeatherSky: %s -> %s"),*S.Original->GetPathName(),*Source->GetPathName());
            }
            M->SetMaterial(0,S.Dynamic);
        }
        if(S.Dynamic)
        {
            // Blend the authored HDRI into atmospheric sky instead of multiplying
            // an opaque skydome to black beneath the moving volume clouds.
            S.Dynamic->SetScalarParameterValue(TEXT("Sky Intensity"),S.Brightness);
            S.Dynamic->SetScalarParameterValue(TEXT("WeatherSkyBlend"),Blend);
            const float Day=FMath::Clamp(FMath::Sin((Weather->NormalizedDayTime-.25f)*2.f*PI)*3.f+.1f,0.f,1.f);
            S.Dynamic->SetScalarParameterValue(TEXT("WeatherSkyDaylight"),Day);
        }
    }
    for(auto& Pair:Lights) if(auto* L=Pair.Key.Get())
    {
        auto& S=Pair.Value;
        // A fresh value from the clock is the baseline; never compound our own value.
        if(!FMath::IsNearlyEqual(L->Intensity,S.Applied,1.e-5f))S.Base=L->Intensity;
        S.Applied=S.Base*FMath::Lerp(1.f,Cast<UDirectionalLightComponent>(L)?.25f:.72f,Blend);
        SetStormLightIntensity(L,S.Applied);
        if(auto* Sun=Cast<UDirectionalLightComponent>(L))Sun->SetAtmosphereSunDiskColorScale(S.Disk*FMath::Lerp(1.f,.005f,Blend));
    }
}

void UStormCloudComponent::Restore()
{
    if(auto* C=Cloud.Get())
    { C->SetMaterial(OriginalMaterial);C->SetLayerBottomAltitude(OriginalBottom);C->SetLayerHeight(OriginalHeight);C->SetSkyLightCloudBottomOcclusion(OriginalOcclusion);C->SetVisibility(bOriginalVisible); }
    for(auto& S:SkyMeshes) if(auto* M=S.Mesh.Get()) if(M->GetMaterial(0)==S.Dynamic)M->SetMaterial(0,S.Original);
    for(auto& P:Lights)if(auto* L=P.Key.Get())
    {if(FMath::IsNearlyEqual(L->Intensity,P.Value.Applied,1.e-5f))SetStormLightIntensity(L,P.Value.Base);P.Value.Applied=-1;if(auto* Sun=Cast<UDirectionalLightComponent>(L))Sun->SetAtmosphereSunDiskColorScale(P.Value.Disk);}
    bOverride=false;
}
void UStormCloudComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    Restore();if(bCreatedCloud&&Cloud.IsValid())Cloud->DestroyComponent();
    Super::EndPlay(Reason);
}
