#pragma once
#include "CoreMinimal.h"

// Shared by catalog, equipped pawn and UI. Indices describe gameplay, not a
// screen-shake preference. The reference weapon is 100 recoil / 100 shake.
struct FWeaponHandling
{
    static constexpr float ReferenceBallisticScale = 0.70f;
    static constexpr float CameraStiffness = 170.f;
    static constexpr float CameraDamping = 15.f;
    static constexpr float CameraADSDamping = 8.f;

    float RecoilIndex = 100.f;
    float ShakeIndex = 100.f;
    float RecoilScale = 1.f;
    float ShakeScale = 1.f;
    float RecoveryTimeScale = 1.f;
    float Stability = 50.f;

    static FWeaponHandling FromIndices(double Recoil, double Shake);
    static FVector2D Pattern(int32 ShotIndex);
    static constexpr int32 PatternCount = 9;
    float RecoveryRate() const { return 1.f / RecoveryTimeScale; }
    float FirstShotDegrees() const;
    float MaxVerticalDegrees() const;
    // 90% decay of the ADS camera spring envelope, not return of control aim.
    float ADSRecoveryMilliseconds() const;
};
