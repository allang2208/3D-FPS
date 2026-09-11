#include "FPSTraversalRulesAuditCommandlet.h"
#include "FPSTraversalRules.h"
#include "../FPSGAMECharacter.h"
#include "GameFramework/CharacterMovementComponent.h"
int32 AuditFPSTraversalWorld();

int32 UFPSTraversalRulesAuditCommandlet::Main(const FString& Params)
{
    const auto* Rules = GetDefault<UFPSTraversalSettings>();
    int32 Checks = 0, Failures = 0;
    const auto Check = [&](const TCHAR* Name, bool Pass)
    {
        ++Checks; if (!Pass) ++Failures;
        UE_LOG(LogTemp, Display, TEXT("TRAVERSAL_RULE %s %s"), Pass ? TEXT("PASS") : TEXT("FAIL"), Name);
    };
    using A = EFPSTraversalAction;
    Check(TEXT("config_valid"), Rules->IsValidConfiguration());
    Check(TEXT("step_matches_character"), Rules->StepHeight == GetDefault<AFPSGAMECharacter>()->GetCharacterMovement()->MaxStepHeight);
    for (const auto& Pair : TArray<TPair<float, A>>{{-1.f,A::None},{0.f,A::None},{49.9f,A::Step},{50.f,A::Step},
        {50.1f,A::Vault},{119.9f,A::Vault},{120.f,A::Vault},{120.1f,A::Mantle},{199.9f,A::Mantle},{200.f,A::Mantle},{200.1f,A::None}})
        Check(*FString::Printf(TEXT("height_%.1f"), Pair.Key), Rules->ClassifyHeight(Pair.Key) == Pair.Value);
    FFPSTraversalProbe P;
    P.Height=100.f; P.Depth=60.f; P.EdgeDistance=6.f; P.FacingDot=1.f;
    Check(TEXT("unset_probe_rejected"), Rules->Evaluate(P)==A::None);
    P.bJumpPressed=P.bStandingGrounded=P.bTraversalAvailable=P.bStaticObstacle=true;
    P.bApproachClear=P.bTopWalkable=P.bVaultPathClear=P.bLandingStandingSpace=true;
    Check(TEXT("thin_low_wall_vault"),Rules->Evaluate(P)==A::Vault);
    auto Q=P; Q.Depth=200.f; Q.bTopStandingSpace=Q.bMantlePathClear=true;
    Check(TEXT("wide_low_platform_mantle"),Rules->Evaluate(Q)==A::Mantle);
    Q.Height=180.f;
    Check(TEXT("high_platform_mantle"),Rules->Evaluate(Q)==A::Mantle);
    Q.bTopStandingSpace=false;
    Check(TEXT("blocked_top_rejected"),Rules->Evaluate(Q)==A::None);
    Q=P; Q.Height=180.f;
    Check(TEXT("high_thin_wall_rejected"),Rules->Evaluate(Q)==A::None);
    Q=P; Q.LandingHeightDelta=-60.f;
    Check(TEXT("drop_limit_inclusive"),Rules->Evaluate(Q)==A::Vault);
    Q.LandingHeightDelta=-60.1f;
    Check(TEXT("unsafe_drop_rejected"),Rules->Evaluate(Q)==A::None);
    Q=P; Q.LandingHeightDelta=50.f;
    Check(TEXT("rise_limit_inclusive"),Rules->Evaluate(Q)==A::Vault);
    Q.LandingHeightDelta=50.1f;
    Check(TEXT("unsafe_rise_rejected"),Rules->Evaluate(Q)==A::None);
    Q=P; Q.EdgeDistance=20.f;
    Check(TEXT("distance_limit_inclusive"),Rules->Evaluate(Q)==A::Vault);
    Q.EdgeDistance=20.1f;
    Check(TEXT("too_far_rejected"),Rules->Evaluate(Q)==A::None);
    Q=P; Q.FacingDot=FMath::Cos(FMath::DegreesToRadians(40.f));
    Check(TEXT("angle_limit_inclusive"),Rules->Evaluate(Q)==A::Vault);
    Q.FacingDot=FMath::Cos(FMath::DegreesToRadians(41.f));
    Check(TEXT("sideways_rejected"),Rules->Evaluate(Q)==A::None);
    for (bool FFPSTraversalProbe::* Flag : {&FFPSTraversalProbe::bJumpPressed,&FFPSTraversalProbe::bStandingGrounded,
        &FFPSTraversalProbe::bTraversalAvailable,&FFPSTraversalProbe::bStaticObstacle,&FFPSTraversalProbe::bApproachClear,
        &FFPSTraversalProbe::bTopWalkable,&FFPSTraversalProbe::bVaultPathClear,&FFPSTraversalProbe::bLandingStandingSpace})
    {
        Q=P; Q.*Flag=false;
        Check(TEXT("missing_required_condition_rejected"),Rules->Evaluate(Q)==A::None);
    }
    Q=P; Q.Depth=120.f;
    Check(TEXT("vault_depth_inclusive"),Rules->Evaluate(Q)==A::Vault);
    Q.Depth=120.1f;
    Check(TEXT("vault_depth_over_rejected_without_top"),Rules->Evaluate(Q)==A::None);
    Q=P; Q.bLandingStandingSpace=false; Q.Depth=100.f; Q.bTopStandingSpace=Q.bMantlePathClear=true;
    Check(TEXT("blocked_far_side_mantle_fallback"),Rules->Evaluate(Q)==A::Mantle);
    Q.Depth=99.9f;
    Check(TEXT("insufficient_top_depth_rejected"),Rules->Evaluate(Q)==A::None);
    UE_LOG(LogTemp,Display,TEXT("TRAVERSAL_RULE_RESULT checks=%d failures=%d"),Checks,Failures);
    return (Failures + AuditFPSTraversalWorld()) ? 1 : 0;
}
