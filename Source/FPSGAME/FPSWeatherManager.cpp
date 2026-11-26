#include "FPSWeatherManager.h"
#include "WorldGeneration/ForestVillageMap.h"
#include "Dungeons/DungeonRoomSubsystem.h"
#include "FPSUDSBridgeComponent.h"
#include "WeatherSurfaceComponent.h"
#include "WeatherViewEffectsComponent.h"
#include "Net/UnrealNetwork.h"
#include "GameFramework/GameStateBase.h"
#include "WeatherWorldValidation.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/SceneComponent.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "UObject/ConstructorHelpers.h"

namespace FPSWeatherNames
{
    static const FName Wetness(TEXT("WeatherWetness"));
    static const FName Cloudiness(TEXT("WeatherCloudiness"));
}

AFPSWeatherManager::AFPSWeatherManager()
{
    PrimaryActorTick.bCanEverTick = true;
    bReplicates=true;bAlwaysRelevant=true;SetNetUpdateFrequency(2.f);

    SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("WeatherRoot"));
    SetRootComponent(SceneRoot);

    SurfaceEffects = CreateDefaultSubobject<UWeatherSurfaceComponent>(TEXT("RainSurfaces"));
    // Keep the serialized subobject name used by existing maps and Blueprints.
    ViewEffects = CreateDefaultSubobject<UWeatherViewEffectsComponent>(TEXT("WeatherViewEffects"));
    UDSBridge = CreateDefaultSubobject<UFPSUDSBridgeComponent>(TEXT("UDSBridge"));

    static ConstructorHelpers::FObjectFinder<UMaterialParameterCollection> WeatherParametersFinder(
        TEXT("/Game/Weather/Materials/MPC_FPS_Weather.MPC_FPS_Weather"));
    if (WeatherParametersFinder.Succeeded()) WeatherParameters = WeatherParametersFinder.Object;
}

void AFPSWeatherManager::BeginPlay()
{
    Super::BeginPlay();
    if(GetNetMode()!=NM_Client)SetReplicates(true);

    SurfaceEffects->AddTickPrerequisiteActor(this);
    // Maps saved across the UDS migration can have a null ViewEffects reference
    // after the default subobject was renamed. Reuse the owned component first;
    // only create a replacement when the serialized instance has none left.
    if(!IsValid(ViewEffects))
    {
        ViewEffects=FindComponentByClass<UWeatherViewEffectsComponent>();
        if(!IsValid(ViewEffects))
        {
            ViewEffects=NewObject<UWeatherViewEffectsComponent>(this,NAME_None,RF_Transient);
            AddInstanceComponent(ViewEffects);
        }
        UE_LOG(LogTemp,Warning,TEXT("FPSWeatherManager repaired missing ViewEffects on %s"),*GetPathName());
    }
    if(!ViewEffects->IsRegistered())ViewEffects->RegisterComponent();
    if(GetNetMode()!=NM_DedicatedServer)ViewEffects->Initialize();
    else ViewEffects->SetComponentTickEnabled(false);
    const FString Map = UGameplayStatics::GetCurrentLevelName(this, true);
    const bool bTemperateHills = ForestVillageMap::HasVillage(Map);
    if (bTemperateHills)
    {
        // Existing hills maps were authored with the schedule disabled for the
        // vegetation study. Enable gameplay weather without regenerating the map.
        bAutomaticSchedule = true;
    }
    // Start outdoor scenes at 09:00 so first entry is in daylight.
    if (Map == TEXT("L_Normandy_FPS_Test") || Map == TEXT("L_MilitaryTrench_FPS_Test") || bTemperateHills)
    {
        NormalizedDayTime = 0.375f;
        WeatherClockSeconds = NormalizedDayTime * RealSecondsPerGameDay;
    }
    if(HasAuthority())
    {
        RequestState(bAutomaticSchedule ? ResolveScheduledState() : CurrentState);
        UpdateNetworkWeather(0.f);
    }

    UE_LOG(LogTemp, Display,
        TEXT("FPSWeatherManager ready: day=%.0fs state=%d wetness=%s bridge=%s"),
        RealSecondsPerGameDay,
        static_cast<int32>(CurrentState),
        TEXT("surface"),
        UDSBridge ? TEXT("UDS") : TEXT("none"));
    if(GetNetMode()==NM_Client)OnRep_Weather();
}

void AFPSWeatherManager::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    if(GetNetMode()!=NM_Client)
    {
        AdvanceNaturalClock(DeltaSeconds);
    }
    else UpdateNetworkWeather(DeltaSeconds);
    if(GetNetMode()!=NM_DedicatedServer)
    {
        UpdatePlayerFollowing();
        UpdateShelter(DeltaSeconds);
    }
    if (HasAuthority() && CurrentState == EFPSWeatherState::Cloudy) CloudyElapsedSeconds += DeltaSeconds;
    if(GetNetMode()!=NM_Client)UpdateSchedule();

    // Effective rain intensity follows the weather state transition locally;
    // UDS presents the visuals through the bridge, gameplay keeps these values.
    const float Speed = 1.0f / FMath::Max(TransitionSeconds, 0.1f);
    EffectiveRainIntensity = FMath::FInterpTo(EffectiveRainIntensity, TargetRainIntensity, DeltaSeconds, Speed * 5.0f);
    SurfaceEffects->SetRain(EffectiveRainIntensity);
    if(HasAuthority())UpdateNetworkWeather(DeltaSeconds);

    if (WeatherParameters && GetNetMode()!=NM_DedicatedServer)
    {
        if (UMaterialParameterCollectionInstance* Instance = GetWorld()->GetParameterCollectionInstance(WeatherParameters))
        {
            const float Cloudiness = CurrentState == EFPSWeatherState::Clear ? 0.12f :
                CurrentState == EFPSWeatherState::Cloudy ? 0.7f : FMath::Lerp(0.72f, 1.0f, EffectiveRainIntensity);
            Instance->SetScalarParameterValue(FPSWeatherNames::Wetness, GetSurfaceWetness());
            Instance->SetScalarParameterValue(FPSWeatherNames::Cloudiness, Cloudiness);
        }
    }
}

float AFPSWeatherManager::GetSurfaceWetness() const
{
    return SurfaceEffects ? SurfaceEffects->GetWetness() : 0;
}

bool AFPSWeatherManager::SampleActorRain(AActor* Actor,float& ExposedRain) const
{
    return UDSBridge&&UDSBridge->SampleActorRain(Actor,ExposedRain);
}

bool AFPSWeatherManager::IsWeatherPresentationConnected() const
{
    return UDSBridge && UDSBridge->IsWeatherConnected();
}

bool AFPSWeatherManager::IsSkyClockConnected() const
{
    return UDSBridge && UDSBridge->IsClockConnected();
}

bool AFPSWeatherManager::IsSceneDayNightActive() const
{
    return IsSkyClockConnected();
}

void AFPSWeatherManager::AdvanceGameTime(float Hours)
{
    if (!FMath::IsFinite(Hours) || Hours <= 0.0f || !HasAuthority()) return;

    // The manager owns the only clock; UDS presentation follows via the bridge.
    const double Days=double(NormalizedDayTime)+double(Hours)/24.0;
    DaySerial+=FMath::FloorToInt(Days);
    WeatherClockSeconds = FMath::Frac(Days)*RealSecondsPerGameDay;
    NormalizedDayTime = WeatherClockSeconds / RealSecondsPerGameDay;
    UpdateSchedule();NetworkPublishLeft=0.f;UpdateNetworkWeather(0.f);ForceNetUpdate();
    UE_LOG(LogTemp, Display, TEXT("WEATHER_TIME +%.2fh -> %.2f"), Hours, NormalizedDayTime);
}

void AFPSWeatherManager::SetWeatherState(EFPSWeatherState NewState, bool bDisableAutomaticSchedule)
{
    if(GetNetMode()==NM_Client)return;
    if (bDisableAutomaticSchedule)
    {
        bAutomaticSchedule = false;
    }
    RequestState(NewState);
    NetworkPublishLeft=0.f;UpdateNetworkWeather(0.f);ForceNetUpdate();
}

void AFPSWeatherManager::ResumeAutomaticSchedule()
{
    if(GetNetMode()==NM_Client)return;
    bAutomaticSchedule = true;
    RequestState(ResolveScheduledState());
    NetworkPublishLeft=0.f;UpdateNetworkWeather(0.f);ForceNetUpdate();
}

float AFPSWeatherManager::GetRainLeadInRemaining() const
{
    return bRainPending
        ? FMath::Max(0.f, FMath::Max(RainCloudLeadSeconds, TransitionSeconds) - CloudyElapsedSeconds) : 0.f;
}

void AFPSWeatherManager::RequestState(EFPSWeatherState NewState)
{
    const float LeadSeconds = FMath::Max(RainCloudLeadSeconds, TransitionSeconds);
    // A repeated schedule request or a different queued rain intensity does not
    // restart the lead-in. Existing rain can change intensity without stopping.
    if (StateIntensity(NewState) > 0 && TargetRainIntensity <= 0 &&
        (CurrentState != EFPSWeatherState::Cloudy || CloudyElapsedSeconds < LeadSeconds))
    {
        PendingRainState = NewState;
        bRainPending = true;
        ApplyState(EFPSWeatherState::Cloudy);
        return;
    }
    bRainPending = false;
    ApplyState(NewState);
}

void AFPSWeatherManager::ApplyState(EFPSWeatherState NewState)
{
    if (CurrentState == NewState && TargetRainIntensity == StateIntensity(NewState))
    {
        return;
    }

    const EFPSWeatherState Previous = CurrentState;
    if (Previous != NewState) CloudyElapsedSeconds = 0.f;
    CurrentState = NewState;
    TargetRainIntensity = StateIntensity(NewState);
    UE_LOG(LogTemp, Display, TEXT("FPS weather changed: %d -> %d (rain %.2f)"),
        static_cast<int32>(Previous), static_cast<int32>(CurrentState), TargetRainIntensity);
    OnWeatherChanged.Broadcast(Previous, CurrentState);
}

void AFPSWeatherManager::UpdateSchedule()
{
    if (bAutomaticSchedule)
    {
        RequestState(ResolveScheduledState());
    }
    else if (bRainPending)
    {
        RequestState(PendingRainState);
    }
}

EFPSWeatherState AFPSWeatherManager::ResolveScheduledState() const
{
    const int32 Segment = FMath::Clamp(FMath::FloorToInt(NormalizedDayTime * ScheduleSegmentsPerDay), 0, ScheduleSegmentsPerDay - 1);
    return GetScheduledStateAt(DaySerial, Segment);
}

EFPSWeatherState AFPSWeatherManager::GetScheduledStateAt(int32 Day, int32 Segment) const
{
    auto Raw = [this](int32 D, int32 S)
    {
        uint32 Hash = static_cast<uint32>(WeatherSeed) ^ (static_cast<uint32>(D) * 7919u + static_cast<uint32>(S) * 104729u);
        Hash ^= Hash << 13;
        Hash ^= Hash >> 17;
        Hash ^= Hash << 5;
        const float Pick = static_cast<float>(Hash & 0x00FFFFFFu) / static_cast<float>(0x01000000u);
        if (Pick < .35f) return EFPSWeatherState::Clear;
        if (Pick < .60f) return EFPSWeatherState::Cloudy;
        if (Pick < .76f) return EFPSWeatherState::LightRain;
        if (Pick < .92f) return EFPSWeatherState::Rain;
        return EFPSWeatherState::Storm;
    };
    const EFPSWeatherState State = Raw(Day, Segment);
    const int32 NextSegment = (Segment + 1) % ScheduleSegmentsPerDay;
    const int32 NextDay = Day + (NextSegment == 0 ? 1 : 0);
    // Forecast and simulation share a full cloudy segment before an automatic
    // rain spell, including spells starting across midnight.
    if (State == EFPSWeatherState::Clear && StateIntensity(Raw(NextDay, NextSegment)) > 0)
        return EFPSWeatherState::Cloudy;
    return State;
}

float AFPSWeatherManager::StateIntensity(EFPSWeatherState State) const
{
    switch (State)
    {
    case EFPSWeatherState::LightRain: return 0.35f;
    case EFPSWeatherState::Rain: return 0.68f;
    case EFPSWeatherState::Storm: return 1.0f;
    default: return 0.0f;
    }
}

void AFPSWeatherManager::UpdatePlayerFollowing()
{
    if (APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0))
    {
        const FVector NewLocation = Camera->GetCameraLocation() + FVector(0.0, 0.0, 900.0);
        // SetActorLocation runs the full movement pipeline even for identical
        // values; skip it while the camera holds still.
        if (!NewLocation.Equals(GetActorLocation()))
        {
            SetActorLocation(NewLocation);
        }
    }
}

void AFPSWeatherManager::UpdateShelter(float DeltaSeconds)
{
    if(UDungeonRoomSubsystem::IsDungeonPawn(UGameplayStatics::GetPlayerPawn(this,0)))
    {ShelterAmount=ShelterTarget=1.f;return;}
    // Probe at a coarse rate, but integrate the measured exposure every frame.
    ShelterAmount = FMath::Lerp(ShelterAmount, ShelterTarget, 1.f-FMath::Exp(-DeltaSeconds*4.f));
    ShelterCheckAccumulator += DeltaSeconds;
    if (ShelterCheckAccumulator < 0.25f)
    {
        return;
    }
    ShelterCheckAccumulator = 0.0f;

    APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0);
    if (!Camera)
    {
        return;
    }

    const FVector Start = Camera->GetCameraLocation();
    const FVector End = Start + FVector(0.0, 0.0, 3000.0);
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(FPSWeatherShelter), false);
    if (APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0))
    {
        Params.AddIgnoredActor(Pawn);
    }
    const bool bSheltered = GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params);
    ShelterTarget = bSheltered ? 1.0f : 0.0f;
}

void AFPSWeatherManager::AdvanceNaturalClock(float DeltaSeconds)
{
    if(!FMath::IsFinite(DeltaSeconds)||DeltaSeconds<=0.f)return;
    const double Before=NaturalDayProgress;
    const float Previous=NormalizedDayTime;
    const float BeforeSeconds=WeatherClockSeconds;
    const float Advanced=WeatherClockSeconds+DeltaSeconds;
    WeatherClockSeconds=FMath::Fmod(Advanced,RealSecondsPerGameDay);
    NormalizedDayTime=WeatherClockSeconds/RealSecondsPerGameDay;
    if(NormalizedDayTime<Previous)++DaySerial;
    // Follow the same float calendar used by the existing schedule,
    // including its wrap rounding; do not create a competing day clock.
    NaturalDayProgress+=FMath::Max(0.,(double(WeatherClockSeconds)-BeforeSeconds)/RealSecondsPerGameDay
        +FMath::FloorToDouble(double(Advanced)/RealSecondsPerGameDay));
    const double WorldDelta=GetWorld()->GetDeltaSeconds();
    NaturalDayRate=(NaturalDayProgress-Before)/(WorldDelta>0.?WorldDelta:DeltaSeconds);
}

void AFPSWeatherManager::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(AFPSWeatherManager,NetworkWeather);
}
void AFPSWeatherManager::OnRep_Weather()
{
    if(GetNetMode()!=NM_Client||!NetworkWeather.Ready)return;
    bAutomaticSchedule=NetworkWeather.Automatic;WeatherSeed=NetworkWeather.Seed;
    RealSecondsPerGameDay=FMath::Max(1.f,NetworkWeather.DaySeconds);
    TransitionSeconds=FMath::Max(.1f,NetworkWeather.TransitionSeconds);
    RainCloudLeadSeconds=FMath::Max(1.f,NetworkWeather.CloudLeadSeconds);
    ApplyState(NetworkWeather.Weather);PendingRainState=NetworkWeather.Pending;bRainPending=NetworkWeather.RainPending;
    EffectiveRainIntensity=FMath::Clamp(NetworkWeather.RainIntensity,0.f,1.f);
    WeatherWind=NetworkWeather.Wind;
    SurfaceEffects->SetReplicatedWetness(NetworkWeather.SurfaceWetness);
    UpdateNetworkWeather(0.f);
}
void AFPSWeatherManager::UpdateNetworkWeather(float Delta)
{
    if(GetNetMode()!=NM_Client)
    {
        NetworkPublishLeft-=Delta;if(NetworkPublishLeft>0.f)return;NetworkPublishLeft=.5f;
        NetworkWeather.SampledAt=GetWorld()->GetTimeSeconds();NetworkWeather.DayTime=NormalizedDayTime;
        NetworkWeather.Day=DaySerial;NetworkWeather.DaySeconds=RealSecondsPerGameDay;NetworkWeather.Seed=WeatherSeed;
        NetworkWeather.Weather=CurrentState;NetworkWeather.Pending=PendingRainState;
        NetworkWeather.Automatic=bAutomaticSchedule;NetworkWeather.RainPending=bRainPending;NetworkWeather.CloudyElapsed=CloudyElapsedSeconds;
        NetworkWeather.RainIntensity=EffectiveRainIntensity;NetworkWeather.SurfaceWetness=GetSurfaceWetness();
        NetworkWeather.TransitionSeconds=TransitionSeconds;NetworkWeather.CloudLeadSeconds=RainCloudLeadSeconds;
        if(UDSBridge)UDSBridge->ReadGlobalWind(WeatherWind);
        NetworkWeather.Wind=WeatherWind;
        NetworkWeather.Ready=true;
        return;
    }
    if(!NetworkWeather.Ready)return;
    // Clients advance the shared clock from the replicated sample; the UDS
    // presentation on each client follows the local bridge.
    const auto* GS=GetWorld()->GetGameState();const double Now=GS?GS->GetServerWorldTimeSeconds():GetWorld()->GetTimeSeconds();
    const double Elapsed=FMath::Max(0.,Now-NetworkWeather.SampledAt);
    const double Day=NetworkWeather.DayTime+Elapsed/FMath::Max(1.f,NetworkWeather.DaySeconds);
    NormalizedDayTime=FMath::Frac(Day);DaySerial=NetworkWeather.Day+FMath::FloorToInt(Day);
    WeatherClockSeconds=NormalizedDayTime*RealSecondsPerGameDay;CloudyElapsedSeconds=NetworkWeather.CloudyElapsed+Elapsed;
}
void AFPSWeatherManager::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    if (WeatherParameters && GetWorld())
        if (auto* Parameters = GetWorld()->GetParameterCollectionInstance(WeatherParameters))
            Parameters->SetScalarParameterValue(FPSWeatherNames::Cloudiness, 0.f);
    Super::EndPlay(EndPlayReason);
}


