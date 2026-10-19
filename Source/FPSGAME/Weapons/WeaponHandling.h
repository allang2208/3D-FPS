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
    static constexpr float ADSJitterMultiplier = 0.45f;
    static constexpr float MinimumRecoveryTimeScale = 0.25f;

    float RecoilIndex = 100.f;
    float ShakeIndex = 100.f;
    float RecoilScale = 1.f;
    float ShakeScale = 1.f;
    float RecoveryTimeScale = 1.f;
    float Stability = 50.f;
    // 武器系数（1 = 参考枪）：连点扩散的增速/上限，以及移动与滞空带来的后坐力放大。
    // 由 `spread_growth_mult` / `recoil_load_mult` 驱动，用于"耐用"型武器不因连续或移动射击劣化。
    float SpreadGrowthScale = 1.f;
    float RecoilLoadScale = 1.f;

    static FWeaponHandling FromIndices(double Recoil, double Shake, double StabilityMultiplier = 1.);
    // Temporary stance bonus on the already-composed rating, without mutating
    // equipment stats or re-clamping its effective shake index as raw input.
    FWeaponHandling WithStabilityMultiplier(double Multiplier) const;
    static FVector2D Pattern(int32 ShotIndex);
    static constexpr int32 PatternCount = 9;
    float RecoveryRate() const { return 1.f / RecoveryTimeScale; }
    float FirstShotDegrees() const;
    float MaxVerticalDegrees() const;
    float ADSHorizontalDegrees(int32 ShotIndex) const;
    float FirstHorizontalDegrees() const { return FMath::Abs(ADSHorizontalDegrees(0)); }
    float MaxHorizontalDegrees() const;
    // 90% decay of the ADS camera spring envelope, not return of control aim.
    float ADSRecoveryMilliseconds() const;
};
