#include "BuildingDaylight.h"
#include "../FPSWeatherManager.h"
#include "Components/BoxComponent.h"
#include "Components/PostProcessComponent.h"
#include "Components/SceneComponent.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "HAL/IConsoleManager.h"
#include "SceneView.h"

namespace
{
// Applied during view composition, including rooms serialized with the old
// per-building settings. No map reauthoring or extra lights are required.
TAutoConsoleVariable<float> CVarInteriorVisionExposureBoost(
    TEXT("fps.InteriorVision.ExposureBoost"), .4f,
    TEXT("Additional daylight-only exposure compensation inside authored rooms, in stops."));
TAutoConsoleVariable<float> CVarInteriorVisionDarkAdaptationBoost(
    TEXT("fps.InteriorVision.DarkAdaptationBoost"), .5f,
    TEXT("Additional dark-adaptation range inside authored rooms, in stops."));
}

ABuildingDaylight::ABuildingDaylight()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.TickInterval = .25f;
    PrimaryActorTick.bAllowTickOnDedicatedServer = false;
    SetRootComponent(CreateDefaultSubobject<USceneComponent>(TEXT("Room")));
    RoomBounds = CreateDefaultSubobject<UBoxComponent>(TEXT("InteriorBounds"));
    RoomBounds->SetupAttachment(RootComponent);
    RoomBounds->SetCollisionEnabled(ECollisionEnabled::NoCollision);
    RoomBounds->SetGenerateOverlapEvents(false);
    RoomBounds->SetCanEverAffectNavigation(false);
    Vision = CreateDefaultSubobject<UPostProcessComponent>(TEXT("InteriorVision"));
    Vision->SetupAttachment(RoomBounds);
    // The blendable performs the exact oriented room containment and feathering.
    // Do not depend on a NoCollision box providing a valid Chaos volume query.
    Vision->bUnbound = true;
    Vision->BlendRadius = 0.f;
    Vision->Priority = 100.f;
}

void ABuildingDaylight::UpdateBounds()
{
    RoomBounds->SetRelativeLocation((RoomMinimum + RoomMaximum) * .5);
    RoomBounds->SetBoxExtent((RoomMaximum - RoomMinimum).GetAbs() * .5, false);
}

void ABuildingDaylight::OnConstruction(const FTransform& Transform)
{
    Super::OnConstruction(Transform);
    UpdateBounds();
}

void ABuildingDaylight::BindWeather()
{
    if (Weather.IsValid() || GetWorld()->GetTimeSeconds() < NextWeatherSearch) return;
    NextWeatherSearch = GetWorld()->GetTimeSeconds() + 2.;
    for (TActorIterator<AFPSWeatherManager> It(GetWorld()); It; ++It)
    {
        Weather = *It;
        break;
    }
}

void ABuildingDaylight::BeginPlay()
{
    Super::BeginPlay();
    UpdateBounds();
    if (GetNetMode() == NM_DedicatedServer)
    {
        Vision->bEnabled = false;
        SetActorTickEnabled(false);
        return;
    }
    // Existing serialized house components may still have the old bounded flag.
    Vision->bUnbound = true;
    Vision->Settings.WeightedBlendables.Array.Add(FWeightedBlendable(1.f, this));
    Tick(.25f);
}

void ABuildingDaylight::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    if (!bFollowDaylight)
    {
        DaylightStrength = 1.f;
        return;
    }
    BindWeather();
    const float Clock = Weather.IsValid() ? Weather->NormalizedDayTime : .5f;
    DaylightStrength = FMath::SmoothStep(-.11f, .34f, FMath::Sin((Clock - .25f) * 2.f * PI));
}

void ABuildingDaylight::OverrideBlendableSettings(FSceneView& View, float Weight) const
{
    if (View.bIsSceneCapture || DaylightStrength <= 0.f) return;
    const FTransform Placement = GetActorTransform();
    const FVector Eye = Placement.InverseTransformPosition(View.ViewMatrices.GetViewOrigin());
    if (!FBox(RoomMinimum, RoomMaximum).IsInsideOrOn(Eye)) return;
    const FVector Scale = Placement.GetScale3D().GetAbs();
    const double Depth = FMath::Min(
        FMath::Min(Eye.X - RoomMinimum.X, RoomMaximum.X - Eye.X) * Scale.X,
        FMath::Min(Eye.Y - RoomMinimum.Y, RoomMaximum.Y - Eye.Y) * Scale.Y);
    const float Alpha = FMath::Clamp(Weight, 0.f, 1.f) * DaylightStrength
        * FMath::SmoothStep(0.f, EntranceTransitionCm, float(Depth));
    if (Alpha <= KINDA_SMALL_NUMBER) return;

    // Compose with the sky/weather's current exposure, independently for each view.
    // Widen dark adaptation only; retain the outdoor bright limit and colour grading.
    auto& S = View.FinalPostProcessSettings;
    const auto* Range = IConsoleManager::Get().FindConsoleVariable(TEXT("r.DefaultFeature.AutoExposure.ExtendDefaultLuminanceRange"));
    const float Stops = (AdditionalDarkAdaptationStops
        + FMath::Clamp(CVarInteriorVisionDarkAdaptationBoost.GetValueOnGameThread(), 0.f, 2.f)) * Alpha;
    S.AutoExposureMethod = AEM_Histogram;
    S.AutoExposureMinBrightness = Range && Range->GetInt() != 0
        ? FMath::Max(-10.f, S.AutoExposureMinBrightness - Stops)
        : FMath::Max(.0001f, S.AutoExposureMinBrightness / FMath::Exp2(Stops));
    S.AutoExposureBias += (ExposureCompensation
        + FMath::Clamp(CVarInteriorVisionExposureBoost.GetValueOnGameThread(), 0.f, 2.f)) * Alpha;
    // Meter room midtones rather than allowing the bright windows to dominate.
    S.AutoExposureLowPercent = FMath::Lerp(S.AutoExposureLowPercent, 35.f, Alpha);
    S.AutoExposureHighPercent = FMath::Lerp(S.AutoExposureHighPercent, 80.f, Alpha);
    S.AutoExposureSpeedUp = FMath::Lerp(S.AutoExposureSpeedUp, 6.f, Alpha);
    S.AutoExposureSpeedDown = FMath::Lerp(S.AutoExposureSpeedDown, 2.f, Alpha);
    S.LocalExposureMethod = ELocalExposureMethod::Bilateral;
    S.LocalExposureShadowContrastScale = FMath::Lerp(S.LocalExposureShadowContrastScale,
        FMath::Clamp(ShadowContrast - .1f, .4f, 1.f), Alpha);
    S.LocalExposureHighlightContrastScale = FMath::Lerp(S.LocalExposureHighlightContrastScale,
        FMath::Clamp(HighlightContrast - .1f, .4f, 1.f), Alpha);
}

void ABuildingDaylight::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    Vision->Settings.WeightedBlendables.Array.RemoveAll([this](const FWeightedBlendable& Item)
        { return Item.Object == this; });
    Vision->bEnabled = false;
    Super::EndPlay(EndPlayReason);
}
