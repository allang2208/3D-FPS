#include "SColdSteelEffectArrow.h"
#include "Engine/Texture2D.h"
#include "Rendering/DrawElements.h"
#include "Types/PaintArgs.h"

void SColdSteelEffectArrow::Construct(const FArguments& Args)
{
    PixelScale = Args._PixelScale;
    FirstTile = Args._Gain ? 0 : 32;
    FrameBrush.DrawAs = ESlateBrushDrawType::Image;
    FrameBrush.SetResourceObject(Args._Atlas);
    SetVisibility(EVisibility::HitTestInvisible);
    SetCanTick(false);
    ForceVolatile(true);
}

FVector2D SColdSteelEffectArrow::ComputeDesiredSize(float) const
{
    return FVector2D(18,18) / PixelScale;
}

int32 SColdSteelEffectArrow::OnPaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect&,
    FSlateWindowElementList& Out, int32 Layer, const FWidgetStyle& Style, bool ParentEnabled) const
{
    constexpr int32 FrameCount = 60;
    constexpr double Period = 2.4;
    const int32 Step = FMath::FloorToInt32(FMath::Fmod(Args.GetCurrentTime(), Period) * FrameCount / Period);
    const int32 Tile = FirstTile + FMath::Min(Step, FrameCount - Step);
    const FVector2f MinUV((Tile % 8) / 8.f, (Tile / 8) / 8.f);
    FrameBrush.SetUVRegion(FBox2f(MinUV, MinUV + FVector2f(.125f,.125f)));
    // Transparent room around the glyph holds the soft halo without moving the number.
    const FVector2f Size(44.f / PixelScale,44.f / PixelScale);
    const FVector2f Offset = (FVector2f(Geometry.GetLocalSize()) - Size) * .5f;
    FSlateDrawElement::MakeBox(Out, Layer, Geometry.ToPaintGeometry(Size, FSlateLayoutTransform(Offset)),
        &FrameBrush, ParentEnabled ? ESlateDrawEffect::None : ESlateDrawEffect::DisabledEffect,
        Style.GetColorAndOpacityTint());
    return Layer;
}
