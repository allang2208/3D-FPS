#include "FPSTraversalRules.h"

bool UFPSTraversalSettings::IsValidConfiguration() const
{
    const float Values[] = {StepHeight, VaultMaxHeight, MantleMaxHeight, VaultMaxDepth,
        MantleMinDepth, MaxEdgeDistance, MaxFacingAngle, MaxLandingDrop, MaxLandingRise, HoldToTraverseTime};
    for (float Value : Values) if (!FMath::IsFinite(Value) || Value < 0.f) return false;
    return StepHeight < VaultMaxHeight && VaultMaxHeight < MantleMaxHeight &&
        VaultMaxDepth > 0.f && MantleMinDepth > 0.f && MaxEdgeDistance > 0.f &&
        HoldToTraverseTime > 0.f && MaxFacingAngle > 0.f && MaxFacingAngle < 90.f;
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
    const EFPSTraversalAction HeightClass = ClassifyHeight(P.Height);
    // Step is a height classification, not an instruction to override CMC stepping.
    if (HeightClass == EFPSTraversalAction::None || HeightClass == EFPSTraversalAction::Step)
        return HeightClass;
    if (!P.bJumpPressed || !P.bStandingGrounded || !P.bTraversalAvailable || !P.bStaticObstacle ||
        !P.bApproachClear || !P.bTopWalkable || !FMath::IsFinite(P.Depth) || P.Depth <= 0.f ||
        !FMath::IsFinite(P.EdgeDistance) || P.EdgeDistance < 0.f || P.EdgeDistance > MaxEdgeDistance ||
        !FMath::IsFinite(P.FacingDot) || P.FacingDot > 1.f ||
        P.FacingDot < FMath::Cos(FMath::DegreesToRadians(MaxFacingAngle)))
        return EFPSTraversalAction::None;

    const bool bLandingHeightOK = FMath::IsFinite(P.LandingHeightDelta) &&
        P.LandingHeightDelta >= -MaxLandingDrop && P.LandingHeightDelta <= MaxLandingRise;
    if (HeightClass == EFPSTraversalAction::Vault && P.Depth <= VaultMaxDepth &&
        P.bVaultPathClear && P.bLandingStandingSpace && bLandingHeightOK)
        return EFPSTraversalAction::Vault;

    // A broad low platform, or a blocked far side, may still allow climbing onto its top.
    if (P.Depth >= MantleMinDepth && P.bTopStandingSpace && P.bMantlePathClear)
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
