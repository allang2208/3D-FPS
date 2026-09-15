#include "SAttachmentSelectionPulse.h"
#include "ColdSteelUIStyle.h"
#include "Rendering/DrawElementTypes.h"
#include "Styling/CoreStyle.h"

void SAttachmentSelectionPulse::Construct(const FArguments& Args)
{
    Active = Args._Active;
    SetVisibility(EVisibility::HitTestInvisible);
    SetCanTick(true);
}

void SAttachmentSelectionPulse::Tick(const FGeometry& Geometry, double CurrentTime, float DeltaTime)
{
    SLeafWidget::Tick(Geometry,CurrentTime,DeltaTime);
    const bool bActive = Active.Get();
    if (bPlaying != bActive)
    {
        bPlaying = bActive;
        Elapsed = 0.f;
        Invalidate(EInvalidateWidgetReason::PaintAndVolatility);
    }
    if (bPlaying)
    {
        Elapsed = FMath::Fmod(Elapsed + DeltaTime,2.4f);
        Invalidate(EInvalidateWidgetReason::Paint);
    }
}

int32 SAttachmentSelectionPulse::OnPaint(const FPaintArgs&, const FGeometry& Geometry, const FSlateRect&,
    FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle& Style, bool bParentEnabled) const
{
    if (!bPlaying || !bParentEnabled) return Layer;
    const FVector2f Size = Geometry.GetLocalSize();
    if (Size.X <= 16.f || Size.Y <= 16.f) return Layer;
    const float Travel = FMath::Clamp(Elapsed / 1.95f,0.f,1.f);
    const float Head = FMath::Lerp(-.2f * Size.X,1.65f * Size.X,Travel);
    const auto Weight = [Head,Size](float X)
    {
        const float Distance = X - Head;
        const float Width = Size.X * (Distance < 0.f ? .20f : .045f);
        return FMath::Exp(-.5f * FMath::Square(Distance / FMath::Max(1.f,Width)));
    };
    const FLinearColor Tint = Style.GetColorAndOpacityTint();
    auto Band = [&](float Y,float Height,float Alpha,int32 Z)
    {
        const float BandWidth = Size.X-16.f;
        TArray<FSlateGradientStop> Stops;
        constexpr int32 Samples = 40;
        Stops.Reserve(Samples+1);
        for (int32 Index=0; Index<=Samples; ++Index)
        {
            const float X = BandWidth * Index / Samples;
            const float Strength = Weight(X+8.f);
            FLinearColor Color = FMath::Lerp(ColdSteelUI::Success,ColdSteelUI::TextPrimary,Strength * .38f);
            Color.A = Alpha * Strength;
            Stops.Emplace(FVector2f(X,0),Color * Tint);
        }
        // Slate's vertical strip orientation interpolates the stops along X.
        FSlateDrawElement::MakeGradient(Elements,Layer+Z,
            Geometry.ToPaintGeometry(FVector2f(BandWidth,Height),FSlateLayoutTransform(FVector2f(8.f,Y))),
            MoveTemp(Stops),Orient_Vertical,ESlateDrawEffect::None,FVector4f(Height*.5f));
    };
    Band(0,6.f,.10f,0);
    Band(Size.Y-6.f,6.f,.14f,0);
    Band(0,1.5f,.78f,1);
    Band(Size.Y-2.f,2.f,.94f,1);
    for (const float X : {0.f,Size.X-1.5f})
    {
        FLinearColor Color = ColdSteelUI::Success;
        Color.A = .7f * Weight(X);
        FSlateDrawElement::MakeBox(Elements,Layer+1,
            Geometry.ToPaintGeometry(FVector2f(1.5f,Size.Y-16.f),FSlateLayoutTransform(FVector2f(X,8.f))),
            FCoreStyle::Get().GetBrush("WhiteBrush"),ESlateDrawEffect::None,Color * Tint);
    }
    return Layer+1;
}
