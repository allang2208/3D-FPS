#pragma once
#include "CoreMinimal.h"

struct FGeometry;
struct FStatusEffectView;
class FSlateWindowElementList;

namespace ColdSteelUI
{
    // Original code-native icons. Tribute images are intentionally handled by the existing widget.
    int32 PaintStatusEffectIcon(const FGeometry& Geometry, FSlateWindowElementList& Out,
        int32 Layer, FVector2D Offset, float Size, const FStatusEffectView& View, const FLinearColor& Tint);
}
