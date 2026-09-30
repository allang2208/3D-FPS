#pragma once

#include "CoreMinimal.h"

class FPreviewScene;
class USceneCaptureComponent2D;

namespace GunsmithPreviewLighting
{
    void Create(FPreviewScene& Scene, USceneCaptureComponent2D& Capture);
    // Bounds are in capture space and include the complete visible assembly.
    void Update(USceneCaptureComponent2D& Capture, const FBox& ViewBounds, bool bGraphite201 = false);
}
