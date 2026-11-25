#pragma once

#include "Widgets/SLeafWidget.h"
#include "Styling/SlateBrush.h"

// Draw only the curved photo area, leaving the card surface visible around its shoulder.
class SHorseMarketPlate final : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SHorseMarketPlate) {}
        SLATE_ARGUMENT(const FSlateBrush*, Sharp)
        SLATE_ARGUMENT(const FSlateBrush*, Soft)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args);
    void SetReveal(float Value);
    virtual FVector2D ComputeDesiredSize(float Scale) const override { return FVector2D(80,174); }
    virtual int32 OnPaint(const FPaintArgs&, const FGeometry& Geometry, const FSlateRect&,
        FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle& Style, bool Enabled) const override;
private:
    const FSlateBrush* Sharp=nullptr;
    const FSlateBrush* Soft=nullptr;
    float Reveal=0;
};
