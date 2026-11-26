#include "TemperateHillsWorld.h"
#include "WeatherRainGust.h"
#include "../FPSWeatherManager.h"
#include "DynamicWindParameters.h"
#include "Engine/World.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "Subsystems/WorldSubsystem.h"
#include "UObject/UnrealType.h"

namespace
{
struct FForestCollectionBinding
{
    TWeakObjectPtr<UMaterialParameterCollectionInstance> Instance;
    FLinearColor LastWeather=FLinearColor::Transparent;
    FLinearColor LastWind=FLinearColor::Transparent;
    float LastGrassStrength=-1.f;
    float LastGrassYaw=0.f;

    void Publish(UMaterialParameterCollectionInstance* MPC,const FLinearColor& Weather,const FLinearColor& Wind,
        const float* GrassYaw=nullptr)
    {
        if(!MPC)return;
        const bool Changed=Instance.Get()!=MPC;
        Instance=MPC;
        if(Changed||LastWeather!=Weather)
        {
            MPC->SetVectorParameterValue(TEXT("RainforestWeather"),Weather);
            LastWeather=Weather;
        }
        if(GrassYaw)
        {
            // PN_WindAnimation divides WindDirection by 360, then builds (cos,sin) in world XY.
            // Its existing Pivot Painter path also feeds the trample function its wind offset.
            const float Strength=Wind.B*FMath::Lerp(.76f,1.f,Weather.G);
            if(Changed||FMath::Abs(FMath::FindDeltaAngleDegrees(LastGrassYaw,*GrassYaw))>.1f)
            {
                MPC->SetScalarParameterValue(TEXT("WindDirection"),*GrassYaw);
                LastGrassYaw=*GrassYaw;
            }
            if(Changed||!FMath::IsNearlyEqual(LastGrassStrength,Strength,.001f))
            {
                MPC->SetScalarParameterValue(TEXT("WindStrength"),Strength);
                LastGrassStrength=Strength;
            }
        }
        else if(Changed||!LastWind.Equals(Wind,.001f))
        {
            MPC->SetVectorParameterValue(TEXT("ForestWind"),Wind);
            LastWind=Wind;
        }
    }
};
}

struct FTemperateForestWindState
{
    TWeakObjectPtr<USubsystem> Subsystem;
    TWeakObjectPtr<UFunction> Update;
    TWeakObjectPtr<UMaterialParameterCollection> GrassParameters;
    FForestCollectionBinding Forest,Grass;
    double Yaw=0.;
    float Amplitude=-1.f;
    FLinearColor LastBones=FLinearColor::Transparent;
    double NextBoneRefresh=0.;
    double NextGrassLookup=0.;
};

void ATemperateHillsWorld::TickForestWind(float DeltaSeconds)
{
    ForestWindUpdateLeft-=DeltaSeconds;
    if(ForestWindUpdateLeft>0.f)return;
    const float Elapsed=.1f-ForestWindUpdateLeft;
    ForestWindUpdateLeft=.1f;
    const auto* Weather=SkyWeather.Get();
    if(GetNetMode()==NM_DedicatedServer||!Weather||!Assets)return;
    if(!ForestWindState)ForestWindState=MakeShared<FTemperateForestWindState>();
    auto& State=*ForestWindState;
    UWorld* World=GetWorld();
    const double Now=World->GetTimeSeconds();
    const float Rain=FMath::Clamp(Weather->GetEffectiveRainIntensity(),0.f,1.f);
    const FVector Wind=Weather->GetWeatherWind();
    const double Speed=Wind.Size2D();
    const double TargetYaw=Speed>1.?FMath::Atan2(Wind.Y,Wind.X):State.Yaw;
    const float Gust=Rain>0.f?(WeatherRainGust::Magnitude(float(WeatherRainGust::SampleTime(*World)))-20.f)/115.f:0.f;
    // Clear air has a small baseline bend. Rain adds a shared pulse, with
    // full storm peaks staying inside the existing vegetation wind envelope.
    const float TargetAmplitude=.72f*FMath::Sqrt(FMath::Clamp(float(Speed/632.4555),0.f,1.f))
        +Rain*(.10f+.28f*Gust);
    const bool First=State.Amplitude<0.f;
    State.Yaw=First?TargetYaw:State.Yaw+FMath::FindDeltaAngleRadians(State.Yaw,TargetYaw)*(1.-FMath::Exp(-Elapsed*.8));
    State.Yaw=FMath::UnwindRadians(State.Yaw);
    State.Amplitude=First?TargetAmplitude:FMath::Lerp(State.Amplitude,TargetAmplitude,1.f-FMath::Exp(-Elapsed*2.f));
    const FVector Direction(FMath::Cos(State.Yaw),FMath::Sin(State.Yaw),0.);
    const FLinearColor Flow(Direction.X,Direction.Y,State.Amplitude,0.f);

    // The public 5.8 subsystem header includes a private engine header.
    // Bind its reflected function once for this world and reuse it.
    if(!State.Subsystem.IsValid()||!State.Update.IsValid())
    {
        auto* Class=FindObject<UClass>(nullptr,TEXT("/Script/DynamicWind.DynamicWindSubsystem"));
        auto* Subsystem=Class?World->GetSubsystemBase(Class):nullptr;
        auto* Update=Subsystem?Subsystem->FindFunction(TEXT("UpdateWindParameters")):nullptr;
        auto* Field=Update?CastField<FStructProperty>(Update->FindPropertyByName(TEXT("Parameters"))):nullptr;
        if(Field&&Field->Struct==FDynamicWindParameters::StaticStruct()&&Update->NumParms==1&&Update->ParmsSize==sizeof(FDynamicWindParameters))
        {
            State.Subsystem=Subsystem;
            State.Update=Update;
            State.NextBoneRefresh=0.;
        }
    }
    if(State.Subsystem.IsValid()&&State.Update.IsValid()&&(!State.LastBones.Equals(Flow,.001f)||Now>=State.NextBoneRefresh))
    {
        FDynamicWindParameters Parameters;
        Parameters.WindDirection=Direction;
        Parameters.WindSpeed=24.f; // frequency multiplies absolute shader time; changing it would jump branch phase
        Parameters.WindAmplitude=State.Amplitude;
        State.Subsystem->ProcessEvent(State.Update.Get(),&Parameters);
        State.LastBones=Flow;
        State.NextBoneRefresh=Now+3.; // a recreated render scene can have a fresh provider
    }
    const FLinearColor Wetness(Weather->GetSurfaceWetness(),Rain,0,0);
    if(Assets->ForestWindParameters)
        State.Forest.Publish(World->GetParameterCollectionInstance(Assets->ForestWindParameters),Wetness,Flow);
    if(!State.GrassParameters.IsValid()&&Now>=State.NextGrassLookup)
    {
        State.GrassParameters=FindObject<UMaterialParameterCollection>(nullptr,
            TEXT("/Game/PN_GrassLibrary/Materials/PN_WindParameters.PN_WindParameters"));
        State.NextGrassLookup=Now+1.;
    }
    if(auto* Collection=State.GrassParameters.Get())
    {
        const float GrassYaw=FRotator::ClampAxis(FMath::RadiansToDegrees(State.Yaw));
        State.Grass.Publish(World->GetParameterCollectionInstance(Collection),Wetness,Flow,&GrassYaw);
    }
}
