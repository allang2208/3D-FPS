#include "StormCloudComponent.h"
#include "FPSWeatherManager.h"
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
    SetComponentTickEnabled(Map==TEXT("DayNight_Lighting")||Map==TEXT("L_Normandy_FPS_Test")||Map==TEXT("L_MilitaryTrench_FPS_Test"));
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
        UE_LOG(LogTemp,Display,TEXT("StormClouds: bound %s material=%s created=%d"),*C->GetPathName(),*OriginalMaterial->GetPathName(),bCreatedCloud);
    }
}

void UStormCloudComponent::TickComponent(float Delta,ELevelTick Type,FActorComponentTickFunction* Tick)
{
    Super::TickComponent(Delta,Type,Tick);
    auto* Weather=Cast<AFPSWeatherManager>(GetOwner());if(!Weather)return;
    const float Target=Weather->CurrentState==EFPSWeatherState::Storm?1.f:0.f;
    Blend=FMath::FInterpConstantTo(Blend,Target,Delta,1.f/FMath::Max(.1f,Weather->TransitionSeconds));
    DiscoveryTime-=Delta;
    if(DiscoveryTime<=0 || (Blend>0&&!CloudMaterial)){Discover();DiscoveryTime=1;}
    if(Blend<=0){if(bOverride)Restore();return;}
    bOverride=true;
    if(auto* C=Cloud.Get();C&&CloudMaterial)
    {
        C->SetMaterial(CloudMaterial);C->SetVisibility(true);
        C->SetLayerBottomAltitude(FMath::Lerp(OriginalBottom,1.2f,Blend));
        C->SetLayerHeight(FMath::Lerp(OriginalHeight,.8f,Blend));
        C->SetSkyLightCloudBottomOcclusion(FMath::Lerp(OriginalOcclusion,.3f,Blend));
        CloudMaterial->SetScalarParameterValue(TEXT("Cloud_GlobalCoverage"),FMath::Lerp(bOriginalVisible?Coverage:-1.f,.1f,Blend));
        CloudMaterial->SetScalarParameterValue(TEXT("Cloud_GlobalDensity"),FMath::Lerp(bOriginalVisible?Density:0.f,0.f,Blend));
        CloudMaterial->SetScalarParameterValue(TEXT("StormClouds"),FMath::Lerp(Storm,.3f,Blend));
        CloudMaterial->SetVectorParameterValue(TEXT("Cloud_AlbedoColor"),FMath::Lerp(Albedo,FLinearColor(.75f,.75f,.75f,Albedo.A),Blend));
        CloudMaterial->SetVectorParameterValue(TEXT("Storm_AlbedoColor"),FLinearColor(.4f,.4f,.4f,.333333f));
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
                S.Dynamic=UMaterialInstanceDynamic::Create(S.Original,this);
            }
            M->SetMaterial(0,S.Dynamic);
        }
        if(S.Dynamic)S.Dynamic->SetScalarParameterValue(TEXT("Sky Intensity"),S.Brightness*(1.f-Blend));
    }
    for(auto& Pair:Lights) if(auto* L=Pair.Key.Get())
    {
        auto& S=Pair.Value;
        // A fresh value from the clock is the baseline; never compound our own value.
        if(!FMath::IsNearlyEqual(L->Intensity,S.Applied,1.e-5f))S.Base=L->Intensity;
        S.Applied=S.Base*FMath::Lerp(1.f,Cast<UDirectionalLightComponent>(L)?.25f:.85f,Blend);
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
