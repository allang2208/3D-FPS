#pragma once

#include "Widgets/SLeafWidget.h"
#include "Styling/SlateBrush.h"

// Crisp ColdSteel tactical portrait plate with subtle studio scrim, smooth hover zoom, and optional corner brackets.
class SHorseMarketPlate final : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SHorseMarketPlate)
        : _Sharp(nullptr), _Soft(nullptr), _PreferredHeight(154.f), _CornerRadius(5.f), _ShowScrim(true), _CornerBrackets(false), _PortraitFocus(FVector2f(.46f, .14f)) {}
        SLATE_ARGUMENT(const FSlateBrush*, Sharp)
        SLATE_ARGUMENT(const FSlateBrush*, Soft)
        SLATE_ARGUMENT(float, PreferredHeight)
        SLATE_ARGUMENT(float, CornerRadius)
        SLATE_ARGUMENT(bool, ShowScrim)
        SLATE_ARGUMENT(bool, CornerBrackets)
        SLATE_ARGUMENT(FVector2f, PortraitFocus)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args);
    void SetReveal(float Value);
    void SetSelected(bool Value);
    void SetMuted(bool Value);
    virtual FVector2D ComputeDesiredSize(float Scale) const override { return FVector2D(80.f, PreferredHeight); }
    virtual int32 OnPaint(const FPaintArgs&, const FGeometry& Geometry, const FSlateRect&,
        FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle& Style, bool Enabled) const override;
private:
    const FSlateBrush* Sharp=nullptr;
    const FSlateBrush* Soft=nullptr;
    float PreferredHeight=154.f;
    float CornerRadius=5.f;
    float Reveal=0.f;
    FVector2f PortraitFocus=FVector2f(.46f,.14f);
    bool bShowScrim=true;
    bool bCornerBrackets=false;
    bool bSelected=false;
    bool bMuted=false;
};
