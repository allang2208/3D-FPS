#pragma once
#include "CoreMinimal.h"

class UStarMarrowComponent;
class FSlateWindowElementList;
class FWidgetStyle;
struct FGeometry;

namespace ColdSteelStarMarrow
{
inline constexpr float BarTopOffset=172.f;
inline constexpr float ExperienceOffset=BarTopOffset+112.f;
inline float LayoutScale(float PixelToLocal,float HalfHeight)
{return FMath::Min(PixelToLocal,HalfHeight/(BarTopOffset+136.f));}
int32 Paint(const UStarMarrowComponent& Core,const FGeometry& Geometry,
    FSlateWindowElementList& Elements,int32 Layer,const FWidgetStyle& Style,float PixelToLocal);
}
