#include "M24ScopeDrawing.h"
#include "Engine/LocalPlayer.h"
#include "Engine/GameViewportClient.h"
#include "GameFramework/PlayerController.h"
#include "Framework/Application/SlateApplication.h"
#include "Rendering/SlateRenderer.h"
#include "Styling/CoreStyle.h"
#include "SceneView.h"

namespace
{
struct FEtchedLines
{
    const FGeometry& Geometry;
    FVector2f Center;
    float Pixel, Alpha;
    FM24ScopeReticleCache& Cache;

    void Stroke(FVector2f A, FVector2f B, float Width, FLinearColor Color)
    {
        const FVector2f Delta = B - A;
        if (Delta.SizeSquared() < .001f) return;
        const FVector2f Normal = FVector2f(-Delta.Y, Delta.X).GetSafeNormal();
        const float Half = Width * Pixel * .5f, Feather = Pixel * .65f;
        const int32 Base = Cache.Vertices.Num();
        for (int32 Band = 0; Band < 4; ++Band)
        {
            const float Offset = Band == 0 ? -Half - Feather : Band == 1 ? -Half : Band == 2 ? Half : Half + Feather;
            FLinearColor Tint = Color;
            Tint.A *= (Band == 0 || Band == 3) ? 0.f : Alpha;
            for (const FVector2f P : {A, B})
                Cache.Vertices.Add(FSlateVertex::Make<ESlateVertexRounding::Disabled>(Geometry.GetAccumulatedRenderTransform(),
                    Center + P + Normal * Offset, FVector2f(.5f, .5f), Tint.ToFColor(true)));
        }
        for (int32 Band = 0; Band < 3; ++Band)
        {
            const int32 I = Base + Band * 2;
            Cache.Indices.Append({SlateIndex(I), SlateIndex(I + 1), SlateIndex(I + 2),
                SlateIndex(I + 2), SlateIndex(I + 1), SlateIndex(I + 3)});
        }
    }

    void Line(FVector2f A, FVector2f B, float Width = .85f, float Opacity = 1.f)
    {
        // Fine pale edge preserves the dark etching against shaded targets.
        Stroke(A, B, Width + .9f, FLinearColor(.72f, .75f, .73f, .28f * Opacity));
        Stroke(A, B, Width, FLinearColor(.010f, .013f, .012f, .96f * Opacity));
    }
};
}

void M24ScopeDrawing::PaintReticle(FSlateWindowElementList& Out, int32 Layer, const FGeometry& Geometry,
    const FVector2f& Center, float Radius, float Alpha, const APlayerController* Controller,
    FM24ScopeReticleCache& Cache,float OpticalFieldOfView)
{
    const FVector2f Size(Geometry.GetLocalSize());
    const float Pixel = 1.f / FMath::Max(.1f, Geometry.GetAccumulatedLayoutTransform().GetScale());
    Cache.Vertices.Reset(); Cache.Indices.Reset();
    Cache.Vertices.Reserve(4096); Cache.Indices.Reserve(9216);
    FEtchedLines Pen{Geometry, Center, Pixel, Alpha, Cache};

    // Use the lens projection when the scene is independently captured. The
    // main-camera path remains available for existing authoring callers.
    // A mil here is 0.001 radians, not an arbitrary pixel interval or a BDC.
    FVector2f Focal(0, 0);
    const auto* Local = Controller ? Controller->GetLocalPlayer() : nullptr;
    FSceneViewProjectionData Projection;
    if(OpticalFieldOfView>0.f)
        Focal=FVector2f(Radius/FMath::Tan(FMath::DegreesToRadians(OpticalFieldOfView)*.5f));
    else if (Local && Local->ViewportClient && Local->ViewportClient->Viewport &&
        Local->GetProjectionData(Local->ViewportClient->Viewport, Projection))
    {
        const FIntRect View = Projection.GetViewRect(), Constrained = Projection.GetConstrainedViewRect();
        if (View.Width() > 0 && View.Height() > 0)
            Focal = FVector2f(float(Projection.ProjectionMatrix.M[0][0]) * Constrained.Width() * .5f * Size.X / View.Width(),
                float(Projection.ProjectionMatrix.M[1][1]) * Constrained.Height() * .5f * Size.Y / View.Height());
    }
    const bool HasScale = Focal.X > 0.f && Focal.Y > 0.f;
    const FVector2f OneMil = Focal * FMath::Tan(.001f);
    const float End = Radius * .96f;
    for (int32 Axis = 0; Axis < 2; ++Axis)
    {
        const FVector2f Direction = Axis == 0 ? FVector2f(1, 0) : FVector2f(0, 1);
        const float F = Axis == 0 ? Focal.X : Focal.Y;
        const float Shoulder = HasScale ? FMath::Min(End * .72f, F * FMath::Tan(.022f)) : End * .35f;
        Pen.Line(Direction * -Shoulder, Direction * Shoulder);
        for (int32 Sign : {-1, 1})
            Pen.Line(Direction * (Sign * Shoulder), Direction * (Sign * End), 2.25f);
    }

    if (HasScale)
    {
        const float MilPixels = FMath::Min(OneMil.X, OneMil.Y) / Pixel;
        const float HalfOpacity = FMath::SmoothStep(4.5f, 7.f, MilPixels) * .65f;
        // Twenty numbered mils each side; half-mil ticks fade out before they
        // become subpixel clutter. The exact angular positions never rescale.
        for (int32 Half = 1; Half <= 40; ++Half)
        {
            const bool Whole = Half % 2 == 0, Major = Half % 10 == 0;
            if (!Whole && HalfOpacity < .01f) continue;
            const float Length = (Major ? 4.5f : Whole ? 2.5f : 1.45f) * Pixel;
            const float Angle = Half * .0005f;
            for (int32 Axis = 0; Axis < 2; ++Axis)
            {
                const float Distance = (Axis == 0 ? Focal.X : Focal.Y) * FMath::Tan(Angle);
                if (Distance > End * .70f) continue;
                for (int32 Sign : {-1, 1})
                {
                    const FVector2f At = Axis == 0 ? FVector2f(Sign * Distance, 0) : FVector2f(0, Sign * Distance);
                    const FVector2f Along = Axis == 0 ? FVector2f(0, Length) : FVector2f(Length, 0);
                    Pen.Line(At - Along, At + Along, Major ? .95f : .75f, Whole ? 1.f : HalfOpacity);
                }
            }
        }
    }
    const auto Resource = FSlateApplication::Get().GetRenderer()->GetResourceHandle(*FCoreStyle::Get().GetBrush(TEXT("WhiteBrush")));
    FSlateDrawElement::MakeCustomVerts(Out, Layer, Resource, Cache.Vertices, Cache.Indices, nullptr, 0, 0);

    // Labels are angular readings only; no fabricated distance or drop values.
    if (HasScale && FMath::Min(OneMil.X, OneMil.Y) >= 3.5f * Pixel)
    {
        const float S = FMath::Min(Size.X, Size.Y) / 900.f;
        auto Font = FCoreStyle::GetDefaultFontStyle("Regular", FMath::Max(7, FMath::RoundToInt(8.f * S)));
        Font.OutlineSettings.OutlineSize = 1;
        Font.OutlineSettings.OutlineColor = FLinearColor(.80f, .82f, .80f, .30f * Alpha);
        static const TCHAR* Labels[] = {TEXT("5"), TEXT("10"), TEXT("15"), TEXT("20")};
        for (int32 Index = 0; Index < 4; ++Index)
        {
            const float Angle = (Index + 1) * .005f;
            const FVector2f At = Focal * FMath::Tan(Angle);
            if (At.X < End * .70f)
                for (int32 Sign : {-1, 1})
                    FSlateDrawElement::MakeText(Out, Layer + 1,
                        Geometry.ToPaintGeometry(FVector2f(24, 16), FSlateLayoutTransform(Center + FVector2f(Sign * At.X + 3.f * Pixel, 7.f * Pixel))),
                        Labels[Index], Font, ESlateDrawEffect::None, FLinearColor(.015f, .018f, .016f, .85f * Alpha));
            if (At.Y < End * .70f)
                FSlateDrawElement::MakeText(Out, Layer + 1,
                    Geometry.ToPaintGeometry(FVector2f(24, 16), FSlateLayoutTransform(Center + FVector2f(8.f * Pixel, At.Y - 5.f * Pixel))),
                    Labels[Index], Font, ESlateDrawEffect::None, FLinearColor(.015f, .018f, .016f, .85f * Alpha));
        }
    }
}
