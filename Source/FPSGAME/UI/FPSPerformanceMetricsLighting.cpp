#include "FPSPerformanceMetrics.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/LocalLightComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/RectLightComponent.h"
#include "Components/SpotLightComponent.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "SceneView.h"

void UFPSPerformanceMetricsSubsystem::ScanLight(const ULightComponent* Light, const FVector& ViewLocation,
    const FConvexVolume* Frustum, FFPSPerformanceSnapshot& Snapshot) const
{
    FFPSLightObservation Row;
    auto& Coverage = Snapshot.Coverage;
    const AActor* Owner = Light->GetOwner();
    Row.ObjectPath = Light->GetPathName();
    Row.Label = Owner ? Owner->GetActorNameOrLabel() : Light->GetName();
    Row.Position = Light->GetComponentLocation();
    Row.DistanceCm = FVector::Distance(ViewLocation, Row.Position);
    Row.Intensity = Light->Intensity;
    Row.bRegistered = Light->IsRegistered();
    Row.bVisibleFlag = Light->IsVisible() && !Light->bHiddenInGame && (!Owner || !Owner->IsHidden());
    Row.bAffectsWorld = Light->bAffectsWorld;
    // EV intensities may be zero/negative while still emitting light; IES can override raw intensity.
    Row.bPositiveBrightness = Light->ComputeLightBrightness() > 0.f;
    Row.bEnabled = Row.bRegistered && Row.bVisibleFlag && Row.bAffectsWorld && Row.bPositiveBrightness;
    Row.bCastShadows = Light->CastShadows;
    Row.bCastVolumetricShadow = Light->bCastVolumetricShadow;
    Row.RayTracedShadowMode = int32(Light->CastRaytracedShadow.GetValue());
    Row.VolumetricScattering = Light->VolumetricScatteringIntensity;
    Row.MaxDrawDistanceCm = Light->MaxDrawDistance;
    Row.FadeRangeCm = Light->MaxDistanceFadeRange;
    const auto* ScaleCVar = IConsoleManager::Get().FindConsoleVariable(TEXT("r.LightMaxDrawDistanceScale"));
    const float Scale = ScaleCVar ? FMath::Max(0.f, ScaleCVar->GetFloat()) : 1.f;
    Row.EffectiveMaxDrawDistanceCm = Row.MaxDrawDistanceCm * Scale;
    Row.Mobility = Light->Mobility == EComponentMobility::Movable ? TEXT("Movable")
        : Light->Mobility == EComponentMobility::Stationary ? TEXT("Stationary") : TEXT("Static");
    Row.Type = TEXT("Other");
    Row.IntensityUnits = TEXT("engine");
    if (Owner)
        for (const FName Tag : Owner->Tags)
        {
            const FString Value = Tag.ToString();
            if (Value.StartsWith(TEXT("DungeonModule."))) Row.Module = Value;
            if (Value.StartsWith(TEXT("DungeonLight."))) Row.Role = Value.Mid(13);
        }
    if (const auto* Local = Cast<ULocalLightComponent>(Light))
    {
        Row.bLocal = true;
        Row.RadiusCm = Local->AttenuationRadius;
        switch (Local->IntensityUnits)
        {
        case ELightUnits::Lumens: Row.IntensityUnits = TEXT("lm"); break;
        case ELightUnits::Candelas: Row.IntensityUnits = TEXT("cd"); break;
        case ELightUnits::Nits: Row.IntensityUnits = TEXT("nit"); break;
        case ELightUnits::EV: Row.IntensityUnits = TEXT("EV"); break;
        default: Row.IntensityUnits = TEXT("unitless"); break;
        }
    }
    if (const auto* Spot = Cast<USpotLightComponent>(Light))
    {
        Row.Type = TEXT("Spot");
        Row.OuterConeDegrees = Spot->OuterConeAngle;
        ++Coverage.SpotLights;
    }
    else if (Light->IsA<UPointLightComponent>()) { Row.Type = TEXT("Point"); ++Coverage.PointLights; }
    else if (Light->IsA<URectLightComponent>()) { Row.Type = TEXT("Rect"); ++Coverage.RectLights; }
    else if (Light->IsA<UDirectionalLightComponent>())
    {
        Row.Type = TEXT("Directional"); Row.IntensityUnits = TEXT("lux"); ++Coverage.DirectionalLights;
    }
    ++Coverage.Lights;
    // Retain schema <= 6 fields as flag-only counts, including zero-intensity components.
    if (Row.bRegistered && Row.bVisibleFlag)
    {
        ++Coverage.VisibleLights;
        if (Row.bCastShadows) ++Coverage.ShadowLights;
    }
    if (Row.bEnabled)
    {
        ++Coverage.EnabledLights;
        if (Row.bCastShadows) ++Coverage.EnabledShadowLights;
    }
    if (Snapshot.bHasView)
    {
        Row.bWithinDrawDistance = !Row.bLocal || Row.MaxDrawDistanceCm <= 0.f
            || Row.DistanceCm < Row.EffectiveMaxDrawDistanceCm;
        Row.bCameraInsideBounds = Row.bLocal && Row.DistanceCm <= Row.RadiusCm;
        if (Row.bEnabled && Row.bCameraInsideBounds && Row.bWithinDrawDistance) ++Coverage.CameraLightBounds;
        if (Frustum)
        {
            Row.bFrustumCandidate = !Row.bLocal || Frustum->IntersectSphere(Row.Position, Row.RadiusCm);
            Row.bViewCandidate = Row.bEnabled && Row.bWithinDrawDistance && Row.bFrustumCandidate;
            if (Row.bViewCandidate)
            {
                ++Coverage.LightViewCandidates;
                if (Row.bCastShadows) ++Coverage.ShadowViewCandidates;
            }
        }
    }
    Snapshot.Lights.Add(MoveTemp(Row));
}
