#include "FPSUDSBridgeComponent.h"
#include "WorldGeneration/ForestVillageMap.h"
#include "Components/DirectionalLightComponent.h"
#include "FPSWeatherManager.h"
#include "Engine/Level.h"
#include "Engine/World.h"
#include "Components/SceneComponent.h"
#include "GameFramework/Actor.h"
#include "Kismet/GameplayStatics.h"
#include "HAL/IConsoleManager.h"
#include "UObject/StructOnScope.h"
#include "UObject/UnrealType.h"

namespace UDSBridge
{
    constexpr const TCHAR* SkyPath=TEXT("/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Sky.Ultra_Dynamic_Sky_C");
    constexpr const TCHAR* WeatherPath=TEXT("/Game/UltraDynamicSky/Blueprints/Ultra_Dynamic_Weather.Ultra_Dynamic_Weather_C");
    const TCHAR* PresetNames[]={TEXT("Clear_Skies"),TEXT("Cloudy"),TEXT("Rain_Light"),TEXT("Rain"),TEXT("Rain_Thunderstorm")};
    TAutoConsoleVariable<bool> Enabled(TEXT("fps.UDS.Bridge"),true,
        TEXT("Enable the FPS clock and server weather bridge to UDS/UDW. Disabling stops bridge writes and spawning."));

    FProperty* Property(UObject* Object,const TCHAR* Name)
    {
        return Object?Object->GetClass()->FindPropertyByName(FName(Name)):nullptr;
    }
    void SetBool(UObject* Object,const TCHAR* Name,bool Value)
    {
        if(auto* P=CastField<FBoolProperty>(Property(Object,Name)))P->SetPropertyValue_InContainer(Object,Value);
    }
    void SetNumber(UObject* Object,FProperty* Field,double Value)
    {
        if(auto* P=CastField<FNumericProperty>(Field))
        {
            void* Address=P->ContainerPtrToValuePtr<void>(Object);
            if(P->IsFloatingPoint())P->SetFloatingPointPropertyValue(Address,Value);
            else if(P->IsInteger())P->SetIntPropertyValue(Address,static_cast<int64>(Value));
        }
    }
    bool IsActorClass(const AActor* Actor,const TCHAR* Path)
    {
        for(const UClass* Class=Actor->GetClass();Class;Class=Class->GetSuperClass())
            if(Class->GetPathName()==Path)return true;
        return false;
    }
}

UFPSUDSBridgeComponent::UFPSUDSBridgeComponent()
{
    PrimaryComponentTick.bCanEverTick=true;
    PrimaryComponentTick.TickGroup=TG_PrePhysics;
}

bool UFPSUDSBridgeComponent::IsBridgeEnabled()
{
    return UDSBridge::Enabled.GetValueOnGameThread();
}

void UFPSUDSBridgeComponent::BeginPlay()
{
    Super::BeginPlay();
    Weather=Cast<AFPSWeatherManager>(GetOwner());
    if(!Weather.IsValid()){SetComponentTickEnabled(false);return;}
    AddTickPrerequisiteActor(GetOwner());
    const FString Map=UGameplayStatics::GetCurrentLevelName(this,true);
    bAllowAutoSpawn=Map==TEXT("DayNight_Lighting")||Map==TEXT("L_Normandy_FPS_Test")
        ||Map==TEXT("L_MilitaryTrench_FPS_Test")||ForestVillageMap::HasVillage(Map);
    auto* World=GetWorld();
    ActorSpawnedHandle=World->AddOnActorSpawnedHandler(FOnActorSpawned::FDelegate::CreateUObject(this,&ThisClass::RegisterActor));
    LevelAddedHandle=FWorldDelegates::LevelAddedToWorld.AddUObject(this,&ThisClass::RegisterLevel);
    // Read existing level actors once, without loading sky classes into interiors.
    for(ULevel* Level:World->GetLevels())RegisterLevel(Level,World);
    ResolveActors();
    if(!bAllowAutoSpawn&&!SkyActor.IsValid()&&!WeatherActor.IsValid())SetComponentTickEnabled(false);
}

void UFPSUDSBridgeComponent::EndPlay(const EEndPlayReason::Type Reason)
{
    RestoreWeatherAudio();
    if(GetWorld())GetWorld()->RemoveOnActorSpawnedHandler(ActorSpawnedHandle);
    FWorldDelegates::LevelAddedToWorld.Remove(LevelAddedHandle);
    if(auto* Sky=SkyActor.Get())Sky->RemoveTickPrerequisiteComponent(this);
    if(auto* Actor=WeatherActor.Get())Actor->RemoveTickPrerequisiteComponent(this);
    SkyActor.Reset();WeatherActor.Reset();PresetsByState.Reset();ActorWeatherSample=nullptr;
    Super::EndPlay(Reason);
}

void UFPSUDSBridgeComponent::RegisterLevel(ULevel* Level,UWorld* World)
{
    if(!Level||World!=GetWorld())return;
    for(AActor* Actor:Level->Actors)RegisterActor(Actor);
    if(bHillsAtmosphereConfigured && SkyActor.IsValid() && ForestVillageMap::Is(World))
        ReleaseForestSampleLighting(Level);
}

void UFPSUDSBridgeComponent::RegisterActor(AActor* Actor)
{
    if(!IsValid(Actor)||Actor->GetWorld()!=GetWorld()||!IsBridgeEnabled())return;
    if(!SkyActor.IsValid()&&UDSBridge::IsActorClass(Actor,UDSBridge::SkyPath))BindSkyReflection(Actor);
    else if(!WeatherActor.IsValid()&&UDSBridge::IsActorClass(Actor,UDSBridge::WeatherPath))BindWeatherReflection(Actor);
}

void UFPSUDSBridgeComponent::ResolveActors()
{
    // Clients wait for server actors through spawn/level events. Never create a
    // local duplicate while another actor's replicated channel is still arriving.
    if(!Weather.IsValid()||!Weather->HasAuthority()||!bAllowAutoSpawn||!IsBridgeEnabled())return;
    const double Now=GetWorld()->GetTimeSeconds();
    if(Now<ResolveRetryAfter)return;
    ResolveRetryAfter=Now+1.;
    auto Spawn=[this](TObjectPtr<UClass>& Class,const TCHAR* Path,bool IsSky)
    {
        if(!Class)Class=LoadObject<UClass>(nullptr,Path);
        if(!Class)return;
        auto* Actor=GetWorld()->SpawnActorDeferred<AActor>(Class,FTransform::Identity,nullptr,nullptr,
            ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
        if(!Actor)return;
        Actor->SetReplicates(true);Actor->bAlwaysRelevant=true;
        if(IsSky)BindSkyReflection(Actor);else BindWeatherReflection(Actor);
        Actor->FinishSpawning(FTransform::Identity);
        UE_LOG(LogTemp,Display,TEXT("UDSBridge: authority spawned %s"),*Actor->GetName());
    };
    if(!SkyActor.IsValid())Spawn(SkyClass,UDSBridge::SkyPath,true);
    if(!WeatherActor.IsValid())Spawn(WeatherClass,UDSBridge::WeatherPath,false);
}

void UFPSUDSBridgeComponent::BindSkyReflection(AActor* Sky)
{
    if(SkyActor.Get()==Sky)return;
    if(auto* Previous=SkyActor.Get())Previous->RemoveTickPrerequisiteComponent(this);
    SkyActor=Sky;LastDrivenClockUnits=-1.f;bHillsAtmosphereConfigured=false;
    TimeProperty=UDSBridge::Property(Sky,TEXT("Time Of Day"));
    AnimateProperty=UDSBridge::Property(Sky,TEXT("Animate Time Of Day"));
    DaySpeedProperty=UDSBridge::Property(Sky,TEXT("Time Speed"));
    // FPS supplies the smooth replicated clock on every peer; disable UDS'
    // competing periodic clock correction, as well as its independent advance.
    UDSBridge::SetBool(Sky,TEXT("Animate Time Of Day"),false);
    UDSBridge::SetNumber(Sky,DaySpeedProperty.Get(),0.);
    UDSBridge::SetBool(Sky,TEXT("Replicate Time Of Day To Clients"),false);
    if(Weather->HasAuthority()){Sky->SetReplicates(true);Sky->bAlwaysRelevant=true;}
    Sky->AddTickPrerequisiteComponent(this);
    SetComponentTickEnabled(true);
    UE_LOG(LogTemp,Display,TEXT("UDSBridge: sky bound (%s), FPS clock, native clock replication disabled"),*Sky->GetName());
}

void UFPSUDSBridgeComponent::BindWeatherReflection(AActor* Actor)
{
    if(WeatherActor.Get()==Actor)return;
    RestoreWeatherAudio();
    if(auto* Previous=WeatherActor.Get())Previous->RemoveTickPrerequisiteComponent(this);
    WeatherActor=Actor;LastDrivenState=static_cast<EFPSWeatherState>(255);
    bReportedPresentationFailure=false;
    ChangeWeatherFunction.Reset();WeatherPresetParameter.Reset();WeatherTimeParameter.Reset();
    BindActorWeatherQuery(Actor);
    UDSBridge::SetBool(Actor,TEXT("Replicate Lightning Direction"),true);
    if(Weather->HasAuthority())
    {
        Actor->SetReplicates(true);Actor->bAlwaysRelevant=true;
        UDSBridge::SetBool(Actor,TEXT("Begin Play Weather Is Random"),false);
        FProperty* Random=UDSBridge::Property(Actor,TEXT("Random Weather Variation"));
        if(auto* Enum=CastField<FEnumProperty>(Random))
            Enum->GetUnderlyingProperty()->SetIntPropertyValue(Enum->ContainerPtrToValuePtr<void>(Actor),static_cast<uint64>(0));
        else UDSBridge::SetNumber(Actor,Random,0.);
        ChangeWeatherFunction=Actor->FindFunction(TEXT("Change Weather"));
        if(auto* Function=ChangeWeatherFunction.Get())
        {
            int32 Inputs=0;
            for(TFieldIterator<FProperty> It(Function);It;++It)
            {
                FProperty* P=*It;
                if(!P->HasAnyPropertyFlags(CPF_Parm)||P->HasAnyPropertyFlags(CPF_ReturnParm))continue;
                ++Inputs;
                const FString Name=P->GetName().Replace(TEXT("_"),TEXT(" "));
                if(CastField<FObjectPropertyBase>(P)&&Name.Contains(TEXT("new weather type")))WeatherPresetParameter=P;
                if(auto* Numeric=CastField<FNumericProperty>(P);Numeric&&Numeric->IsFloatingPoint()
                    &&Name.Contains(TEXT("time to transition")))WeatherTimeParameter=P;
            }
            if(Inputs!=2||!WeatherPresetParameter.IsValid()||!WeatherTimeParameter.IsValid())
            {
                UE_LOG(LogTemp,Error,TEXT("UDSBridge: unsupported Change Weather signature on %s; not invoking an untyped parameter block"),*Actor->GetName());
                ChangeWeatherFunction.Reset();bReportedPresentationFailure=true;
            }
        }
        CachePresets();
    }
    Actor->AddTickPrerequisiteComponent(this);
    ConfigureWeatherAudio();
    SetComponentTickEnabled(true);
    UE_LOG(LogTemp,Display,TEXT("UDSBridge: weather bound (%s), authority=%d; UDW owns transition/lightning replication"),
        *Actor->GetName(),Weather->HasAuthority()?1:0);
}

void UFPSUDSBridgeComponent::CachePresets()
{
    if(!PresetsByState.IsEmpty())return;
    for(int32 Index=0;Index<UE_ARRAY_COUNT(UDSBridge::PresetNames);++Index)
    {
        const FString Name(UDSBridge::PresetNames[Index]);
        const FString Path=FString::Printf(TEXT("/Game/UltraDynamicSky/Blueprints/Weather_Effects/Weather_Presets/%s.%s"),*Name,*Name);
        if(UObject* Preset=LoadObject<UObject>(nullptr,*Path))PresetsByState.Add(Index,Preset);
        else UE_LOG(LogTemp,Error,TEXT("UDSBridge: required weather preset missing: %s"),*Path);
    }
}

void UFPSUDSBridgeComponent::TickComponent(float DeltaTime,ELevelTick TickType,FActorComponentTickFunction* TickFunction)
{
    Super::TickComponent(DeltaTime,TickType,TickFunction);
    if(!Weather.IsValid()||!IsBridgeEnabled()){RestoreWeatherAudio();return;}
    if(!SkyActor.IsValid()||!WeatherActor.IsValid())ResolveActors();
    if(!bAllowAutoSpawn&&!SkyActor.IsValid()&&!WeatherActor.IsValid()){SetComponentTickEnabled(false);return;}
    if(!Weather->IsWeatherStateReady())return;
    ConfigureHillsAtmosphere();
    ApplyClock();
    if(Weather->HasAuthority())ApplyWeatherState(Weather->CurrentState);
    UpdateWeatherAudio(DeltaTime);
}

void UFPSUDSBridgeComponent::ApplyClock()
{
    auto* Sky=SkyActor.Get();
    if(!Sky||!TimeProperty.IsValid())return;
    const float Units=Weather->NormalizedDayTime*2400.f;
    if(FMath::IsNearlyEqual(Units,LastDrivenClockUnits,.01f))return;
    UDSBridge::SetNumber(Sky,TimeProperty.Get(),Units);LastDrivenClockUnits=Units;
}

void UFPSUDSBridgeComponent::ApplyWeatherState(EFPSWeatherState State)
{
    if(!WeatherActor.IsValid()||!WeatherActor->HasActorBegunPlay()||State==LastDrivenState)return;
    UObject* Preset=PresetsByState.FindRef(static_cast<int32>(State));
    if(CallChangeWeather(Preset,FMath::Max(Weather->TransitionSeconds,1.f)))
    {
        LastDrivenState=State;bReportedPresentationFailure=false;
        UE_LOG(LogTemp,Display,TEXT("UDSBridge: authority weather -> %d, replicated UDW transition"),static_cast<int32>(State));
    }
    else if(!bReportedPresentationFailure)
    {
        bReportedPresentationFailure=true;
        UE_LOG(LogTemp,Error,TEXT("UDSBridge: cannot submit state %d; retaining last UDW state (no direct-property fallback)"),static_cast<int32>(State));
    }
}

bool UFPSUDSBridgeComponent::CallChangeWeather(UObject* Preset,float TransitionSeconds)
{
    auto* Actor=WeatherActor.Get();auto* Function=ChangeWeatherFunction.Get();
    auto* PresetParam=CastField<FObjectPropertyBase>(WeatherPresetParameter.Get());
    auto* TimeParam=CastField<FNumericProperty>(WeatherTimeParameter.Get());
    if(!Actor||!Function||!Preset||!PresetParam||!TimeParam||!Preset->IsA(PresetParam->PropertyClass))return false;
    FStructOnScope Parameters(Function);
    uint8* Data=Parameters.GetStructMemory();
    PresetParam->SetObjectPropertyValue_InContainer(Data,Preset);
    TimeParam->SetFloatingPointPropertyValue(TimeParam->ContainerPtrToValuePtr<void>(Data),TransitionSeconds);
    Actor->ProcessEvent(Function,Data);
    return true;
}

bool UFPSUDSBridgeComponent::ReadGlobalWind(FVector& OutWind) const
{
    auto* Actor=WeatherActor.Get();
    if(!Actor||LastDrivenState==static_cast<EFPSWeatherState>(255))return false;
    auto* StateProperty=CastField<FObjectPropertyBase>(UDSBridge::Property(Actor,TEXT("Global Weather State")));
    auto* State=StateProperty?StateProperty->GetObjectPropertyValue_InContainer(Actor):nullptr;
    if(!State)return false;
    auto Read=[State](const TCHAR* Name,double& Out)
    {
        auto* Field=CastField<FNumericProperty>(UDSBridge::Property(State,Name));
        if(!Field||!Field->IsFloatingPoint())return false;
        Out=Field->GetFloatingPointPropertyValue(Field->ContainerPtrToValuePtr<void>(State));
        return FMath::IsFinite(Out);
    };
    double Intensity=0.,Direction=0.;
    if(!Read(TEXT("Wind Intensity"),Intensity)||!Read(TEXT("Wind Direction"),Direction))return false;
    // Preserve the project's clear-weather speed (length of 120,40) at UDW's
    // intensity 2. Smoke already applies its own world-space wind cap.
    OutWind=FRotator(0.,Direction,0.).Vector()*(FMath::Max(0.,Intensity)*63.2455532034);
    return true;
}


bool UFPSUDSBridgeComponent::ReadSunRays(FVector& Direction) const
{
    auto* Sky=SkyActor.Get();
    if(!Sky)return false;
    for(auto* Sun:TInlineComponentArray<UDirectionalLightComponent*>(Sky))
    {
        if(!Sun->IsVisible()||!Sun->IsUsedAsAtmosphereSunLight()||Sun->GetAtmosphereSunLightIndex()!=0||Sun->Intensity<=0.f)continue;
        Direction=Sun->GetForwardVector();
        return true;
    }
    return false;
}
