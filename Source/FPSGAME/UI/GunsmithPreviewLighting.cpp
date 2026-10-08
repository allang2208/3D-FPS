#include "GunsmithPreviewLighting.h"
#include "PreviewScene.h"
#include "Components/RectLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"

namespace GunsmithPreviewLighting
{
namespace
{
struct FSoftbox
{
    const TCHAR* Tag;
    FVector Offset;
    float Lumens;
    float Width;
    float Height;
};

// Shared with every workbench family. These are the broad sources previously
// available only to the rune sword and claymore, which also need metal reflections.
const FSoftbox Softboxes[] = {
    {TEXT("GunsmithStudioKey"),  FVector(-130,-65,85), 75.f,100.f,120.f},
    {TEXT("GunsmithStudioFill"), FVector(-100,85,-25), 35.f,110.f,110.f},
    {TEXT("GunsmithStudioRim"),  FVector(65,35,90),    90.f,40.f,100.f}
};
}

void Create(FPreviewScene& Scene, USceneCaptureComponent2D& Capture)
{
    for (const auto& Source : Softboxes)
    {
        auto* Light = NewObject<URectLightComponent>(GetTransientPackage(), NAME_None, RF_Transient);
        Light->ComponentTags.Add(FName(Source.Tag));
        Light->SetMobility(EComponentMobility::Movable);
        Light->SetIntensityUnits(ELightUnits::Lumens);
        Light->SetIntensity(Source.Lumens);
        Light->SetLightColor(FLinearColor::White);
        Light->SetCastShadows(false);
        Light->SetSourceWidth(Source.Width);
        Light->SetSourceHeight(Source.Height);
        Light->SetAttenuationRadius(600.f);
        // The firearm capture follows a world-space player camera. Attaching
        // the rig avoids leaving its lights behind at the old fixed (500,0,0).
        Light->SetupAttachment(&Capture);
        Light->SetRelativeTransform(FTransform((-Source.Offset).Rotation(), FVector(500,0,0)+Source.Offset));
        Scene.AddComponent(Light, FTransform::Identity);
    }
}

void Update(USceneCaptureComponent2D& Capture, const FBox& ViewBounds, bool bGraphite201, float SoftboxIntensityScale)
{
    if (!ViewBounds.IsValid) return;
    const FVector Center = ViewBounds.GetCenter();
    const float Scale = FMath::Clamp(float(ViewBounds.GetSize().Size()/140.), .45f, 1.7f);
    for (USceneComponent* Child : Capture.GetAttachChildren())
    {
        auto* Light = Cast<URectLightComponent>(Child);
        if (!Light) continue;
        for (const auto& Source : Softboxes)
        {
            if (!Light->ComponentHasTag(FName(Source.Tag))) continue;
            const FTransform Pose((-Source.Offset).Rotation(), Center+Source.Offset*Scale);
            if (!Light->GetRelativeTransform().Equals(Pose, .01f)) Light->SetRelativeTransform(Pose);
            // Scale emitter area, distance and flux together: a pistol receives
            // the same lighting level as a long weapon instead of washing out.
            // The rebuilt 201's broad side planes need a dominant key and a
            // weaker fill to show coating and bevels in the orthographic view.
            const float FinishScale = !bGraphite201 ? 1.f :
                Light->ComponentHasTag(TEXT("GunsmithStudioFill")) ? .45f :
                Light->ComponentHasTag(TEXT("GunsmithStudioKey")) ? .75f : .9f;
            const float Lumens = Source.Lumens*Scale*Scale*FinishScale*SoftboxIntensityScale;
            if (!FMath::IsNearlyEqual(Light->Intensity, Lumens, .01f)) Light->SetIntensity(Lumens);
            if (!FMath::IsNearlyEqual(Light->SourceWidth, Source.Width*Scale, .01f)) Light->SetSourceWidth(Source.Width*Scale);
            if (!FMath::IsNearlyEqual(Light->SourceHeight, Source.Height*Scale, .01f)) Light->SetSourceHeight(Source.Height*Scale);
            if (!FMath::IsNearlyEqual(Light->AttenuationRadius, 600.f*Scale, .01f)) Light->SetAttenuationRadius(600.f*Scale);
            break;
        }
    }
}
}
