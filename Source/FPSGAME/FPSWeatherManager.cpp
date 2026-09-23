#include "FPSWeatherManager.h"
#include "LightingConflictValidation.h"
#include "RainUpgradeValidation.h"
#include "WeatherWorldValidation.h"
#include "WeatherSurfaceComponent.h"
#include "StormCloudValidation.h"
#include "StormCloudComponent.h"
#include "WeatherViewEffectsComponent.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/AudioComponent.h"
#include "Components/DecalComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SceneComponent.h"
#include "Components/DirectionalLightComponent.h"
#include "Components/SkyLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/RectLightComponent.h"
#include "Engine/SkyLight.h"
#include "Engine/EngineTypes.h"
#include "EngineUtils.h"
#include "GameFramework/Pawn.h"
#include "Kismet/GameplayStatics.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Materials/MaterialParameterCollection.h"
#include "Materials/MaterialParameterCollectionInstance.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"
#include "UObject/UnrealType.h"
#include "UObject/ConstructorHelpers.h"

namespace FPSWeatherNames
{
    static const FName RainIntensity(TEXT("User.RainIntensity"));
    static const FName SpawnRate(TEXT("User.SpawnRate"));
    static const FName Wetness(TEXT("WeatherWetness"));
    static const FName Cloudiness(TEXT("WeatherCloudiness"));
    static const FName Lightning(TEXT("WeatherLightning"));
}

namespace FPSStormLightning
{
    constexpr float AttackSeconds = .05f;

    float RandomSeconds(FRandomStream& Random, const FVector2D& Range, float Minimum)
    {
        const float Low = FMath::Max(Minimum, static_cast<float>(FMath::Min(Range.X, Range.Y)));
        const float High = FMath::Max(Low, static_cast<float>(FMath::Max(Range.X, Range.Y)));
        return Random.FRandRange(Low, High);
    }

    void ConfigureFill(UPointLightComponent* Light)
    {
        // The sky/cloud materials provide the broad flash. This one existing
        // local light only supplies soft nearby surface response (35 m above view).
        Light->SetRelativeLocation(FVector(0.0, 0.0, 2600.0));
        Light->SetIntensityUnits(ELightUnits::Lumens);
        Light->SetUseInverseSquaredFalloff(true);
        Light->SetInverseExposureBlend(0.f);
        Light->SetAttenuationRadius(9000.f);
        Light->SetSourceRadius(250.f);
        Light->SetSoftSourceRadius(350.f);
        Light->SetLightColor(FColor(210, 225, 255));
        Light->SetCastShadows(false);
        Light->SetSpecularScale(.1f);
        Light->SetVolumetricScatteringIntensity(0.f);
        Light->SetIndirectLightingIntensity(0.f);
        Light->SetIntensity(0.f);
        Light->SetVisibility(false);
    }
}

AFPSWeatherManager::AFPSWeatherManager()
{
    PrimaryActorTick.bCanEverTick = true;

    SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("WeatherRoot"));
    SetRootComponent(SceneRoot);

    RainComponent = CreateDefaultSubobject<UNiagaraComponent>(TEXT("CameraRain"));
    RainComponent->SetupAttachment(SceneRoot);
    RainComponent->SetAutoActivate(false);

    MistComponent = CreateDefaultSubobject<UNiagaraComponent>(TEXT("DistantRainMist"));
    MistComponent->SetupAttachment(SceneRoot);
    MistComponent->SetRelativeLocation(FVector(0.0, 0.0, -700.0));
    MistComponent->SetAutoActivate(false);
    RainComponent->SetCastShadow(false);
    MistComponent->SetCastShadow(false);
    SurfaceEffects = CreateDefaultSubobject<UWeatherSurfaceComponent>(TEXT("RainSurfaces"));
    StormClouds = CreateDefaultSubobject<UStormCloudComponent>(TEXT("StormClouds"));
    ViewEffects = CreateDefaultSubobject<UWeatherViewEffectsComponent>(TEXT("WeatherViewEffects"));
    PresentationLibrary=TSoftObjectPtr<UWeatherPresentationAssets>(FSoftObjectPath(
        TEXT("/Game/Weather/RainVisibility/DA_WeatherPresentation.DA_WeatherPresentation")));

    LightRainAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("LightRainAudio"));
    LightRainAudio->SetupAttachment(SceneRoot);
    LightRainAudio->bAutoActivate = false;

    RainAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("RainAudio"));
    RainAudio->SetupAttachment(SceneRoot);
    RainAudio->bAutoActivate = false;

    HeavyRainAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("HeavyRainAudio"));
    HeavyRainAudio->SetupAttachment(SceneRoot);
    HeavyRainAudio->bAutoActivate = false;

    ThunderAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("ThunderAudio"));
    ThunderAudio->SetupAttachment(SceneRoot);
    ThunderAudio->bAutoActivate = false;

    ThunderTailAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("ThunderTailAudio"));
    ThunderTailAudio->SetupAttachment(SceneRoot);
    ThunderTailAudio->bAutoActivate = false;

    LightningLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("LightningFlash"));
    LightningLight->SetupAttachment(SceneRoot);
    FPSStormLightning::ConfigureFill(LightningLight);

    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> RainFinder(
        TEXT("/Game/Weather/VFX/NS_FPS_RainFine.NS_FPS_RainFine"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> SplashFinder(
        TEXT("/Game/Weather/VFX/NS_FPS_SurfaceSplashes.NS_FPS_SurfaceSplashes"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> MistFinder(
        TEXT("/Game/Weather/VFX/NS_FPS_RainMist.NS_FPS_RainMist"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> DripFinder(
        TEXT("/Game/Weather/VFX/NS_FPS_RoofDrips.NS_FPS_RoofDrips"));
    static ConstructorHelpers::FObjectFinder<UMaterialParameterCollection> WeatherParametersFinder(
        TEXT("/Game/Weather/Materials/MPC_FPS_Weather.MPC_FPS_Weather"));
    static ConstructorHelpers::FObjectFinder<USoundBase> LightRainFinder(
        TEXT("/Game/Weather/Audio/S_Rain_Light_Loop.S_Rain_Light_Loop"));
    static ConstructorHelpers::FObjectFinder<USoundBase> RainAudioFinder(
        TEXT("/Game/Weather/Audio/S_Rain_Soft_Loop.S_Rain_Soft_Loop"));
    static ConstructorHelpers::FObjectFinder<USoundBase> HeavyRainFinder(
        TEXT("/Game/Weather/Audio/S_Rain_Patter_Loop.S_Rain_Patter_Loop"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> PuddleMaterialFinder(
        TEXT("/Game/Weather/Materials/M_RainWetSurface.M_RainWetSurface"));
    static ConstructorHelpers::FObjectFinder<USoundBase> ThunderOneFinder(
        TEXT("/Game/Weather/Audio/S_Thunder_I.S_Thunder_I"));
    static ConstructorHelpers::FObjectFinder<USoundBase> ThunderTwoFinder(
        TEXT("/Game/Weather/Audio/S_Thunder_II.S_Thunder_II"));
    static ConstructorHelpers::FObjectFinder<USoundBase> ThunderThreeFinder(
        TEXT("/Game/Weather/Audio/S_Thunder_III.S_Thunder_III"));
    if (RainFinder.Succeeded()) RainSystem = RainFinder.Object;
    if (SplashFinder.Succeeded()) SplashSystem = SplashFinder.Object;
    if (MistFinder.Succeeded()) MistSystem = MistFinder.Object;
    if (DripFinder.Succeeded()) RoofDripSystem = DripFinder.Object;
    if (WeatherParametersFinder.Succeeded()) WeatherParameters = WeatherParametersFinder.Object;
    if (LightRainFinder.Succeeded()) LightRainSound = LightRainFinder.Object;
    if (RainAudioFinder.Succeeded()) RainSound = RainAudioFinder.Object;
    if (HeavyRainFinder.Succeeded()) HeavyRainSound = HeavyRainFinder.Object;
    if (PuddleMaterialFinder.Succeeded()) PuddleDecalMaterial = PuddleMaterialFinder.Object;
    if (ThunderOneFinder.Succeeded()) ThunderSounds.Add(ThunderOneFinder.Object);
    if (ThunderTwoFinder.Succeeded()) ThunderSounds.Add(ThunderTwoFinder.Object);
    if (ThunderThreeFinder.Succeeded()) ThunderSounds.Add(ThunderThreeFinder.Object);
}

void AFPSWeatherManager::BeginPlay()
{
    Super::BeginPlay();
    StormClouds->AddTickPrerequisiteActor(this);
    ViewEffects->AddTickPrerequisiteActor(this);
    PresentationAssets=PresentationLibrary.LoadSynchronous();
    ViewEffects->Initialize(PresentationAssets);
    if (PresentationAssets)
    {
        if (PresentationAssets->Rain) RainSystem = PresentationAssets->Rain;
        if (PresentationAssets->Splashes) SplashSystem = PresentationAssets->Splashes;
        if (PresentationAssets->Mist) MistSystem = PresentationAssets->Mist;
        if (PresentationAssets->Drips) RoofDripSystem = PresentationAssets->Drips;
        if (PresentationAssets->Puddles) PuddleDecalMaterial = PresentationAssets->Puddles;
    }

    WeatherRandom.Initialize(WeatherSeed);
    // Migrate the previous default stored in already-authored weather actors.
    if (FMath::IsNearlyEqual(ThunderVolume, .75f, 1.e-6f)) ThunderVolume = 1.f;
    if (FMath::IsNearlyEqual(LightningHoldSeconds, 1.f, 1.e-6f)) LightningHoldSeconds = .5f;
    // Saved map actors can still reference the old cues. Migrate only those
    // exact stock sounds; leave authored replacement sounds untouched.
    const TCHAR* ThunderVariants[] = { TEXT("I"), TEXT("II"), TEXT("III") };
    for (TObjectPtr<USoundBase>& Sound : ThunderSounds)
    {
        if (!Sound) continue;
        for (const TCHAR* Variant : ThunderVariants)
        {
            const FString OldName = FString::Printf(TEXT("CUE_Thunder_Lightning_%s_Without_rain_wind_background_noise_Cue"), Variant);
            const FString OldPath = FString::Printf(TEXT("/Game/Thunder_Sounds/CUE/%s.%s"), *OldName, *OldName);
            if (Sound->GetPathName() != OldPath) continue;
            const FString NewPath = FString::Printf(TEXT("/Game/Weather/Audio/S_Thunder_%s.S_Thunder_%s"), Variant, Variant);
            if (USoundBase* Prepared = LoadObject<USoundBase>(nullptr, *NewPath)) Sound = Prepared;
            break;
        }
    }
    // Apply the presentation profile to previously saved component defaults too.
    FPSStormLightning::ConfigureFill(LightningLight);
    UAudioComponent* ThunderVoices[] = { ThunderAudio, ThunderTailAudio };
    for (UAudioComponent* Voice : ThunderVoices)
    {
        Voice->bAllowSpatialization = false;
        Voice->bOverrideAttenuation = true;
        Voice->AttenuationOverrides.bAttenuate = false;
        Voice->AttenuationOverrides.bSpatialize = false;
        Voice->SetLowPassFilterEnabled(true);
    }
    RainComponent->SetAsset(RainSystem);
    MistComponent->SetAsset(MistSystem);
    SurfaceEffects->Initialize(SplashSystem, RoofDripSystem, PuddleDecalMaterial);
    LightRainAudio->SetSound(LightRainSound);
    RainAudio->SetSound(RainSound);
    HeavyRainAudio->SetSound(HeavyRainSound);
    UpdatePlayerFollowing();
    bSkyClockConnected = TrySynchronizeWithSkyClock();
    const FString Map = UGameplayStatics::GetCurrentLevelName(this, true);
    const bool bTemperateHills = Map == TEXT("L_TemperateHills_Initial");
    if (bTemperateHills)
    {
        // Existing hills maps were authored with the schedule disabled for the
        // vegetation study. Enable gameplay weather without regenerating the map.
        bAutomaticSchedule = true;
    }
    if (!bSkyClockConnected && (Map == TEXT("L_Normandy_FPS_Test") || Map == TEXT("L_MilitaryTrench_FPS_Test") || bTemperateHills))
    {
        // Start outdoor scenes at 09:00 so first entry is in daylight.
        NormalizedDayTime = 0.375f;
        WeatherClockSeconds = NormalizedDayTime * RealSecondsPerGameDay;
    }
    if (bTemperateHills) InitializeHillsLighting();
    RequestState(bAutomaticSchedule ? ResolveScheduledState() : CurrentState);

    UE_LOG(LogTemp, Display,
        TEXT("FPSWeatherManager ready: day=%.0fs state=%d rain=%s splashes=%s puddles=%s rainAudio=%d thunder=%d"),
        RealSecondsPerGameDay,
        static_cast<int32>(CurrentState),
        RainSystem ? TEXT("yes") : TEXT("no"),
        SplashSystem ? TEXT("yes") : TEXT("no"),
        PuddleDecalMaterial ? TEXT("yes") : TEXT("no"),
        static_cast<int32>(LightRainSound != nullptr) + static_cast<int32>(RainSound != nullptr) + static_cast<int32>(HeavyRainSound != nullptr),
        ThunderSounds.Num());
    StartLightingConflictValidation(this);
    StartRainUpgradeValidation(this);
    StartStormCloudValidation(this);
    StartWeatherWorldValidation(this);
}

void AFPSWeatherManager::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    bSkyClockConnected = TrySynchronizeWithSkyClock();
    if (!bSkyClockConnected)
    {
        const float Previous = NormalizedDayTime;
        WeatherClockSeconds = FMath::Fmod(WeatherClockSeconds + DeltaSeconds, RealSecondsPerGameDay);
        NormalizedDayTime = WeatherClockSeconds / RealSecondsPerGameDay;
        if (NormalizedDayTime < Previous)
        {
            ++DaySerial;
        }
    }

    UpdatePlayerFollowing();
    UpdateShelter(DeltaSeconds);
    if (CurrentState == EFPSWeatherState::Cloudy) CloudyElapsedSeconds += DeltaSeconds;
    UpdateSchedule();
    UpdateLightning(DeltaSeconds);
    UpdateEffects(DeltaSeconds);
    UpdateSceneDayNight(DeltaSeconds);

}

float AFPSWeatherManager::GetSurfaceWetness() const
{
    return SurfaceEffects ? SurfaceEffects->GetWetness() : 0;
}

void AFPSWeatherManager::AdvanceGameTime(float Hours)
{
    if (Hours == 0.0f) return;

    // 与 TrySynchronizeWithSkyClock 同一套属性发现规则（类名含 FPS_DayNightManager、属性名含 SunHeight，
    // 0..2400 = 一天）。这里再走一遍是为了不往头文件加新的反射成员。
    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
    {
        AActor* Actor = *It;
        if (!Actor->GetClass()->GetName().Contains(TEXT("FPS_DayNightManager"))) continue;
        for (TFieldIterator<FProperty> PropertyIt(Actor->GetClass()); PropertyIt; ++PropertyIt)
        {
            FProperty* Property = *PropertyIt;
            const FString PropertyName = Property->GetName().Replace(TEXT("_"), TEXT("")).Replace(TEXT(" "), TEXT(""));
            FString DisplayName;
#if WITH_EDITOR
            DisplayName = Property->GetDisplayNameText().ToString().Replace(TEXT(" "), TEXT(""));
#endif
            if (!PropertyName.Contains(TEXT("SunHeight"), ESearchCase::IgnoreCase) &&
                !DisplayName.Contains(TEXT("SunHeight"), ESearchCase::IgnoreCase)) continue;

            const float Advance = Hours / 24.0f * 2400.0f;
            if (FFloatProperty* FloatProperty = CastField<FFloatProperty>(Property))
            {
                const float Units = FloatProperty->GetPropertyValue_InContainer(Actor);
                if (Units < 0.0f) continue;
                const float Advanced = FMath::Fmod(Units + Advance + 2400.0f, 2400.0f);
                FloatProperty->SetPropertyValue_InContainer(Actor, Advanced);
                // 立刻刷新读数；LastSkyTimeUnits 故意不碰，跨午夜的日序仍由同步逻辑自己记一次。
                NormalizedDayTime = Advanced / 2400.0f;
                WeatherClockSeconds = NormalizedDayTime * RealSecondsPerGameDay;
                UE_LOG(LogTemp, Display, TEXT("WEATHER_TIME sky-clock +%.2fh -> %.0f/2400 (%.2f)"), Hours, Advanced, NormalizedDayTime);
                return;
            }
            if (FDoubleProperty* DoubleProperty = CastField<FDoubleProperty>(Property))
            {
                const double Units = DoubleProperty->GetPropertyValue_InContainer(Actor);
                if (Units < 0.0) continue;
                const double Advanced = FMath::Fmod(Units + Advance + 2400.0, 2400.0);
                DoubleProperty->SetPropertyValue_InContainer(Actor, Advanced);
                NormalizedDayTime = static_cast<float>(Advanced) / 2400.0f;
                WeatherClockSeconds = NormalizedDayTime * RealSecondsPerGameDay;
                UE_LOG(LogTemp, Display, TEXT("WEATHER_TIME sky-clock +%.2fh -> %.0f/2400 (%.2f)"), Hours, Advanced, NormalizedDayTime);
                return;
            }
        }
    }

    // 没有天空时钟的关卡：推进内部时钟，日序沿用 Tick 里的回绕判断。
    const float Previous = NormalizedDayTime;
    WeatherClockSeconds = FMath::Fmod(WeatherClockSeconds + Hours / 24.0f * RealSecondsPerGameDay, RealSecondsPerGameDay);
    NormalizedDayTime = WeatherClockSeconds / RealSecondsPerGameDay;
    if (NormalizedDayTime < Previous) ++DaySerial;
    UE_LOG(LogTemp, Display, TEXT("WEATHER_TIME internal +%.2fh -> %.2f"), Hours, NormalizedDayTime);
}

void AFPSWeatherManager::SetWeatherState(EFPSWeatherState NewState, bool bDisableAutomaticSchedule)
{
    if (bDisableAutomaticSchedule)
    {
        bAutomaticSchedule = false;
    }
    RequestState(NewState);
}

void AFPSWeatherManager::ResumeAutomaticSchedule()
{
    bAutomaticSchedule = true;
    RequestState(ResolveScheduledState());
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
    LightningCountdown = FPSStormLightning::RandomSeconds(WeatherRandom,
        NewState == EFPSWeatherState::Storm ? FirstLightningDelaySeconds : LightningIntervalSeconds, .5f);
    if (NewState != EFPSWeatherState::Storm) ResetLightning(true);
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

void AFPSWeatherManager::UpdateEffects(float DeltaSeconds)
{
    const float Speed = 1.0f / FMath::Max(TransitionSeconds, 0.1f);
    const float OutdoorIntensity = FMath::FInterpTo(EffectiveRainIntensity, TargetRainIntensity, DeltaSeconds, Speed * 5.0f);
    EffectiveRainIntensity = OutdoorIntensity;
    const float WindTime = GetWorld()->GetTimeSeconds();
    const float Gust = 1.f + .18f*FMath::Sin(WindTime*.37f) + .09f*FMath::Sin(WindTime*.83f);
    const FVector WindTarget = FVector(1.f,.32f+.12f*FMath::Sin(WindTime*.07f),0.f) * FMath::Lerp(100.f,360.f,OutdoorIntensity)*Gust;
    WeatherWind = FMath::Lerp(WeatherWind,WindTarget,1.f-FMath::Exp(-DeltaSeconds*.8f));
    const int32 Quality = UWeatherSurfaceComponent::GetQuality();
    const float VisibleIntensity = Quality > 0 ? OutdoorIntensity * (1.0f-ShelterAmount) : 0;
    const float AudioShelter = FMath::Lerp(1.0f, 0.25f, ShelterAmount) * ThunderRainMix;

    RainComponent->SetFloatParameter(FPSWeatherNames::RainIntensity, VisibleIntensity);
    RainComponent->SetVariableVec3(TEXT("User.WeatherWind"), WeatherWind);
    MistComponent->SetVariableVec3(TEXT("User.WeatherWind"), WeatherWind*.35f);
    RainComponent->SetFloatParameter(FPSWeatherNames::SpawnRate, VisibleIntensity * (Quality==1?800.0f:Quality==3?2000.0f:1400.0f));
    const float MistRate=Quality>=2?VisibleIntensity*3.0f:0;
    MistComponent->SetFloatParameter(FPSWeatherNames::SpawnRate,MistRate);
    MistComponent->SetFloatParameter(FPSWeatherNames::RainIntensity,VisibleIntensity);
    SurfaceEffects->SetRain(OutdoorIntensity);

    const bool bShouldRun = VisibleIntensity > 0.01f;
    if (bShouldRun && !RainComponent->IsActive()) RainComponent->Activate();
    if (!bShouldRun && RainComponent->IsActive()) RainComponent->Deactivate();
    if (MistRate>.01f && !MistComponent->IsActive()) MistComponent->Activate();
    if (MistRate<=.01f && MistComponent->IsActive()) MistComponent->Deactivate();

    const float LightLayer = FMath::Clamp(1.0f - FMath::Abs(OutdoorIntensity - 0.3f) / 0.35f, 0.0f, 1.0f) * AudioShelter * FMath::Clamp(OutdoorIntensity / 0.1f, 0.0f, 1.0f);
    const float MidLayer = FMath::Clamp(1.0f - FMath::Abs(OutdoorIntensity - 0.65f) / 0.4f, 0.0f, 1.0f) * AudioShelter;
    const float HeavyLayer = FMath::Clamp((OutdoorIntensity - 0.65f) / 0.35f, 0.0f, 1.0f) * AudioShelter;
    UAudioComponent* RainLayers[] = { LightRainAudio, RainAudio, HeavyRainAudio };
    const float Volumes[] = { LightLayer, MidLayer, HeavyLayer };
    for (int32 Index = 0; Index < 3; ++Index)
    {
        RainLayers[Index]->SetVolumeMultiplier(Volumes[Index]);
        if (Volumes[Index] > 0.01f && RainLayers[Index]->Sound && !RainLayers[Index]->IsPlaying()) RainLayers[Index]->Play();
        if (Volumes[Index] <= 0.01f && RainLayers[Index]->IsPlaying()) RainLayers[Index]->Stop();
    }

    if (WeatherParameters)
    {
        if (UMaterialParameterCollectionInstance* Instance = GetWorld()->GetParameterCollectionInstance(WeatherParameters))
        {
            const float Cloudiness = CurrentState == EFPSWeatherState::Clear ? 0.12f :
                CurrentState == EFPSWeatherState::Cloudy ? 0.7f : FMath::Lerp(0.72f, 1.0f, OutdoorIntensity);
            Instance->SetScalarParameterValue(FPSWeatherNames::Wetness, GetSurfaceWetness());
            Instance->SetScalarParameterValue(FPSWeatherNames::Cloudiness, Cloudiness);
            // One continuous world-local value feeds all cloud and sky materials.
            // Hold/idle frames do not upload redundant uniform-buffer updates.
            if (LightningAmount != PublishedLightningAmount)
            {
                Instance->SetScalarParameterValue(FPSWeatherNames::Lightning, LightningAmount);
                PublishedLightningAmount = LightningAmount;
            }
        }
    }
}

FVector2D AFPSWeatherManager::GetLightningMaterialLuminance() const
{
    const float Day = FMath::Clamp(FMath::Sin((NormalizedDayTime - .25f) * 2.f * PI) * 3.f + .1f, 0.f, 1.f);
    // The former sky value (.35) disappears in daylight exposure. Keep night
    // restrained and smoothly raise radiance with the same sky daylight curve.
    return FVector2D(FMath::Lerp(.45f, 8.f, Day), FMath::Lerp(1.2f, 12.f, Day));
}

void AFPSWeatherManager::UpdateLightning(float DeltaSeconds)
{
    UAudioComponent* Voices[] = { ThunderAudio, ThunderTailAudio };
    ThunderRainDuckSeconds = FMath::Max(0.f, ThunderRainDuckSeconds - DeltaSeconds);
    ThunderRainMix = FMath::FInterpTo(ThunderRainMix, ThunderRainDuckSeconds > 0.f ? .35f : 1.f,
        DeltaSeconds, ThunderRainDuckSeconds > 0.f ? 8.f : .7f);
    const float Gain = FMath::Clamp(ThunderVolume, 0.f, 1.f) * FMath::Lerp(1.f, .55f, ShelterAmount);
    if (!FMath::IsNearlyEqual(Gain, LastThunderGain, .01f) ||
        !FMath::IsNearlyEqual(ShelterAmount, LastThunderShelter, .02f))
    {
        for (UAudioComponent* Voice : Voices)
        {
            Voice->SetVolumeMultiplier(Gain);
            Voice->SetLowPassFilterFrequency(FMath::Lerp(18000.f, 4000.f, ShelterAmount));
        }
        LastThunderGain = Gain;
        LastThunderShelter = ShelterAmount;
    }

    // One pending strike and two reusable voices. No timer allocation or sound
    // component creation per strike, and a new cue never interrupts an old tail.
    if (PendingThunderDelay >= 0.f)
    {
        PendingThunderDelay -= DeltaSeconds;
        if (PendingThunderDelay <= 0.f)
        {
            if (CurrentState == EFPSWeatherState::Storm && ThunderSounds.IsValidIndex(PendingThunderSound)
                && PendingThunderVoice != INDEX_NONE)
            {
                UAudioComponent* Voice = Voices[PendingThunderVoice];
                Voice->SetSound(ThunderSounds[PendingThunderSound]);
                Voice->SetPitchMultiplier(WeatherRandom.FRandRange(.97f, 1.03f));
                Voice->Play();
                // Prepared waves begin at the audible onset. Keep rain below
                // the main roll, then release smoothly without muting gameplay.
                ThunderRainDuckSeconds = 6.f;
                LastThunderSound = PendingThunderSound;
                UE_LOG(LogTemp, Display, TEXT("WeatherThunder: sound=%s gain=%.2f voice=%d"),
                    *ThunderSounds[PendingThunderSound]->GetName(), Gain, PendingThunderVoice);
            }
            PendingThunderDelay = -1.f;
            PendingThunderVoice = PendingThunderSound = INDEX_NONE;
        }
    }

    if (LightningFlashElapsed >= 0.f)
    {
        LightningFlashElapsed += DeltaSeconds;
        const float HoldEnd = FPSStormLightning::AttackSeconds + FMath::Max(0.f, LightningHoldSeconds);
        const float End = HoldEnd + FMath::Max(.1f, LightningFadeSeconds);
        float Envelope = 1.f;
        if (LightningFlashElapsed < FPSStormLightning::AttackSeconds)
            Envelope = FMath::SmoothStep(0.f, FPSStormLightning::AttackSeconds, LightningFlashElapsed);
        else if (LightningFlashElapsed > HoldEnd)
            Envelope = 1.f - FMath::SmoothStep(HoldEnd, End, LightningFlashElapsed);
        LightningAmount = LightningPeak * FMath::Clamp(LightningStrength, 0.f, 1.f) * Envelope;
        if (LightningFlashElapsed >= End)
        {
            LightningFlashElapsed = -1.f;
            LightningAmount = 0.f;
        }
    }

    const float Fill = LightningAmount * FMath::Clamp(LightningFillLumens, 0.f, 200000.f)
        * FMath::Square(1.f - ShelterAmount);
    if (Fill != AppliedLightningFill)
    {
        LightningLight->SetIntensity(Fill);
        if ((Fill > .01f) != (AppliedLightningFill > .01f)) LightningLight->SetVisibility(Fill > .01f);
        AppliedLightningFill = Fill;
    }

    if (CurrentState != EFPSWeatherState::Storm) return;
    LightningCountdown -= DeltaSeconds;
    if (LightningCountdown > 0.f || EffectiveRainIntensity < .5f || LightningFlashElapsed >= 0.f || PendingThunderDelay >= 0.f) return;
    const float Delay = FPSStormLightning::RandomSeconds(WeatherRandom, ThunderDelaySeconds, .1f);
    if (!QueueThunder(Delay))
    {
        // Both tails are still playing: defer the entire strike, retaining A/V pairing.
        LightningCountdown = 1.f;
        return;
    }
    LightningFlashElapsed = 0.f;
    LightningPeak = WeatherRandom.FRandRange(.82f, 1.f);
    LightningCountdown = FPSStormLightning::RandomSeconds(WeatherRandom, LightningIntervalSeconds, 3.f);
    UE_LOG(LogTemp, Display, TEXT("WeatherLightning: peak=%.2f thunderDelay=%.2fs next=%.2fs"),
        LightningPeak * LightningStrength, Delay, LightningCountdown);
}

bool AFPSWeatherManager::QueueThunder(float DelaySeconds)
{
    if (ThunderSounds.IsEmpty()) return false;
    const int32 VoiceIndex = !ThunderAudio->IsPlaying() ? 0 : !ThunderTailAudio->IsPlaying() ? 1 : INDEX_NONE;
    if (VoiceIndex == INDEX_NONE) return false;
    int32 SoundIndex;
    if (ThunderSounds.Num() > 1 && ThunderSounds.IsValidIndex(LastThunderSound))
    {
        SoundIndex = WeatherRandom.RandRange(0, ThunderSounds.Num() - 2);
        if (SoundIndex >= LastThunderSound) ++SoundIndex;
    }
    else SoundIndex = WeatherRandom.RandRange(0, ThunderSounds.Num() - 1);
    if (!ThunderSounds[SoundIndex]) return false;
    PendingThunderSound = SoundIndex;
    PendingThunderVoice = VoiceIndex;
    PendingThunderDelay = DelaySeconds;
    return true;
}

void AFPSWeatherManager::ResetLightning(bool bFadeThunder)
{
    PendingThunderDelay = LightningFlashElapsed = -1.f;
    PendingThunderSound = PendingThunderVoice = INDEX_NONE;
    LightningAmount = AppliedLightningFill = 0.f;
    ThunderRainDuckSeconds = 0.f;
    LightningLight->SetIntensity(0.f);
    LightningLight->SetVisibility(false);
    UAudioComponent* Voices[] = { ThunderAudio, ThunderTailAudio };
    for (UAudioComponent* Voice : Voices)
    {
        if (bFadeThunder && Voice->IsPlaying()) Voice->FadeOut(.75f, 0.f);
        else Voice->Stop();
    }
}

void AFPSWeatherManager::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    ResetLightning(false);
    if (WeatherParameters && GetWorld())
        if (auto* Parameters = GetWorld()->GetParameterCollectionInstance(WeatherParameters))
            Parameters->SetScalarParameterValue(FPSWeatherNames::Lightning, 0.f);
    Super::EndPlay(EndPlayReason);
}

void AFPSWeatherManager::InitializeHillsLighting()
{
    // Existing maps lock exposure at EV100 1 for the old vegetation study.
    // Override only exposure in the running hills world, including saved worlds;
    // the weather actor owns this component through travel and EndPlay.
    HillsExposure = NewObject<UPostProcessComponent>(this, TEXT("HillsCanopyExposure"), RF_Transient);
    HillsExposure->SetupAttachment(SceneRoot);
    HillsExposure->bUnbound = true;
    HillsExposure->Priority = 10.0f;
    HillsExposure->BlendWeight = 1.0f;
    FPostProcessSettings& Settings = HillsExposure->Settings;
    Settings.bOverride_AutoExposureMethod = true;
    Settings.AutoExposureMethod = AEM_Histogram;
    Settings.bOverride_AutoExposureMinBrightness = true;
    Settings.bOverride_AutoExposureMaxBrightness = true;
    Settings.AutoExposureMinBrightness = 1.0f - HillsShadeExposureAllowance;
    Settings.AutoExposureMaxBrightness = 1.0f;
    Settings.bOverride_AutoExposureSpeedUp = true;
    Settings.bOverride_AutoExposureSpeedDown = true;
    Settings.AutoExposureSpeedUp = 3.0f;
    Settings.AutoExposureSpeedDown = 1.0f;
    Settings.bOverride_LocalExposureMethod = true;
    Settings.LocalExposureMethod = ELocalExposureMethod::Bilateral;
    Settings.bOverride_LocalExposureShadowContrastScale = true;
    Settings.LocalExposureShadowContrastScale = HillsDayShadowContrast;
    // HDR skies contain isolated bright pixels. Camera lens ghosts turn these
    // into unrelated blue/red spots; hills retain bloom without those ghosts.
    Settings.bOverride_LensFlareIntensity = true;
    Settings.LensFlareIntensity = 0.0f;
    HillsExposure->RegisterComponent();
}

void AFPSWeatherManager::UpdateSceneDayNight(float DeltaSeconds)
{
    // These outdoor scenes have no BP_FPS_DayNightManager. Drive their
    // existing lights only in the running world; shared source sublevels stay intact.
    const FString Map = UGameplayStatics::GetCurrentLevelName(this, true);
    if (bSkyClockConnected || (Map != TEXT("L_Normandy_FPS_Test") && Map != TEXT("L_MilitaryTrench_FPS_Test") && Map != TEXT("L_TemperateHills_Initial"))) return;
    SceneLightingRefresh += DeltaSeconds;
    if (SceneLightingRefresh < 0.1f) return;
    SceneLightingRefresh = 0.0f;
    const float SunHeight = FMath::Sin((NormalizedDayTime - 0.25f) * 2.0f * PI);
    const float Daylight = FMath::SmoothStep(-0.12f, 0.35f, SunHeight);
    const bool bTemperateHills = Map == TEXT("L_TemperateHills_Initial");
    if (HillsExposure)
    {
        // Allow at most 0.75 stop of eye adaptation under a canopy in daylight.
        // Fade that allowance and the extra local shadow lift out at night.
        HillsExposure->Settings.AutoExposureMinBrightness = 1.0f - HillsShadeExposureAllowance * Daylight;
        HillsExposure->Settings.LocalExposureShadowContrastScale = FMath::Lerp(0.8f, HillsDayShadowContrast, Daylight);
    }
    // Cloud component applies the single weather attenuation after the clock.
    // This controller only supplies the unmodified time-of-day baseline.
    for (TActorIterator<AActor> It(GetWorld()); It; ++It)
    {
        AActor* Actor = *It;
        if (Actor == this) continue;
        // Normandy's baked blue sky dome would otherwise remain bright at midnight.
        if (Map == TEXT("L_Normandy_FPS_Test"))
        {
            for (UStaticMeshComponent* Mesh : TInlineComponentArray<UStaticMeshComponent*>(Actor))
            {
                if (Mesh->GetStaticMesh() && Mesh->GetStaticMesh()->GetName().Contains(TEXT("SkySphere")))
                    Mesh->SetVisibility(false);
            }
        }
        for (ULightComponentBase* Light : TInlineComponentArray<ULightComponentBase*>(Actor))
        {
            UDirectionalLightComponent* Sun = Cast<UDirectionalLightComponent>(Light);
            USkyLightComponent* Sky = Cast<USkyLightComponent>(Light);
            URectLightComponent* Fill = Map == TEXT("L_Normandy_FPS_Test") ? Cast<URectLightComponent>(Light) : nullptr;
            if (!Sun && !Sky && !Fill) continue;
            const TWeakObjectPtr<ULightComponentBase> Key(Light);
            if (!SceneLightIntensities.Contains(Key))
            {
                SceneLightIntensities.Add(Key, Light->Intensity);
                SceneLightColors.Add(Key, FLinearColor(Light->LightColor));
                Light->SetMobility(EComponentMobility::Movable);
                if (Sun) Sun->SetAtmosphereSunLight(true);
                if (Sky) Sky->SetRealTimeCaptureEnabled(true);
                UE_LOG(LogTemp, Display, TEXT("WeatherScene: bound %s %s base=%.2f"), *Map, *Light->GetPathName(), Light->Intensity);
            }
            const float Base = SceneLightIntensities[Key];
            if (Sun)
            {
                // Use a dim, cool light on the opposite arc at night. A sky capture
                // alone is black without a light source and leaves these scenes unreadable.
                const bool bNight = SunHeight < 0.0f;
                const float Pitch = -(NormalizedDayTime - 0.25f) * 360.0f + (bNight ? 180.0f : 0.0f);
                Sun->SetWorldRotation(FRotator(Pitch, -35.0f, 0.0f));
                Sun->SetLightColor(bNight ? FLinearColor(0.46f, 0.60f, 1.0f) : SceneLightColors[Key]);
                Sun->SetIntensity(Base * FMath::Abs(SunHeight) * (bNight ? 0.035f : 1.0f));
                bSceneDayNightActive = true;
            }
            if (Sky)
            {
                // Lift diffuse sky illumination without increasing direct sun
                // or adding another shadow-casting light beneath every tree.
                const float CanopyFill = bTemperateHills ? FMath::Lerp(1.0f, HillsDaySkyLightScale, Daylight) : 1.0f;
                Sky->SetIntensity(Base * FMath::Lerp(0.06f, 1.0f, Daylight) * CanopyFill);
            }
            if (Fill) Fill->SetIntensity(Base * FMath::Lerp(0.025f, 1.0f, Daylight));
        }
    }
}

bool AFPSWeatherManager::TrySynchronizeWithSkyClock()
{
    // The clock actor and its SunHeight property are level-static content. Resolve
    // them once; per frame only the weak handles are validated and the value read.
    if (!SkyClockActor.IsValid())
    {
        SkyClockActor.Reset();
        SkyClockProperty.Reset();
        for (TActorIterator<AActor> It(GetWorld()); It; ++It)
        {
            AActor* Actor = *It;
            if (!Actor->GetClass()->GetName().Contains(TEXT("FPS_DayNightManager")))
            {
                continue;
            }

            for (TFieldIterator<FProperty> PropertyIt(Actor->GetClass()); PropertyIt; ++PropertyIt)
            {
                FProperty* Property = *PropertyIt;
                const FString PropertyName = Property->GetName().Replace(TEXT("_"), TEXT("")).Replace(TEXT(" "), TEXT(""));
                FString DisplayName;
#if WITH_EDITOR
                DisplayName = Property->GetDisplayNameText().ToString().Replace(TEXT(" "), TEXT(""));
#endif
                if (!PropertyName.Contains(TEXT("SunHeight"), ESearchCase::IgnoreCase) &&
                    !DisplayName.Contains(TEXT("SunHeight"), ESearchCase::IgnoreCase))
                {
                    continue;
                }

                if (CastField<FFloatProperty>(Property) || CastField<FDoubleProperty>(Property))
                {
                    SkyClockActor = Actor;
                    SkyClockProperty = *PropertyIt;
                    break;
                }
            }
            if (SkyClockActor.IsValid())
            {
                break;
            }
        }
        if (!SkyClockActor.IsValid())
        {
            return false;
        }
    }

    AActor* Actor = SkyClockActor.Get();
    FProperty* Property = SkyClockProperty.Get();
    if (!Actor || !Property)
    {
        SkyClockActor.Reset();
        SkyClockProperty.Reset();
        return false;
    }

    float SkyUnits = -1.0f;
    if (const FFloatProperty* FloatProperty = CastField<FFloatProperty>(Property))
    {
        SkyUnits = FloatProperty->GetPropertyValue_InContainer(Actor);
    }
    else if (const FDoubleProperty* DoubleProperty = CastField<FDoubleProperty>(Property))
    {
        SkyUnits = static_cast<float>(DoubleProperty->GetPropertyValue_InContainer(Actor));
    }
    if (SkyUnits < 0.0f) return false;

    SkyUnits = FMath::Fmod(SkyUnits, 2400.0f);
    if (LastSkyTimeUnits >= 0.0f && SkyUnits + 1200.0f < LastSkyTimeUnits)
    {
        ++DaySerial;
    }
    LastSkyTimeUnits = SkyUnits;
    NormalizedDayTime = SkyUnits / 2400.0f;
    WeatherClockSeconds = NormalizedDayTime * RealSecondsPerGameDay;
    return true;
}
