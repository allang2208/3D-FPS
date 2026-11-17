#pragma once

#include "CoreMinimal.h"
class UTextureRenderTarget2D;

// Synchronous GPU readback for offline map bakes and diagnostics only.
namespace ColdSteelMapReadback
{
    bool ReadPhoto(UTextureRenderTarget2D* Target, TArray<FColor>& Pixels);
}
