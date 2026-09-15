#include "SColdSteelCooldownMask.h"
#include "ColdSteelUIStyle.h"
#include "Layout/Clipping.h"
#include "Rendering/DrawElementTypes.h"

namespace
{
// CSS cubic-bezier(x1, 0, x2, 1): solve its time coordinate before evaluating Y.
float CssEase(float Time, float X1, float X2)
{
    if (Time <= 0.f) return 0.f;
    if (Time >= 1.f) return 1.f;
    float Low = 0.f, High = 1.f;
    for (int32 I = 0; I < 12; ++I)
    {
        const float T = (Low + High) * .5f, U = 1.f - T;
        const float X = 3.f * U * U * T * X1 + 3.f * U * T * T * X2 + T * T * T;
        if (X < Time) Low = T; else High = T;
    }
    const float T = (Low + High) * .5f;
    return T * T * (3.f - 2.f * T);
}
}

float ColdSteelQuickSlotFX::KeyOpacity(float Elapsed)
{
    const float Phase = FMath::Fmod(Elapsed,KeyPeriod) / KeyPeriod;
    return Phase < .5f ? FMath::Lerp(1.f,.4f,CssEase(Phase * 2.f,.42f,.58f))
        : FMath::Lerp(.4f,1.f,CssEase((Phase - .5f) * 2.f,.42f,.58f));
}

float ColdSteelQuickSlotFX::FlashOpacity(float Elapsed)
{
    return .8f * (1.f - CssEase(Elapsed / FlashDuration,0.f,.58f));
}

void SColdSteelCooldownMask::Construct(const FArguments& Args)
{
    Brush = ColdSteelUI::RoundedBrush(FLinearColor(0,0,0,.65f),Args._CornerRadius,FLinearColor::Transparent,0);
    SetVisibility(EVisibility::HitTestInvisible);
}

void SColdSteelCooldownMask::SetFraction(float Value)
{
    Value = FMath::Clamp(Value,0.f,1.f);
    if (Fraction == Value) return;
    Fraction = Value;
    Invalidate(EInvalidateWidgetReason::Paint);
}

int32 SColdSteelCooldownMask::OnPaint(const FPaintArgs&, const FGeometry& Geometry, const FSlateRect&,
    FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle& Style, bool) const
{
    if (Fraction <= 0.f) return Layer;
    const FVector2f Size = Geometry.GetLocalSize();
    // Clip a full-size rounded brush so its corners are not stretched with CD height.
    Elements.PushClip(FSlateClippingZone(Geometry.ToPaintGeometry(
        FVector2f(Size.X,Size.Y * Fraction),FSlateLayoutTransform())));
    FSlateDrawElement::MakeBox(Elements,Layer,Geometry.ToPaintGeometry(),&Brush,
        ESlateDrawEffect::None,Brush.GetTint(Style)*Style.GetColorAndOpacityTint());
    Elements.PopClip();
    return Layer;
}
