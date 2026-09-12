#include "FPSTraversalRules.h"

bool UFPSTraversalSettings::IsValidConfiguration() const
{
    const float Values[] = {StepHeight, VaultMaxHeight, MantleMaxHeight, VaultMaxDepth,
        MaxEdgeDistance, MaxFacingAngle, MaxLandingDrop, MaxLandingRise, VaultPlaybackRate,
        AirMinLedgeHeight,AirMaxLedgeHeight,AirMaxFallSpeed,AirMaxLandingDrop};
    for (float Value : Values) if (!FMath::IsFinite(Value) || Value < 0.f) return false;
    return StepHeight < VaultMaxHeight && VaultMaxHeight < MantleMaxHeight &&
        VaultMaxDepth > 0.f && MaxEdgeDistance > 0.f &&
        VaultPlaybackRate > 0.f && MaxFacingAngle > 0.f && MaxFacingAngle < 90.f &&
        AirMinLedgeHeight > 0.f && AirMinLedgeHeight < AirMaxLedgeHeight &&
        AirMaxFallSpeed > 0.f && AirMaxLandingDrop > 0.f;
}

EFPSTraversalAction UFPSTraversalSettings::ClassifyHeight(float Height) const
{
    if (!IsValidConfiguration() || !FMath::IsFinite(Height) || Height <= 0.f || Height > MantleMaxHeight)
        return EFPSTraversalAction::None;
    if (Height <= StepHeight) return EFPSTraversalAction::Step;
    if (Height <= VaultMaxHeight) return EFPSTraversalAction::Vault;
    return EFPSTraversalAction::Mantle;
}

EFPSTraversalAction UFPSTraversalSettings::Evaluate(const FFPSTraversalProbe& P) const
{
    EFPSTraversalAction HeightClass = ClassifyHeight(P.Height);
    if (P.bAirborne)
    {
        if (!IsValidConfiguration() || !FMath::IsFinite(P.Height) ||
            P.Height<AirMinLedgeHeight || P.Height>AirMaxLedgeHeight || !P.bAirReachable)
            return EFPSTraversalAction::None;
        HeightClass=P.Height<=VaultMaxHeight?EFPSTraversalAction::Vault:EFPSTraversalAction::Mantle;
    }
    // Step is a height classification, not an instruction to override CMC stepping.
    if (HeightClass == EFPSTraversalAction::None || HeightClass == EFPSTraversalAction::Step)
        return HeightClass;
    if (!P.bJumpPressed || (!P.bStandingGrounded && !P.bAirborne) || !P.bTraversalAvailable || !P.bStableObstacle ||
        !P.bApproachClear || !P.bTopGrippable || !FMath::IsFinite(P.Depth) || P.Depth <= 0.f ||
        !FMath::IsFinite(P.EdgeDistance) || P.EdgeDistance < 0.f || P.EdgeDistance > MaxEdgeDistance ||
        !FMath::IsFinite(P.FacingDot) || P.FacingDot > 1.f ||
        P.FacingDot < FMath::Cos(FMath::DegreesToRadians(MaxFacingAngle)))
        return EFPSTraversalAction::None;

    const bool bLandingHeightOK = FMath::IsFinite(P.LandingHeightDelta) &&
        P.LandingHeightDelta >= -(P.bAirborne?AirMaxLandingDrop:MaxLandingDrop) && P.LandingHeightDelta <= MaxLandingRise;
    if (HeightClass == EFPSTraversalAction::Vault && P.Depth <= VaultMaxDepth &&
        P.bVaultPathClear && P.bLandingStandingSpace && bLandingHeightOK)
        return EFPSTraversalAction::Vault;

    // A broad low platform, or a blocked far side, may still allow climbing onto its top.
    // Actual support and capsule clearance decide whether a top is usable;
    // the front component's thickness does not describe a modular platform.
    if (P.bTopStandingSpace && P.bMantlePathClear)
        return EFPSTraversalAction::Mantle;
    return EFPSTraversalAction::None;
}

EFPSTraversalAction UFPSTraversalRules::ClassifyObstacleHeight(float Height)
{
    return GetDefault<UFPSTraversalSettings>()->ClassifyHeight(Height);
}

EFPSTraversalAction UFPSTraversalRules::EvaluateObstacle(const FFPSTraversalProbe& Probe)
{
    return GetDefault<UFPSTraversalSettings>()->Evaluate(Probe);
}
