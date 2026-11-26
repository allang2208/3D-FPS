#pragma once

#include "Widgets/SLeafWidget.h"
#include "Styling/SlateBrush.h"

class UTexture2D;

/** The atlas contains the first half of the approved 60-frame pulse for each direction. */
class SColdSteelEffectArrow final : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SColdSteelEffectArrow) : _Atlas(nullptr), _Gain(true), _PixelScale(1.f) {}
        SLATE_ARGUMENT(UTexture2D*, Atlas)
        SLATE_ARGUMENT(bool, Gain)
        SLATE_ARGUMENT(float, PixelScale)
    SLATE_END_ARGS()

    void Construct(const FArguments& Args);
    virtual FVector2D ComputeDesiredSize(float) const override;
    virtual int32 OnPaint(const FPaintArgs&, const FGeometry&, const FSlateRect&,
        FSlateWindowElementList&, int32, const FWidgetStyle&, bool) const override;

private:
    mutable FSlateBrush FrameBrush;
    int32 FirstTile = 0;
    float PixelScale = 1.f;
};
