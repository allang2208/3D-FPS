#pragma once
#include "CoreMinimal.h"

class UBowWeaponComponent;
class FSlateWindowElementList;
class FWidgetStyle;
struct FGeometry;

namespace ColdSteelBowResonance
{
struct FCueLayout
{
    float Width, Top;
    float Height() const { return Width/3.f; }
    float ExperienceOffset() const { return Top+Height()+15.f; }
    float Scale(const FVector2D& HalfView,float PixelToLocal) const
    {
        return FMath::Min(PixelToLocal,float(FMath::Min(HalfView.X/(Width*.5f+8.f),
            HalfView.Y/FMath::Max(132.f,Top+Height()+8.f))));
    }
};
// Anchor the top edge below the reticle, so enlarging the gauge extends it downward.
inline constexpr FCueLayout LightPillarLayout{240.f,96.f};
inline constexpr FCueLayout CadenceLayout{160.f,68.f};
int32 Paint(const UBowWeaponComponent& Bow,const FGeometry& Geometry,
    FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,float PixelToLocal);
}
