#pragma once

#include "CoreMinimal.h"
#include "Widgets/SLeafWidget.h"

namespace ColdSteelQuickSlotFX
{
    constexpr float KeyPeriod = 1.2f;
    constexpr float MaskTransition = .05f;
    constexpr float FlashDuration = .6f;
    float KeyOpacity(float Elapsed);
    float FlashOpacity(float Elapsed);
}

/** Source quick-bar CSS: top-anchored black mask, clipped to the rounded slot. */
class SColdSteelCooldownMask : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelCooldownMask) : _CornerRadius(7.f) {}
        SLATE_ARGUMENT(float, CornerRadius)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args);
    void SetFraction(float Value);
    virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D::ZeroVector; }
    virtual int32 OnPaint(const FPaintArgs&, const FGeometry&, const FSlateRect&,
        FSlateWindowElementList&, int32, const FWidgetStyle&, bool) const override;
private:
    FSlateBrush Brush;
    float Fraction = 0.f;
};
