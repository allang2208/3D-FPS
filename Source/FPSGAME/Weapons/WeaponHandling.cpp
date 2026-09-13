#include "WeaponHandling.h"

FWeaponHandling FWeaponHandling::FromIndices(double Recoil, double Shake, double StabilityMultiplier)
{
    FWeaponHandling R;
    R.RecoilIndex = FMath::IsFinite(Recoil) ? FMath::Clamp(Recoil, 0., 400.) : 100.;
    R.ShakeIndex = FMath::IsFinite(Shake) ? FMath::Clamp(Shake, 0., 400.) : 100.;
    R.RecoilScale = R.RecoilIndex / 100.f;
    R.ShakeScale = R.ShakeIndex / 100.f;
    // Retain the reference calibration (100 shake -> 50 points) and the
    // sqrt relation between amplitude and spring time. Keep the scoring curve
    // continuous down to zero shake; the physical time floor is applied below.
    const double BaseStability = 100. / (1. + .5 * R.ShakeScale + .5 * FMath::Sqrt(R.ShakeScale));
    const double Multiplier = FMath::IsFinite(StabilityMultiplier) ? StabilityMultiplier : 1.;
    const double Target = FMath::Clamp(BaseStability * Multiplier, 0., 100.);

    // Below the legacy 400-shake boundary (25 points), continue the inverse
    // curve along its tangent. This reaches zero points with finite feedback,
    // matching both the value and slope at 25 instead of dividing by zero.
    constexpr double Boundary = 25.;
    const double Severity = Target >= Boundary ? 100. / Target - 1.
        : 100. / Boundary - 1. + (Boundary - Target) * 100. / (Boundary * Boundary);
    // Solve x*x + x = 2*Severity, where x is sqrt(shake amplitude).
    // This equivalent root avoids subtracting near-equal numbers at 100 points.
    const double Root = 4. * Severity / (FMath::Sqrt(1. + 8. * Severity) + 1.);
    R.ShakeScale = Root * Root;
    R.ShakeIndex = R.ShakeScale * 100.f;
    R.RecoveryTimeScale = FMath::Max(MinimumRecoveryTimeScale, static_cast<float>(Root));
    R.Stability = Target;
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
{ return 2000.f * FMath::Loge(10.f) / (CameraDamping + CameraADSDamping) * RecoveryTimeScale; }

float FWeaponHandling::ADSHorizontalDegrees(int32 ShotIndex) const
{
    // Repeatable lateral recoil, not random projectile spread. Positive yaw is right.
    static constexpr float Degrees[]={.18f,.24f,-.30f,-.36f,.42f,.48f,-.54f,-.60f,.60f};
    return Degrees[FMath::Max(0,ShotIndex)%UE_ARRAY_COUNT(Degrees)]*RecoilScale;
}
float FWeaponHandling::MaxHorizontalDegrees() const
{
    float Result=0.f;
    for(int32 I=0;I<PatternCount;++I)Result=FMath::Max(Result,FMath::Abs(ADSHorizontalDegrees(I)));
    return Result;
}
