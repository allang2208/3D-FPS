#include "BronzeTorch.h"

#include "../FPSWeatherManager.h"
#include "Components/PointLightComponent.h"
#include "Components/SceneComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
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

ABronzeTorch::ABronzeTorch()
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
}

void ABronzeTorch::ApplyVisuals(float DeltaSeconds)
{
    const bool bIgnited = IgnitionAmount > 0.001f;

    if (TorchFlame)
    {
        if (bEnableFlame && bIgnited)
        {
            const float Scale = FlameScale * FMath::Lerp(FlameIgnitionScaleFloor, 1.0f, IgnitionAmount);
            TorchFlame->SetRelativeScale3D(FVector(Scale));
            if (!TorchFlame->IsActive())
            {
                TorchFlame->Activate(true);
            }
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
            const float Flicker = 1.0f + FlickerAmplitude * 0.55f *
                (FMath::Sin(FlickerPhase) + 0.6f * FMath::Sin(2.7f * FlickerPhase + 1.3f));
            TorchLight->SetVisibility(true);
            TorchLight->SetIntensity(LightLumens * IgnitionAmount * Flicker);
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
}

void ABronzeTorch::SetAutomaticIgnition(bool bEnabled)
{
    bAutomaticIgnition = bEnabled;
    if (bEnabled)
    {
        ClockRefreshCountdown = 0.0f;
        RefreshClock(0.0f);
    }
}
