#pragma once

#include "CoreMinimal.h"

class UBowWeaponComponent;
class FSlateWindowElementList;
class FWidgetStyle;
struct FGeometry;

namespace ColdSteelBowRhythm
{
inline constexpr float TrackY=64.f;
int32 Paint(const UBowWeaponComponent& Bow, const FGeometry& Geometry,
    FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle& Style, float PixelToLocal);
}
