#pragma once

#include "CoreMinimal.h"
#include "Widgets/SLeafWidget.h"

/** Decorative, input-transparent sweep on the selected attachment's frame. */
class SAttachmentSelectionPulse : public SLeafWidget
{
public:
    SLATE_BEGIN_ARGS(SAttachmentSelectionPulse) : _Active(false) {}
        SLATE_ATTRIBUTE(bool, Active)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args);
    virtual void Tick(const FGeometry& Geometry, double CurrentTime, float DeltaTime) override;
    virtual FVector2D ComputeDesiredSize(float) const override { return FVector2D::ZeroVector; }
    virtual bool ComputeVolatility() const override { return bPlaying; }
    virtual int32 OnPaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& CullingRect,
        FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle& Style, bool bParentEnabled) const override;
private:
    TAttribute<bool> Active;
    float Elapsed = 0.f;
    bool bPlaying = false;
};
