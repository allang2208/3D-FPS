#pragma once
#include "CoreMinimal.h"
#include "WarhammerQuickReferenceCamera.h"

// V8: reference butt strike. Pose, camera, cue and contact use one real clock.
namespace WarhammerQuickCombat
{
    inline constexpr float Length=1.30f;
    inline constexpr float Prepare=.15f;
    inline constexpr float Contact=28.f/120.f;
    inline constexpr float Follow=34.f/120.f;
    inline constexpr float Entry=.06f;
    inline constexpr float QueryRadiusCM=32.f;
    inline constexpr const TCHAR* Asset=TEXT("/Game/Weapons/SteelWarhammer20261014/QuickReferenceV8/A_Warhammer_QuickReferenceV8.A_Warhammer_QuickReferenceV8");

    inline float SourceSeconds(float Age)
    {
        return FMath::Clamp(Age,0.f,Length);
    }

    inline void Camera(float Age,FVector& Location,FRotator& Rotation)
    {
        Location=FVector::ZeroVector;
        // Measured image-space motion already includes the source's sway.
        // Normalize for the shared default .45 presentation multiplier.
        Rotation=WarhammerQuickReferenceCamera::Sample(SourceSeconds(Age))*(1.f/.45f);
    }
}
