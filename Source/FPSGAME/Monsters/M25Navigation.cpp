#include "VortexCofferM25.h"
#include "M25BiteComponent.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "../Combat/CombatStatusFormula.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationSystem.h"
#include "NavigationData.h"

bool AVortexCofferM25::SearchDestination(FVector& Destination)
{
    if (!HasAuthority() || !HasActorBegunPlay() || !bSearchForPlayers || Dead() || Controlled()
        || !IsActorTickEnabled() || CombatTarget.IsValid()) return false;
    const auto* AI = Cast<AMonsterAIController>(GetController());
    if (!AI || !AI->bDecisionEnabled || (Combat && Combat->IsBusy())) return false;
    const auto* Status = FindComponentByClass<UCombatStatusFormula>();
    if (Status && (Status->IsFrozen() || Status->IsStunned() || Status->IsPetrified())) return false;
    const double Now = GetWorld()->GetTimeSeconds();
    const FVector Feet = GetNavAgentLocation();
    if (bHasSearchGoal)
    {
        const bool Reached = FVector::DistSquared2D(Feet, SearchGoal) <= FMath::Square(75.f)
            && FMath::Abs(Feet.Z - SearchGoal.Z) <= 50.f;
        if (!Reached && Now < SearchGoalDeadline) { Destination = SearchGoal; return true; }
        bHasSearchGoal = false;
        NextSearchAt = Now + .6;
        return false;
    }
    if (Now < NextSearchAt) return false;
    // A failed nav query is retried by this BT task at a bounded cadence.
    NextSearchAt = Now + 2.;
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const auto& Agent = GetCharacterMovement()->GetNavAgentPropertiesRef();
    auto* Data = Nav ? Nav->GetNavDataForProps(Agent, Feet) : nullptr;
    if (!Data) return false;
    const FVector HomeFeet = Home - (GetActorLocation() - Feet);
    FNavLocation Center;
    if (!Nav->ProjectPointToNavigation(HomeFeet, Center,
        FVector(Agent.AgentRadius * 2.f + 30.f, Agent.AgentRadius * 2.f + 30.f, 100.f), Data)) return false;
    const float Radius = FMath::Clamp(SearchRadius, 300.f, FMath::Max(300.f, LeashRadius * .75f));
    for (int32 Attempt = 0; Attempt < 3; ++Attempt)
    {
        FNavLocation Goal;
        if (!Nav->GetRandomReachablePointInRadius(Center.Location, Radius, Goal, Data)) continue;
        const float Distance = FVector::Dist2D(Feet, Goal.Location);
        if (Distance < 300.f || FMath::Abs(Goal.Location.Z - HomeFeet.Z) > 100.f) continue;
        SearchGoal = Goal.Location;
        SearchGoalDeadline = Now + 5. + Distance / FMath::Max(1.f, WalkSpeed) * 1.8;
        bHasSearchGoal = true;
        Destination = SearchGoal;
        return true;
    }
    return false;
}

void AVortexCofferM25::DeferSearch()
{
    bHasSearchGoal = false;
    NextSearchAt = GetWorld()->GetTimeSeconds() + 2.;
}

void AVortexCofferM25::FaceNearbyTarget(APawn* Target, float DeltaSeconds)
{
    if (!HasAuthority() || !IsValid(Target) || Dead() || Controlled() || (Bite && Bite->IsBusy())) return;
    const auto* Status = FindComponentByClass<UCombatStatusFormula>();
    if (Status && (Status->IsFrozen() || Status->IsStunned() || Status->IsPetrified())) return;
    // Close targets behind the creature must not leave it parked facing away
    // indefinitely while the independent back spell continues to fire.
    const FVector Direction = Target->GetActorLocation() - GetActorLocation();
    if (Direction.IsNearlyZero()) return;
    const FRotator Facing(0.f, Direction.Rotation().Yaw, 0.f);
    SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(), Facing, DeltaSeconds,
        FMath::Max(1.f, GetCharacterMovement()->RotationRate.Yaw)));
}
