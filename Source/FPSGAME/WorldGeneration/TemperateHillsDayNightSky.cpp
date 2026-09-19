#include "TemperateHillsWorld.h"
#include "../FPSWeatherManager.h"
#include "../StormCloudComponent.h"
#include "Camera/PlayerCameraManager.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "EngineUtils.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"

void ATemperateHillsWorld::ActivateDayNightSky()
{
    if(DayNightSky||!Assets->DayNightSkyMaterial.IsValid()||!Assets->DayNightSkyMesh.IsValid())return;
    auto* Mesh=Assets->DayNightSkyMesh.Get();
    DayNightSkyMID=UMaterialInstanceDynamic::Create(Assets->DayNightSkyMaterial.Get(),this);
    DayNightSky=NewObject<UStaticMeshComponent>(this,TEXT("HillsDayNightSky"),RF_Transient);
    AddInstanceComponent(DayNightSky);DayNightSky->SetupAttachment(RootComponent);
    DayNightSky->SetMobility(EComponentMobility::Movable);
    DayNightSky->SetStaticMesh(Mesh);DayNightSky->SetMaterial(0,DayNightSkyMID);
    DayNightSky->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    DayNightSky->SetGenerateOverlapEvents(false);DayNightSky->SetCanEverAffectNavigation(false);
    DayNightSky->SetCastShadow(false);DayNightSky->bAffectDistanceFieldLighting=false;
    DayNightSky->bVisibleInRealTimeSkyCaptures=true;
    // A 50 km radius puts this backdrop beyond the hills' 10 km fog cutoff
    // and the existing 2 km cloud layer, including at the horizon.
    DayNightSky->SetAbsolute(true,true,true);
    DayNightSky->SetWorldScale3D(FVector(5000000.0/FMath::Max(1.0,Mesh->GetBounds().BoxExtent.GetMax())));
    DayNightSky->RegisterComponent();
    TickDayNightSky();
    UE_LOG(LogTemp,Display,TEXT("HILLS_SKY HDR day/night material=%s clock=FPSWeatherManager"),*Assets->DayNightSkyMaterial.ToString());
}

void ATemperateHillsWorld::TickDayNightSky()
{
    if(!DayNightSkyMID||!DayNightSky)return;
    if(auto* Camera=UGameplayStatics::GetPlayerCameraManager(this,0))
        DayNightSky->SetWorldLocation(Camera->GetCameraLocation());
    if(!SkyWeather.IsValid())
        for(TActorIterator<AFPSWeatherManager> It(GetWorld());It;++It){SkyWeather=*It;break;}
    auto* Weather=SkyWeather.Get();if(!Weather)return;

    // Weights are derived directly from the existing clock: time jumps, travel
    // and midnight need no second timer or separately saved sky phase.
    const float Hour=FMath::Frac(Weather->NormalizedDayTime)*24.f;
    FLinearColor Weights(0,0,0,1); // RGBA: sunrise, sunshine, sunset, night.
    if(Hour>=4.5f&&Hour<6.f)
    {const float A=FMath::SmoothStep(4.5f,6.f,Hour);Weights=FLinearColor(A,0,0,1-A);}
    else if(Hour>=6.f&&Hour<8.5f)
    {const float A=FMath::SmoothStep(6.f,8.5f,Hour);Weights=FLinearColor(1-A,A,0,0);}
    else if(Hour>=8.5f&&Hour<16.5f)Weights=FLinearColor(0,1,0,0);
    else if(Hour>=16.5f&&Hour<18.f)
    {const float A=FMath::SmoothStep(16.5f,18.f,Hour);Weights=FLinearColor(0,1-A,A,0);}
    else if(Hour>=18.f&&Hour<19.5f)
    {const float A=FMath::SmoothStep(18.f,19.5f,Hour);Weights=FLinearColor(0,0,1-A,A);}
    DayNightSkyMID->SetVectorParameterValue(TEXT("SkyPhaseWeights"),Weights);
    DayNightSkyMID->SetScalarParameterValue(TEXT("SkyExposureCompensation"),Assets->SkyExposureCompensation);
    const double Days=Weather->GetScheduleDay()+double(Weather->NormalizedDayTime);
    const float Rotation=Assets->SkyRotationDegrees+float(FMath::Fmod(Days*Assets->SkyTurnsPerGameDay,1.0)*360.0);
    DayNightSkyMID->SetScalarParameterValue(TEXT("SkyRotationDegrees"),Rotation);
    float StormBlend=0;
    if(auto* Clouds=Weather->FindComponentByClass<UStormCloudComponent>())
        StormBlend=Clouds->GetStormBlend();
    DayNightSkyMID->SetScalarParameterValue(TEXT("WeatherSkyBlend"),StormBlend);
    DayNightSkyMID->SetScalarParameterValue(TEXT("FPS_LightningSkyLuminance"),Weather->GetLightningMaterialLuminance().X);
    DayNightSkyMID->SetScalarParameterValue(TEXT("WeatherSkyDaylight"),
        FMath::Clamp(FMath::Sin((Weather->NormalizedDayTime-.25f)*2.f*PI)*3.f+.1f,0.f,1.f));
}

void ATemperateHillsWorld::EndDayNightSky()
{
    if(DayNightSky){RemoveInstanceComponent(DayNightSky);DayNightSky->DestroyComponent();DayNightSky=nullptr;}
    DayNightSkyMID=nullptr;SkyWeather.Reset();
}
