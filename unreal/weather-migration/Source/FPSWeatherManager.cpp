#include "FPSWeatherManager.h"

#include "Camera/PlayerCameraManager.h"
#include "Components/AudioComponent.h"
#include "Components/DecalComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
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
    static const FName WindVelocity(TEXT("User.WindVelocity"));
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

    SplashComponent = CreateDefaultSubobject<UNiagaraComponent>(TEXT("GroundSplashes"));
    SplashComponent->SetupAttachment(SceneRoot);
    SplashComponent->SetRelativeLocation(FVector(0.0, 0.0, -1080.0));
    SplashComponent->SetAutoActivate(false);

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
        TEXT("/Game/Weather/VFX/NS_FPS_Rain.NS_FPS_Rain"));
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> SplashFinder(
        TEXT("/Game/Weather/VFX/NS_FPS_RainSplashes.NS_FPS_RainSplashes"));
    static ConstructorHelpers::FObjectFinder<UMaterialParameterCollection> WeatherParametersFinder(
        TEXT("/Game/Weather/Materials/MPC_FPS_Weather.MPC_FPS_Weather"));
    static ConstructorHelpers::FObjectFinder<USoundBase> LightRainFinder(
        TEXT("/Game/Weather/Audio/S_Rain_Light_Loop.S_Rain_Light_Loop"));
    static ConstructorHelpers::FObjectFinder<USoundBase> RainAudioFinder(
        TEXT("/Game/Weather/Audio/S_Rain_Soft_Loop.S_Rain_Soft_Loop"));
    static ConstructorHelpers::FObjectFinder<USoundBase> HeavyRainFinder(
        TEXT("/Game/Weather/Audio/S_Rain_Patter_Loop.S_Rain_Patter_Loop"));
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> PuddleMaterialFinder(
        TEXT("/Game/JVAD3D_SimpleWaterPuddles/Materials/MI_JVAD3D_SimpleWaterPuddles_A.MI_JVAD3D_SimpleWaterPuddles_A"));
    static ConstructorHelpers::FObjectFinder<USoundBase> ThunderOneFinder(
        TEXT("/Game/Thunder_Sounds/CUE/CUE_Thunder_Lightning_I_Without_rain_wind_background_noise_Cue.CUE_Thunder_Lightning_I_Without_rain_wind_background_noise_Cue"));
    static ConstructorHelpers::FObjectFinder<USoundBase> ThunderTwoFinder(
        TEXT("/Game/Thunder_Sounds/CUE/CUE_Thunder_Lightning_II_Without_rain_wind_background_noise_Cue.CUE_Thunder_Lightning_II_Without_rain_wind_background_noise_Cue"));
    static ConstructorHelpers::FObjectFinder<USoundBase> ThunderThreeFinder(
        TEXT("/Game/Thunder_Sounds/CUE/CUE_Thunder_Lightning_III_Without_rain_wind_background_noise_Cue.CUE_Thunder_Lightning_III_Without_rain_wind_background_noise_Cue"));
    if (RainFinder.Succeeded()) RainSystem = RainFinder.Object;
    if (SplashFinder.Succeeded()) SplashSystem = SplashFinder.Object;
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

    WeatherRandom.Initialize(WeatherSeed);
    RainComponent->SetAsset(RainSystem);
    SplashComponent->SetAsset(SplashSystem);
    LightRainAudio->SetSound(LightRainSound);
    RainAudio->SetSound(RainSound);
    HeavyRainAudio->SetSound(HeavyRainSound);
    UpdatePlayerFollowing();
    TrySynchronizeWithSkyClock();
    ApplyState(ResolveScheduledState());

    UE_LOG(LogTemp, Display,
        TEXT("FPSWeatherManager ready: day=%.0fs state=%d rain=%s splashes=%s puddles=%s rainAudio=%d thunder=%d"),
        RealSecondsPerGameDay,
        static_cast<int32>(CurrentState),
        RainSystem ? TEXT("yes") : TEXT("no"),
        SplashSystem ? TEXT("yes") : TEXT("no"),
        PuddleDecalMaterial ? TEXT("yes") : TEXT("no"),
        static_cast<int32>(LightRainSound != nullptr) + static_cast<int32>(RainSound != nullptr) + static_cast<int32>(HeavyRainSound != nullptr),
        ThunderSounds.Num());
}

void AFPSWeatherManager::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    if (!TrySynchronizeWithSkyClock())
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
    UpdateLightning(DeltaSeconds);

    PuddleRefreshAccumulator += DeltaSeconds;
    if (PuddleRefreshAccumulator >= 3.0f)
    {
        PuddleRefreshAccumulator = 0.0f;
        RefreshRuntimePuddles();
    }
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

        FCollisionQueryParams Params(SCENE_QUERY_STAT(FPSWeatherSplashGround), false);
        if (APawn* Pawn = UGameplayStatics::GetPlayerPawn(this, 0))
        {
            Params.AddIgnoredActor(Pawn);
        }
        FHitResult GroundHit;
        const FVector TraceStart = CameraLocation + FVector(0.0, 0.0, 200.0);
        const FVector TraceEnd = CameraLocation - FVector(0.0, 0.0, 2500.0);
        if (GetWorld()->LineTraceSingleByChannel(GroundHit, TraceStart, TraceEnd, ECC_Visibility, Params) &&
            GroundHit.ImpactNormal.Z > 0.5f)
        {
            SplashComponent->SetWorldLocation(GroundHit.ImpactPoint + GroundHit.ImpactNormal * 3.0f);
        }
    }
}

void AFPSWeatherManager::UpdateShelter(float DeltaSeconds)
{
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
    ShelterAmount = FMath::FInterpTo(ShelterAmount, bSheltered ? 1.0f : 0.0f, 0.25f, 8.0f);
}

void AFPSWeatherManager::UpdateEffects(float DeltaSeconds)
{
    const float Speed = 1.0f / FMath::Max(TransitionSeconds, 0.1f);
    const float OutdoorIntensity = FMath::FInterpTo(EffectiveRainIntensity, TargetRainIntensity, DeltaSeconds, Speed * 5.0f);
    EffectiveRainIntensity = OutdoorIntensity;
    const float VisibleIntensity = OutdoorIntensity * FMath::Lerp(1.0f, 0.08f, ShelterAmount);
    const float AudioShelter = FMath::Lerp(1.0f, 0.25f, ShelterAmount);

    RainComponent->SetFloatParameter(FPSWeatherNames::RainIntensity, VisibleIntensity);
    RainComponent->SetFloatParameter(FPSWeatherNames::SpawnRate, VisibleIntensity * 1200.0f);
    RainComponent->SetVariableVec3(FPSWeatherNames::WindVelocity, FVector(180.0f, 60.0f, -1900.0f));
    SplashComponent->SetFloatParameter(FPSWeatherNames::RainIntensity, VisibleIntensity);
    SplashComponent->SetFloatParameter(FPSWeatherNames::SpawnRate, VisibleIntensity * 180.0f);

    const bool bShouldRun = VisibleIntensity > 0.01f;
    if (bShouldRun && !RainComponent->IsActive()) RainComponent->Activate();
    if (!bShouldRun && RainComponent->IsActive()) RainComponent->Deactivate();
    if (bShouldRun && !SplashComponent->IsActive()) SplashComponent->Activate();
    if (!bShouldRun && SplashComponent->IsActive()) SplashComponent->Deactivate();

    const float LightLayer = FMath::Clamp(1.0f - FMath::Abs(OutdoorIntensity - 0.3f) / 0.35f, 0.0f, 1.0f) * AudioShelter;
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
            Instance->SetScalarParameterValue(FPSWeatherNames::Wetness, OutdoorIntensity);
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
        if (WeakThis.IsValid() && WeakThis->ThunderSounds.IsValidIndex(SoundIndex))
        {
            WeakThis->ThunderAudio->SetSound(WeakThis->ThunderSounds[SoundIndex]);
            WeakThis->ThunderAudio->Play();
        }
    }, DelaySeconds, false);
}

void AFPSWeatherManager::RefreshRuntimePuddles()
{
    if (!PuddleDecalMaterial || RuntimePuddleCount <= 0 || EffectiveRainIntensity < 0.2f)
    {
        for (UDecalComponent* Decal : RuntimePuddles)
        {
            if (Decal) Decal->SetVisibility(false);
        }
        return;
    }

    while (RuntimePuddles.Num() < RuntimePuddleCount)
    {
        UDecalComponent* Decal = NewObject<UDecalComponent>(this);
        Decal->SetupAttachment(SceneRoot);
        Decal->RegisterComponent();
        Decal->SetDecalMaterial(PuddleDecalMaterial);
        Decal->DecalSize = FVector(32.0f, 120.0f, 120.0f);
        Decal->SetFadeScreenSize(0.002f);
        RuntimePuddles.Add(Decal);
    }

    APlayerCameraManager* Camera = UGameplayStatics::GetPlayerCameraManager(this, 0);
    if (!Camera) return;
    const FVector Origin = Camera->GetCameraLocation();
    FCollisionQueryParams Params(SCENE_QUERY_STAT(FPSWeatherPuddles), false);
    for (int32 Index = 0; Index < RuntimePuddles.Num(); ++Index)
    {
        const float Radius = FMath::Sqrt(WeatherRandom.FRand()) * 1600.0f;
        const float Angle = WeatherRandom.FRandRange(0.0f, 2.0f * PI);
        const FVector2D Offset(FMath::Cos(Angle) * Radius, FMath::Sin(Angle) * Radius);
        const FVector Start = Origin + FVector(Offset.X, Offset.Y, 1000.0f);
        const FVector End = Start - FVector(0.0f, 0.0f, 4000.0f);
        FHitResult Hit;
        const bool bHit = GetWorld()->LineTraceSingleByChannel(Hit, Start, End, ECC_Visibility, Params);
        UDecalComponent* Decal = RuntimePuddles[Index];
        Decal->SetVisibility(bHit && Hit.ImpactNormal.Z > 0.85f);
        if (bHit)
        {
            Decal->SetWorldLocation(Hit.ImpactPoint + Hit.ImpactNormal * 2.0f);
            Decal->SetWorldRotation(FRotationMatrix::MakeFromX(-Hit.ImpactNormal).Rotator());
            const float Scale = WeatherRandom.FRandRange(0.65f, 1.5f);
            Decal->DecalSize = FVector(32.0f, 120.0f * Scale, 120.0f * Scale);
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
