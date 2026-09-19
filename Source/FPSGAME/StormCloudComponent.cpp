#include "StormCloudComponent.h"
#include "FPSWeatherManager.h"
#include "WeatherViewEffectsComponent.h"
#include "Components/VolumetricCloudComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/MeshComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/Material.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"

namespace FPSStormCloudLook
{
// Full-storm endpoints. Cloud extinction and sky capture already attenuate the
// scene; retain diffuse fill and a subdued disk instead of blacking them out again.
constexpr float Density = .0065f;
constexpr float Coverage = .012f;
constexpr float StormShape = .12f;
constexpr float LayerHeightKm = 1.f;
constexpr float BottomOcclusion = .06f;
constexpr float DirectLightScale = .55f;
constexpr float SunMoonDiskScale = .65f;
}

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
    FallbackCloudMaterial=TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Weather/Materials/MI_FPSLayeredClouds.MI_FPSLayeredClouds")));
}

void UStormCloudComponent::BeginPlay()
{
    Super::BeginPlay();
    // Upgrade the former profile in existing placed weather actors as well as
    // new actors. Preserve independently authored density overrides.
    if(FMath::IsNearlyEqual(StormCloudDensity,.010f,1.e-6f))StormCloudDensity=FPSStormCloudLook::Density;
    if(FallbackCloudMaterial.ToSoftObjectPath().ToString()==TEXT("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud_Inst.m_SimpleVolumetricCloud_Inst"))
        FallbackCloudMaterial=TSoftObjectPtr<UMaterialInterface>(FSoftObjectPath(TEXT("/Game/Weather/Materials/MI_FPSLayeredClouds.MI_FPSLayeredClouds")));
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    bHillsClouds=Map==TEXT("L_TemperateHills_Initial");
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
        // Existing DayNight_Lighting actors already have an engine cloud layer.
        // A fallback used only when no layer exists never upgrades those actors.
        UMaterialInterface* Source=OriginalMaterial;
        if(OriginalMaterial->GetMaterial()->GetPathName()==TEXT("/Engine/EngineSky/VolumetricClouds/m_SimpleVolumetricCloud.m_SimpleVolumetricCloud"))
            if(auto* Layered=FallbackCloudMaterial.LoadSynchronous())Source=Layered;
        CloudMaterial=UMaterialInstanceDynamic::Create(Source,this);
        float WeatherBlend=0;
        bLayeredClouds=Source->GetScalarParameterValue(FMaterialParameterInfo(TEXT("FPS_WeatherBlend")),WeatherBlend);
        Source->GetScalarParameterValue(FMaterialParameterInfo(TEXT("Layout_CloudGlobalScale")),CloudLayoutScaleKm);
        OriginalMaterial->GetScalarParameterValue(FMaterialParameterInfo(TEXT("Cloud_GlobalCoverage")),Coverage);
        OriginalMaterial->GetScalarParameterValue(FMaterialParameterInfo(TEXT("Cloud_GlobalDensity")),Density);
        OriginalMaterial->GetScalarParameterValue(FMaterialParameterInfo(TEXT("StormClouds")),Storm);
        OriginalMaterial->GetVectorParameterValue(FMaterialParameterInfo(TEXT("Cloud_AlbedoColor")),Albedo);
        OriginalMaterial->GetVectorParameterValue(FMaterialParameterInfo(TEXT("Storm_AlbedoColor")),StormAlbedo);
        OriginalMaterial->GetVectorParameterValue(FMaterialParameterInfo(TEXT("Layout_GlobalTexturePlacement")),LayoutPlacement);
        UE_LOG(LogTemp,Display,TEXT("StormClouds: bound %s material=%s source=%s created=%d authoredDensity=%.5f baselineDensity=%.5f stormDensity=%.5f"),
            *C->GetPathName(),*Source->GetPathName(),*OriginalMaterial->GetPathName(),bCreatedCloud,Density,
            bHillsClouds||Density<=0?CloudDensity:Density,StormCloudDensity);
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
    Blend=FMath::FInterpConstantTo(Blend,Target,Delta,1.f/FMath::Max(.1f,Weather->TransitionSeconds));
    const float WindScale=FMath::Lerp(2.f,FMath::Clamp(StormWindMultiplier,0.f,20.f),Blend);
    WindOffset+=FVector2D(Wind.X,Wind.Y)*Delta*WindScale/(FMath::Max(1.f,CloudLayoutScaleKm)*100000.f);
    // Integrate the noise clock too. Time * a changing speed would jump at
    // weather transitions; this gives continuous, layered billowing instead.
    CloudMotionSeconds+=Delta*FMath::Lerp(1.f,5.f,Blend);
    DiscoveryTime-=Delta;
    if(DiscoveryTime<=0 || (Blend>0&&!CloudMaterial)){Discover();DiscoveryTime=1;}
    if(Blend<=0)
    {
        if(bOverride)Restore();
        // Clear weather keeps a sparse animated baseline, including old hills
        // instances whose saved material still has the former negative coverage.
        if(bHillsClouds||bLayeredClouds)UpdateCloudLayer();
        return;
    }
    bOverride=true;
    UpdateCloudLayer();
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
            S.Dynamic->SetScalarParameterValue(TEXT("FPS_LightningSkyLuminance"),Weather->GetLightningMaterialLuminance().X);
        }
    }
    for(auto& Pair:Lights) if(auto* L=Pair.Key.Get())
    {
        auto& S=Pair.Value;
        // A fresh value from the clock is the baseline; never compound our own value.
        if(!FMath::IsNearlyEqual(L->Intensity,S.Applied,1.e-5f))S.Base=L->Intensity;
        // Keep the clock's sky-light baseline: the cloud layer/capture supplies
        // overcast shading. This also preserves the clock's darker night fill.
        S.Applied=S.Base*FMath::Lerp(1.f,Cast<UDirectionalLightComponent>(L)?FPSStormCloudLook::DirectLightScale:1.f,Blend);
        SetStormLightIntensity(L,S.Applied);
        // Thick cloud can still occlude the disk; thin cloud now retains its
        // natural bright area instead of an extra 99.5% artificial suppression.
        if(auto* Sun=Cast<UDirectionalLightComponent>(L))Sun->SetAtmosphereSunDiskColorScale(S.Disk*FMath::Lerp(1.f,FPSStormCloudLook::SunMoonDiskScale,Blend));
    }
}

void UStormCloudComponent::UpdateCloudLayer()
{
    auto* C=Cloud.Get();if(!C||!CloudMaterial)return;
    // The HDR supplies distant color, not guaranteed cloud coverage. Keep the
    // original clear-weather cloud field visible beneath every sky phase.
    C->SetMaterial(CloudMaterial);C->SetVisibility(true);
    C->SetLayerBottomAltitude(FMath::Lerp(OriginalBottom,1.55f,Blend));
    C->SetLayerHeight(FMath::Lerp(OriginalHeight,FPSStormCloudLook::LayerHeightKm,Blend));
    C->SetSkyLightCloudBottomOcclusion(FMath::Lerp(OriginalOcclusion,FPSStormCloudLook::BottomOcclusion,Blend));
    const float HillsCoverage=Blend<=.3f?FMath::Lerp(ClearCloudCoverage,CloudyCloudCoverage,Blend/.3f):
        FMath::Lerp(CloudyCloudCoverage,FPSStormCloudLook::Coverage,(Blend-.3f)/.7f);
    CloudMaterial->SetScalarParameterValue(TEXT("Cloud_GlobalCoverage"),bHillsClouds?HillsCoverage:FMath::Lerp(bOriginalVisible?Coverage:-.35f,FPSStormCloudLook::Coverage,Blend));
    // This is an extinction multiplier, not the cloud coverage/density bias.
    // The former zero write erased the entire clear-weather density field.
    const float BaseDensity=FMath::Max(.0001f,bHillsClouds||!bOriginalVisible||Density<=0?CloudDensity:Density);
    CloudMaterial->SetScalarParameterValue(TEXT("Cloud_GlobalDensity"),FMath::Lerp(BaseDensity,FMath::Max(.0001f,StormCloudDensity),Blend));
    CloudMaterial->SetScalarParameterValue(TEXT("StormClouds"),FMath::Lerp(Storm,FPSStormCloudLook::StormShape,Blend));
    CloudMaterial->SetScalarParameterValue(TEXT("FPS_WeatherBlend"),Blend);
    CloudMaterial->SetScalarParameterValue(TEXT("FPS_CloudMotionDriven"),1.f);
    CloudMaterial->SetScalarParameterValue(TEXT("FPS_CloudMotionTime"),static_cast<float>(CloudMotionSeconds));
    CloudMaterial->SetVectorParameterValue(TEXT("Cloud_AlbedoColor"),FMath::Lerp(Albedo,FLinearColor(.96f,.97f,.98f,Albedo.A),Blend));
    CloudMaterial->SetVectorParameterValue(TEXT("Storm_AlbedoColor"),FMath::Lerp(StormAlbedo,FLinearColor(.76f,.79f,.82f,StormAlbedo.A),Blend));
    CloudMaterial->SetVectorParameterValue(TEXT("Layout_WindControls"),WindControls);
    CloudMaterial->SetVectorParameterValue(TEXT("Layout_GlobalTexturePlacement"),LayoutPlacement+FLinearColor(WindOffset.X,WindOffset.Y,0.f,0.f));
    // Lightning remains owned by the weather manager, not a second material timer.
    CloudMaterial->SetVectorParameterValue(TEXT("Storm_LightningColor"),FLinearColor::Black);
    if(const auto* Weather=Cast<AFPSWeatherManager>(GetOwner()))
        CloudMaterial->SetScalarParameterValue(TEXT("FPS_LightningCloudLuminance"),Weather->GetLightningMaterialLuminance().Y);
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
