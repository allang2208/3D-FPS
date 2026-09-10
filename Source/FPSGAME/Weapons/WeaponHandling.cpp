#include "WeaponHandling.h"

FWeaponHandling FWeaponHandling::FromIndices(double Recoil, double Shake)
{
    FWeaponHandling R;
    R.RecoilIndex = FMath::IsFinite(Recoil) ? FMath::Clamp(Recoil, 0., 400.) : 100.;
    R.ShakeIndex = FMath::IsFinite(Shake) ? FMath::Clamp(Shake, 0., 400.) : 100.;
    R.RecoilScale = R.RecoilIndex / 100.f;
    R.ShakeScale = R.ShakeIndex / 100.f;
    // Speed the complete oscillator up, keeping its damping ratio unchanged.
    R.RecoveryTimeScale = FMath::Sqrt(FMath::Clamp(R.ShakeScale, .25f, 4.f));
    // Fixed, cross-weapon calibration v1: equal weight for amplitude and time.
    // This is a game rating, not a claimed empirical accuracy percentage.
    R.Stability = R.ShakeScale == 0.f ? 100.f
        : 100.f / (1.f + .5f * R.ShakeScale + .5f * R.RecoveryTimeScale);
    return R;
}

FVector2D FWeaponHandling::Pattern(int32 ShotIndex)
{
    static const FVector2D Points[] = {
        {.009f, 0.f}, {.012f, -.002f}, {.015f, .0025f},
        {.018f, -.0015f}, {.020f, .003f}, {.022f, -.002f},
        {.024f, .002f}, {.026f, -.001f}, {.028f, .0005f}
    };
    return Points[FMath::Clamp(ShotIndex, 0, PatternCount - 1)];
}

float FWeaponHandling::FirstShotDegrees() const
{ return FMath::RadiansToDegrees(Pattern(0).X) * ReferenceBallisticScale * RecoilScale; }
float FWeaponHandling::MaxVerticalDegrees() const
{ return FMath::RadiansToDegrees(Pattern(PatternCount - 1).X) * ReferenceBallisticScale * RecoilScale; }
float FWeaponHandling::ADSRecoveryMilliseconds() const
{ return ShakeScale == 0.f ? 0.f : 2000.f * FMath::Loge(10.f) / (CameraDamping + CameraADSDamping) * RecoveryTimeScale; }
