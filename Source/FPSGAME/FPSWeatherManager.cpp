#include "FPSWeatherManager.h"
#include "LightingConflictValidation.h"
#include "RainUpgradeValidation.h"
#include "WeatherSurfaceComponent.h"
#include "StormCloudValidation.h"
#include "StormCloudComponent.h"
#include "WeatherViewEffectsComponent.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/AudioComponent.h"
#include "Components/DecalComponent.h"
#include "Components/PointLightComponent.h"
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

    LightningLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("LightningFlash"));
    LightningLight->SetupAttachment(SceneRoot);
    LightningLight->SetIntensity(0.0f);
    LightningLight->SetAttenuationRadius(200000.0f);
    LightningLight->SetLightColor(FColor(190, 215, 255));
    LightningLight->SetCastShadows(false);

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
        TEXT("/Game/Thunder_Sounds/CUE/CUE_Thunder_Lightning_I_Without_rain_wind_background_noise_Cue.CUE_Thunder_Lightning_I_Without_rain_wind_background_noise_Cue"));
    static ConstructorHelpers::FObjectFinder<USoundBase> ThunderTwoFinder(
        TEXT("/Game/Thunder_Sounds/CUE/CUE_Thunder_Lightning_II_Without_rain_wind_background_noise_Cue.CUE_Thunder_Lightning_II_Without_rain_wind_background_noise_Cue"));
    static ConstructorHelpers::FObjectFinder<USoundBase> ThunderThreeFinder(
        TEXT("/Game/Thunder_Sounds/CUE/CUE_Thunder_Lightning_III_Without_rain_wind_background_noise_Cue.CUE_Thunder_Lightning_III_Without_rain_wind_background_noise_Cue"));
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
    RainComponent->SetAsset(RainSystem);
    MistComponent->SetAsset(MistSystem);
    SurfaceEffects->Initialize(SplashSystem, RoofDripSystem, PuddleDecalMaterial);
    LightRainAudio->SetSound(LightRainSound);
    RainAudio->SetSound(RainSound);
    HeavyRainAudio->SetSound(HeavyRainSound);
    UpdatePlayerFollowing();
    bSkyClockConnected = TrySynchronizeWithSkyClock();
    const FString Map = UGameplayStatics::GetCurrentLevelName(this, true);
    if (!bSkyClockConnected && (Map == TEXT("L_Normandy_FPS_Test") || Map == TEXT("L_MilitaryTrench_FPS_Test")))
    {
        // Start the imported scenes at 09:00 so first entry is in daylight.
        NormalizedDayTime = 0.375f;
        WeatherClockSeconds = NormalizedDayTime * RealSecondsPerGameDay;
    }
    ApplyState(bAutomaticSchedule ? ResolveScheduledState() : CurrentState);

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
    UpdateSchedule();
    UpdateEffects(DeltaSeconds);
    UpdateSceneDayNight(DeltaSeconds);
    UpdateLightning(DeltaSeconds);

}

float AFPSWeatherManager::GetSurfaceWetness() const
{
    return SurfaceEffects ? SurfaceEffects->GetWetness() : 0;
}

void AFPSWeatherManager::SetWeatherState(EFPSWeatherState NewState, bool bDisableAutomaticSchedule)
{
    if (bDisableAutomaticSchedule)
    {
        bAutomaticSchedule = false;
    }
    ApplyState(NewState);
}

void AFPSWeatherManager::ResumeAutomaticSchedule()
{
    bAutomaticSchedule = true;
    ApplyState(ResolveScheduledState());
}

void AFPSWeatherManager::ApplyState(EFPSWeatherState NewState)
{
    if (CurrentState == NewState && TargetRainIntensity == StateIntensity(NewState))
    {
        return;
    }

    const EFPSWeatherState Previous = CurrentState;
    CurrentState = NewState;
    TargetRainIntensity = StateIntensity(NewState);
    LightningCountdown = WeatherRandom.FRandRange(6.0f, 18.0f);
    UE_LOG(LogTemp, Display, TEXT("FPS weather changed: %d -> %d (rain %.2f)"),
        static_cast<int32>(Previous), static_cast<int32>(CurrentState), TargetRainIntensity);
    OnWeatherChanged.Broadcast(Previous, CurrentState);
}

void AFPSWeatherManager::UpdateSchedule()
{
    if (bAutomaticSchedule)
    {
        ApplyState(ResolveScheduledState());
    }
}

EFPSWeatherState AFPSWeatherManager::ResolveScheduledState() const
{
    constexpr int32 SegmentsPerDay = 8;
    const int32 Segment = FMath::Clamp(FMath::FloorToInt(NormalizedDayTime * SegmentsPerDay), 0, SegmentsPerDay - 1);
    uint32 Hash = static_cast<uint32>(WeatherSeed) ^ static_cast<uint32>(DaySerial * 7919 + Segment * 104729);
    Hash ^= Hash << 13;
    Hash ^= Hash >> 17;
    Hash ^= Hash << 5;
    const float Pick = static_cast<float>(Hash & 0x00FFFFFFu) / static_cast<float>(0x01000000u);

    if (Pick < 0.35f) return EFPSWeatherState::Clear;
    if (Pick < 0.60f) return EFPSWeatherState::Cloudy;
    if (Pick < 0.76f) return EFPSWeatherState::LightRain;
    if (Pick < 0.92f) return EFPSWeatherState::Rain;
    return EFPSWeatherState::Storm;
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
        const FVector CameraLocation = Camera->GetCameraLocation();
        SetActorLocation(CameraLocation + FVector(0.0, 0.0, 900.0));

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
    const float AudioShelter = FMath::Lerp(1.0f, 0.25f, ShelterAmount);

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
            Instance->SetScalarParameterValue(FPSWeatherNames::Lightning, LightningFlashTime > 0.0f ? 1.0f : 0.0f);
        }
    }
}

void AFPSWeatherManager::UpdateLightning(float DeltaSeconds)
{
    if (LightningFlashTime > 0.0f)
    {
        LightningFlashTime -= DeltaSeconds;
        const float Phase = FMath::Clamp(LightningFlashTime / 0.32f, 0.0f, 1.0f);
        const float Pulse = FMath::Square(FMath::Sin(Phase * PI * 3.0f));
        LightningLight->SetIntensity(Pulse * 1800000.0f);
    }
    else
    {
        LightningLight->SetIntensity(0.0f);
    }

    if (CurrentState != EFPSWeatherState::Storm || TargetRainIntensity < 0.9f)
    {
        return;
    }

    LightningCountdown -= DeltaSeconds;
    if (LightningCountdown > 0.0f)
    {
        return;
    }

    LightningFlashTime = 0.32f;
    LightningCountdown = WeatherRandom.FRandRange(6.0f, 18.0f);
    const float StrikeDistanceCm = WeatherRandom.FRandRange(80000.0f, 400000.0f);
    PlayDelayedThunder(StrikeDistanceCm / 34300.0f);
}

void AFPSWeatherManager::PlayDelayedThunder(float DelaySeconds)
{
    if (ThunderSounds.IsEmpty())
    {
        return;
    }
    const int32 SoundIndex = WeatherRandom.RandRange(0, ThunderSounds.Num() - 1);
    TWeakObjectPtr<AFPSWeatherManager> WeakThis(this);
    FTimerHandle Handle;
    GetWorldTimerManager().SetTimer(Handle, [WeakThis, SoundIndex]()
    {
        if (WeakThis.IsValid() && WeakThis->CurrentState == EFPSWeatherState::Storm && WeakThis->ThunderSounds.IsValidIndex(SoundIndex))
        {
            WeakThis->ThunderAudio->SetSound(WeakThis->ThunderSounds[SoundIndex]);
            WeakThis->ThunderAudio->Play();
        }
    }, DelaySeconds, false);
}

void AFPSWeatherManager::UpdateSceneDayNight(float DeltaSeconds)
{
    // The imported test scenes have no BP_FPS_DayNightManager. Drive their
    // existing lights only in the running world; shared source sublevels stay intact.
    const FString Map = UGameplayStatics::GetCurrentLevelName(this, true);
    if (bSkyClockConnected || (Map != TEXT("L_Normandy_FPS_Test") && Map != TEXT("L_MilitaryTrench_FPS_Test"))) return;
    SceneLightingRefresh += DeltaSeconds;
    if (SceneLightingRefresh < 0.1f) return;
    SceneLightingRefresh = 0.0f;
    const float SunHeight = FMath::Sin((NormalizedDayTime - 0.25f) * 2.0f * PI);
    const float Daylight = FMath::SmoothStep(-0.12f, 0.35f, SunHeight);
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
            if (Sky) Sky->SetIntensity(Base * FMath::Lerp(0.06f, 1.0f, Daylight));
            if (Fill) Fill->SetIntensity(Base * FMath::Lerp(0.025f, 1.0f, Daylight));
        }
    }
}

bool AFPSWeatherManager::TrySynchronizeWithSkyClock()
{
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

            float SkyUnits = -1.0f;
            if (const FFloatProperty* FloatProperty = CastField<FFloatProperty>(Property))
            {
                SkyUnits = FloatProperty->GetPropertyValue_InContainer(Actor);
            }
            else if (const FDoubleProperty* DoubleProperty = CastField<FDoubleProperty>(Property))
            {
                SkyUnits = static_cast<float>(DoubleProperty->GetPropertyValue_InContainer(Actor));
            }
            if (SkyUnits < 0.0f) continue;

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
    }
    return false;
}
