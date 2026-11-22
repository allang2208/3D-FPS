#include "BronzeTorch.h"
#include "../Weapons/Staff/StaffIlluminationProfile.h"
#include "../WorldGeneration/VillageInteriorLighting.h"
#include "../WorldGeneration/VillagePresentationView.h"
#include "../WorldGeneration/FluidPresentationSubsystem.h"
#include "../Weapons/ThermalTargetSubsystem.h"

#include "../FPSWeatherManager.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "TimerManager.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "UObject/ConstructorHelpers.h"

namespace
{
    // 资产名按类区分（UBT 的 unity 合并会把同模块的 .cpp 并进一块，匿名命名空间是共享的）。
    const TCHAR* TorchMeshAsset = TEXT("/Game/Props/RomanColumn20260915/SM_BronzeTorch.SM_BronzeTorch");
    const TCHAR* TorchMaterialAsset = TEXT("/Game/Props/RomanColumn20260915/M_Bronze.M_Bronze");
    // 火焰来源：Vefects Free Fire `NS_Fire_Small` 的项目内副本 `NS_TorchFlame`
    // （副本改动：两个火焰发射器 ScaleSpriteSize 的 Uniform Curve Scale 1 -> 0.3，
    //  删除自带 NE_Sparkles 火星与 NE_Lights 光发射器；光照交给本类那个受点火曲线控制的点光）。
    // 早期用 Epic `NiagaraExamples/FX_Misc/NS_Fire`：那是环境火，还带吃静态网格的 CPU 发射器
    // （日志：NiagaraStaticMeshDataInterface used by CPU emitter ... Mesh: SM_BronzeTorch），
    // 挂在火把上不出火；本工程文档里也写着"不能直接挂上"。
    const TCHAR* TorchFlameAsset = TEXT("/Game/Props/RomanColumn20260915/NS_TorchFlame.NS_TorchFlame");
    // 时钟读取节流：点火窗口以分钟计，每秒读 5 次足够，闪烁仍按帧走。
    constexpr float ClockRefreshSeconds = 0.2f;
}

ABronzeTorch::ABronzeTorch(const FObjectInitializer& ObjectInitializer) : Super(ObjectInitializer)
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = 0.0f;

    SceneRoot = CreateDefaultSubobject<USceneComponent>(TEXT("TorchRoot"));
    SetRootComponent(SceneRoot);

    TorchBody = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("TorchBody"));
    TorchBody->SetupAttachment(SceneRoot);
    TorchBody->SetMobility(EComponentMobility::Movable);
    TorchBody->SetCollisionProfileName(TEXT("BlockAll"));
    TorchBody->SetCanEverAffectNavigation(false);

    TorchFlame = CreateDefaultSubobject<UNiagaraComponent>(TEXT("TorchFlame"));
    TorchFlame->SetupAttachment(SceneRoot);
    TorchFlame->SetMobility(EComponentMobility::Movable);
    TorchFlame->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    TorchFlame->SetCanEverAffectNavigation(false);
    TorchFlame->SetCastShadow(false);
    TorchFlame->bAffectDistanceFieldLighting = false;
    TorchFlame->SetAutoActivate(false);

    TorchLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("TorchLight"));
    TorchLight->SetupAttachment(SceneRoot);
    TorchLight->SetMobility(EComponentMobility::Movable);
    TorchLight->SetCastShadows(false);
    TorchLight->SetIntensityUnits(ELightUnits::Lumens);
    TorchLight->SetLightColor(LightColor);
    TorchLight->SetAttenuationRadius(LightRadiusCm);
    TorchLight->SetIntensity(0.0f);
    TorchLight->SetVisibility(false);

    static ConstructorHelpers::FObjectFinder<UStaticMesh> MeshFinder(TorchMeshAsset);
    static ConstructorHelpers::FObjectFinder<UMaterialInterface> MaterialFinder(TorchMaterialAsset);
    static ConstructorHelpers::FObjectFinder<UNiagaraSystem> FlameFinder(TorchFlameAsset);
    if (MeshFinder.Succeeded())
    {
        BodyMesh = MeshFinder.Object;
    }
    if (MaterialFinder.Succeeded())
    {
        BodyMaterial = MaterialFinder.Object;
    }
    if (FlameFinder.Succeeded())
    {
        FlameSystem = FlameFinder.Object;
    }
}

void ABronzeTorch::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    ApplyComponentOffsets();
}

void ABronzeTorch::BeginPlay()
{
    Super::BeginPlay();
    if (bClockDormant) SetActorTickEnabled(true);
    bClockDormant = false;
    WokeAt = -1.;
    NextFlameViewAt = -1.;
    ClockRefreshCountdown = 0.f;
    UThermalTargetSubsystem::RegisterFire(TorchFlame,FVector(12,12,32),FVector(0,0,20));
    // Migrate the old authored defaults on already placed/saved torches too.
    // Keep deliberately customized values; do not rewrite the user's world save.
    if (FMath::IsNearlyEqual(LightLumens, 600.0f)) LightLumens = 350.0f;
    if (FMath::IsNearlyEqual(LightRadiusCm, 900.0f)) LightRadiusCm = 500.0f;
    if (FMath::IsNearlyEqual(FlickerAmplitude, 0.12f)) FlickerAmplitude = 0.04f;
    if (FMath::IsNearlyEqual(FlickerFrequency, 7.5f)) FlickerFrequency = 1.5f;
    const FVector TorchPosition = GetActorLocation();
    const float PhaseSeed = FMath::Sin(TorchPosition.X * 0.017f + TorchPosition.Y * 0.031f + TorchPosition.Z * 0.013f) * 43758.5453f;
    FlickerPhase = (PhaseSeed - FMath::FloorToFloat(PhaseSeed)) * 2.0f * PI;
    ApplyComponentOffsets();
    ResolveWeatherManager();
    RefreshClock(0.0f);
    // 出生瞬间直接取目标状态：进关卡时不该先看到 6 秒的淡入。
    IgnitionAmount = ShouldBeLitNow() ? 1.0f : 0.0f;
    ApplyVisuals(0.0f);
}

void ABronzeTorch::ApplyComponentOffsets()
{
    if (TorchBody)
    {
        TorchBody->SetStaticMesh(BodyMesh);
        if (BodyMaterial)
        {
            TorchBody->SetMaterial(0, BodyMaterial);
        }
    }
    if (TorchFlame)
    {
        if (FlameSystem)
        {
            TorchFlame->SetAsset(FlameSystem);
        }
        TorchFlame->SetRelativeLocation(FlameOffset);
    }
    if (TorchLight)
    {
        TorchLight->SetRelativeLocation(LightOffset);
        TorchLight->SetLightColor(LightColor);
        TorchLight->SetAttenuationRadius(LightRadiusCm);
        TorchLight->SetCastShadows(bLightCastsShadows);
        // Give the flame a finite source; keep sharp glints and fog halos subdued.
        TorchLight->SetSourceRadius(6.0f);
        TorchLight->SetSoftSourceRadius(8.0f);
        TorchLight->SetSpecularScale(SceneSpecularScale);
        TorchLight->SetVolumetricScatteringIntensity(0.08f);
    }
}

AFPSWeatherManager* ABronzeTorch::ResolveWeatherManager()
{
    if (WeatherManager.IsValid())
    {
        return WeatherManager.Get();
    }
    UWorld* World = GetWorld();
    if (!World)
    {
        return nullptr;
    }
    for (TActorIterator<AFPSWeatherManager> It(World); It; ++It)
    {
        WeatherManager = *It;
        break;
    }
    return WeatherManager.Get();
}

void ABronzeTorch::RefreshClock(float DeltaSeconds)
{
    ClockRefreshCountdown -= DeltaSeconds;
    if (ClockRefreshCountdown > 0.0f)
    {
        return;
    }
    ClockRefreshCountdown = ClockRefreshSeconds;

    const AFPSWeatherManager* Weather = ResolveWeatherManager();
    bCachedClockValid = Weather != nullptr;
    CachedHour = Weather ? FMath::Frac(Weather->NormalizedDayTime) * 24.0f : 12.0f;
}

bool ABronzeTorch::ShouldBeLitNow() const
{
    if (!bAutomaticIgnition)
    {
        return bLitOverride;
    }
    if (!bCachedClockValid)
    {
        // 没有天气管理器的关卡（纯光照图/资产预览）回落到固定状态。
        return bStartLit;
    }
    // 窗口跨午夜（默认 17:00 -> 次日 05:30）时按"或"判断。
    return IgniteHour <= ExtinguishHour
        ? (CachedHour >= IgniteHour && CachedHour < ExtinguishHour)
        : (CachedHour >= IgniteHour || CachedHour < ExtinguishHour);
}

void ABronzeTorch::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);

    const double Now = GetWorld()->GetTimeSeconds();
    if (bExteriorClockSleep && TorchLight && Now >= NextRangeCheck)
    {
        NextRangeCheck = Now + .6;
        bool HasView = false;
        const double Range = VillagePresentationView::Distance(*GetWorld(), GetActorLocation(), 0., &HasView);
        const double LightRange = TorchLight->MaxDrawDistance;
        const double FlameRange = bEnableFlame && TorchFlame ? TorchFlame->LDMaxDrawDistance : 0.;
        const double FarRange = FMath::Max(LightRange, FlameRange);
        const bool Distant = HasView && LightRange > 0. && Range > FarRange + (bDistantFixture ? 0. : 500.);
        if (Distant != bDistantFixture)
        {
            if (Distant) NearbyTickInterval = GetActorTickInterval();
            bDistantFixture = Distant;
            SetActorTickInterval(Distant ? FMath::Max(NearbyTickInterval, .6f) : NearbyTickInterval);
        }
    }

    // A tick interval can include the time spent disabled. Only integrate time since ignition resumed.
    if (WokeAt >= 0.)
    {
        DeltaSeconds = FMath::Min(DeltaSeconds, float(FMath::Max(0., double(GetWorld()->GetTimeSeconds()) - WokeAt)));
        WokeAt = -1.;
    }
    RefreshClock(DeltaSeconds);

    const bool bTargetLit = ShouldBeLitNow();
    if (IgnitionBlendSeconds > KINDA_SMALL_NUMBER)
    {
        const float Step = DeltaSeconds / IgnitionBlendSeconds;
        IgnitionAmount = FMath::Clamp(IgnitionAmount + (bTargetLit ? Step : -Step), 0.0f, 1.0f);
    }
    else
    {
        IgnitionAmount = bTargetLit ? 1.0f : 0.0f;
    }

    ApplyVisuals(DeltaSeconds);

    const bool bLitNow = IgnitionAmount > 0.5f;
    if (bLogStateChanges && (!bHasReported || bLitNow != bLastReportedLit))
    {
        bHasReported = true;
        bLastReportedLit = bLitNow;
        UE_LOG(LogTemp, Display, TEXT("TORCH_STATE label=%s lit=%d hour=%.2f clock=%d"),
            *GetName(), bLitNow ? 1 : 0, CachedHour, bCachedClockValid ? 1 : 0);
    }
    if (bExteriorClockSleep && !bTargetLit && IgnitionAmount == 0.f)
    {
        bClockDormant = true;
        SetActorTickEnabled(false);
        UpdateDormantClock();
    }
}

void ABronzeTorch::UpdateDormantClock()
{
    if (!bClockDormant) return;
    FTimerManager& Timers = GetWorldTimerManager();
    if (ShouldBeLitNow())
    {
        Timers.ClearTimer(DormantClockTimer);
        bClockDormant = false;
        WokeAt = GetWorld()->GetTimeSeconds();
        SetActorTickEnabled(true);
    }
    else if (!bAutomaticIgnition)
    {
        Timers.ClearTimer(DormantClockTimer);
    }
    else if (!Timers.TimerExists(DormantClockTimer))
    {
        Timers.SetTimer(DormantClockTimer, this, &ThisClass::PollDormantClock, ClockRefreshSeconds, true);
    }
}

void ABronzeTorch::PollDormantClock()
{
    RefreshClock(ClockRefreshSeconds);
    if (ShouldBeLitNow()) UpdateDormantClock();
}

void ABronzeTorch::EndPlay(const EEndPlayReason::Type Reason)
{
    GetWorldTimerManager().ClearTimer(DormantClockTimer);
    Super::EndPlay(Reason);
}

bool ABronzeTorch::HasBurningFlame() const
{
    return bEnableFlame && IgnitionAmount > .001f && TorchFlame && TorchFlame->GetAsset();
}

void ABronzeTorch::UpdateBurningFlame()
{
    UWorld* World = GetWorld();
    const double Now = World->GetTimeSeconds();
    if (Now >= NextFlameViewAt)
    {
        NextFlameViewAt = Now + .1;
        auto* Fluid = World->GetSubsystem<UFluidPresentationSubsystem>();
        const float Range = TorchFlame->LDMaxDrawDistance > 0.f ? TorchFlame->LDMaxDrawDistance : 6000.f;
        const auto Detail = Fluid ? Fluid->FireViews.Classify(*World, TorchFlame->GetComponentLocation(),
            90.f, 25.f, FMath::Min(2200.f, Range), Range, TorchFlame, bFullFlame) : EFireParticleDetail::Full;
        bFlameInView = Detail != EFireParticleDetail::Off;
        if (bFlameInView && bFullFlame != (Detail == EFireParticleDetail::Full))
        {
            bFullFlame = Detail == EFireParticleDetail::Full;
            for (const auto& Emitter : TorchFlame->GetAsset()->GetEmitterHandles())
            {
                const FName Name = Emitter.GetName();
                if (Emitter.GetIsEnabled() && (Name == TEXT("NE_Flame_02") || Name == TEXT("NE_Ashes") || Name == TEXT("NE_Heat")))
                    TorchFlame->SetEmitterEnable(Name, bFullFlame);
            }
        }
    }
    const float Scale = FlameScale * FMath::Lerp(FlameIgnitionScaleFloor, 1.f, IgnitionAmount);
    if (TorchFlame->GetRelativeScale3D() != FVector(Scale))
        TorchFlame->SetRelativeScale3D(FVector(Scale));
    if (bFlameInView)
    {
        if (!TorchFlame->IsActive()) TorchFlame->Activate(true);
    }
    else if (TorchFlame->IsActive()) TorchFlame->DeactivateImmediate();
}

void ABronzeTorch::ApplyVisuals(float DeltaSeconds)
{
    const bool bIgnited = IgnitionAmount > 0.001f;

    if (TorchFlame)
    {
        if (HasBurningFlame() && GetNetMode() != NM_DedicatedServer)
        {
            UpdateBurningFlame();
        }
        else if (TorchFlame->IsActive())
        {
            TorchFlame->Deactivate();
        }
    }

    if (TorchLight)
    {
        if (bEnableLight && bIgnited)
        {
            FlickerPhase += DeltaSeconds * FlickerFrequency * 2.0f * PI;
            const float Flicker = 1.0f + FlickerAmplitude *
                (0.7f * FMath::Sin(FlickerPhase) + 0.3f * FMath::Sin(0.63f * FlickerPhase + 1.3f));
            TorchLight->SetVisibility(true);
            TorchLight->SetIntensity(LightLumens * IgnitionAmount * (bDistantFixture ? 1.f : Flicker));
        }
        else
        {
            TorchLight->SetIntensity(0.0f);
            TorchLight->SetVisibility(false);
        }
    }
}

void ABronzeTorch::SetLit(bool bLit)
{
    bAutomaticIgnition = false;
    bLitOverride = bLit;
    UpdateDormantClock();
}

void ABronzeTorch::ConfigureSceneLight(float Lumens,float RadiusCm,bool bShadows)
{
    LightLumens=Lumens;LightRadiusCm=RadiusCm;bLightCastsShadows=bShadows;
    TorchLight->SetAttenuationRadius(LightRadiusCm);
    TorchLight->SetCastShadows(bLightCastsShadows);
    TorchLight->SetIntensity(LightLumens*IgnitionAmount);
}

void ABronzeTorch::ConfigureShopInterior(UNiagaraSystem* InteriorFlame)
{
    LightColor = UVillageInteriorLighting::GlowTint();
    LightLumens = UVillageInteriorLighting::FullLumens();
    LightRadiusCm = UStaffIlluminationProfile::RadiusCm;
    bLightCastsShadows = true;
    SceneSpecularScale = 1.f;
    FlickerAmplitude = 0.f;
    UVillageInteriorLighting::Configure(TorchLight, IgnitionAmount);
    if (InteriorFlame)
    {
        FlameSystem = InteriorFlame;
        TorchFlame->SetAsset(FlameSystem);
        NextFlameViewAt = -1.;
    }
}

void ABronzeTorch::SetSceneSpecularScale(float Scale)
{
    SceneSpecularScale = Scale;
    TorchLight->SetSpecularScale(Scale);
}

void ABronzeTorch::SetAutomaticIgnition(bool bEnabled)
{
    bAutomaticIgnition = bEnabled;
    if (bEnabled)
    {
        ClockRefreshCountdown = 0.0f;
        RefreshClock(0.0f);
    }
    UpdateDormantClock();
}
