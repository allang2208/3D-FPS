#pragma once
#include "CoreMinimal.h"

namespace SprintCameraMotion
{
    // 2026-10-13: halve sprint camera translation and rotation across all weapons.
    // Keep authored motion, stride phase, action timing and layer crossfades intact.
    inline constexpr float AmplitudeScale=.5f;

    inline float LocomotionScale(float SprintBlend)
    {
        return FMath::Lerp(1.f,AmplitudeScale,FMath::Clamp(SprintBlend,0.f,1.f));
    }
}
