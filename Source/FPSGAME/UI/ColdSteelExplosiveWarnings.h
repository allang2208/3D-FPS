#pragma once
#include "CoreMinimal.h"
class APlayerController;
struct FGeometry;
class FSlateWindowElementList;
namespace ColdSteelExplosiveWarnings
{
    int32 Paint(APlayerController* Player, const FGeometry& Geometry,
        FSlateWindowElementList& Elements, int32 Layer, const FLinearColor& Tint);
}
