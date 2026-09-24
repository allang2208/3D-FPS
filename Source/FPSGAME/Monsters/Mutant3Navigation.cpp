#include "MonsterAIController.h"
#include "Mutant3.h"
#include "WolfMonster.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationData.h"
#include "NavigationPath.h"
#include "NavigationSystem.h"

bool AMonsterAIController::NavigateFeralTo(FVector Destination, float Acceptance, APawn* VisibleTarget)
{
    auto* Mutant = Cast<AMutant3>(GetPawn());
    auto* Canine = Cast<AWolfMonster>(GetPawn());
    auto* Hunter = Cast<ACharacter>(GetPawn());
    if (!Hunter || (!Mutant && (!Canine || !Canine->bUsePredictiveHunting))) return false;
    const float AttackRange = Mutant ? Mutant->GetClawStartDistance() : Canine->BiteTriggerRange;
    const auto CanReach = [&](const FVector& From, float Range)
    {
        return Mutant ? Mutant->CanClawFrom(VisibleTarget, From, Range)
            : Canine->CanBiteFrom(VisibleTarget, From, Range);
    };
    const bool Moving = GetMoveStatus() == EPathFollowingStatus::Moving;
    const float Now = GetWorld()->GetTimeSeconds();
    if (Now-LastMove < .65f) return Moving;
    const bool Blocked = Moving && Hunter->GetVelocity().Size2D() < 25.f;
    if (Moving && !Blocked && FVector::DistSquared(Destination, LastDestination) < FMath::Square(45.f))
        return true;

    LastMove = Now;
    LastDestination = Destination;
    ++NavigationRequests;
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const auto& Agent = GetNavAgentPropertiesRef();
    const FVector Feet = Hunter->GetNavAgentLocation();
    const auto* Data = Nav ? Nav->GetNavDataForProps(Agent, Feet) : nullptr;
    if (!Data)
    {
        StopMovement();
        bNavigationFailed = true;
        return false;
    }

    const FVector CenterOffset = Hunter->GetActorLocation()-Feet;
    FNavLocation Goal;
    const bool Projected = Nav->ProjectPointToNavigation(Destination, Goal, FVector(100,100,100), Data);
    // Keep a still-advancing path. Retry a stalled one after the normal request
    // interval, even if the target has not moved (the old shortcut held forever).
    if ((!Blocked || !VisibleTarget) && Projected)
    {
        // Acceptance is measured against the real target, not a nav projection
        // that may already be up to 100 cm closer to the approaching monster.
        float Reach = FMath::Max(5.f, Acceptance-FVector::Dist2D(Goal.Location, Destination));
        if (VisibleTarget && !CanReach(Goal.Location+CenterOffset, AttackRange)) Reach = 5.f;
        const auto Result = MoveToLocation(Goal.Location, Reach, false, true, false, false, nullptr, false);
        if (Result == EPathFollowingRequestResult::RequestSuccessful)
        {
            bNavigationFailed = false;
            return true;
        }
        if (Result == EPathFollowingRequestResult::AlreadyAtGoal &&
            (!VisibleTarget || CanReach(Hunter->GetActorLocation(), AttackRange)))
        {
            bNavigationFailed = false;
            return false;
        }
    }

    // A blocked approach or unusable projected goal needs an actual attack
    // position. Only accept complete paths on this agent's navmesh, at a height
    // and distance that can hit the target with a clear line of sight.
    bool Found = false;
    FVector BestGoal = FVector::ZeroVector;
    double BestCost = TNumericLimits<double>::Max();
    if (IsValid(VisibleTarget))
    {
        FVector Away = (Feet-Destination).GetSafeNormal2D();
        if (Away.IsNearlyZero()) Away = -Hunter->GetActorForwardVector();
        const float RingRadius = FMath::Max(65.f, AttackRange-40.f);
        const auto* Capsule = Hunter->GetCapsuleComponent();
        FCollisionQueryParams Params(SCENE_QUERY_STAT(Mutant3Approach), false, Hunter);
        Params.AddIgnoredActor(VisibleTarget);
        const FCollisionResponseParams Response(Capsule->GetCollisionResponseToChannels());
        const FCollisionShape Shape = FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),
            Capsule->GetScaledCapsuleHalfHeight()-2.f);
        FVector OldGoal = FVector::ZeroVector;
        const auto OldPath = GetPathFollowingComponent()->GetPath();
        const bool HadPath = OldPath.IsValid() && !OldPath->GetPathPoints().IsEmpty();
        if (HadPath) OldGoal = OldPath->GetPathPoints().Last().Location;
        for (float Angle : {0.f, 45.f, -45.f, 90.f, -90.f, 135.f, -135.f, 180.f})
        {
            const FVector Candidate = Destination+Away.RotateAngleAxis(Angle, FVector::UpVector)*RingRadius;
            FNavLocation Point;
            if (!Nav->ProjectPointToNavigation(Candidate, Point, FVector(65,65,60), Data) ||
                !CanReach(Point.Location+CenterOffset, AttackRange-10.f)) continue;
            FPathFindingQuery Query(this, *Data, Feet, Point.Location, Data->GetDefaultQueryFilter());
            Query.SetAllowPartialPaths(false);
            const FPathFindingResult Path = Nav->FindPathSync(Agent, Query);
            if (!Path.IsSuccessful() || !Path.Path.IsValid() || Path.Path->IsPartial()) continue;
            // Navmesh paths alone do not account for every blocking pawn or
            // newly closed obstacle. Reject a first step the capsule cannot take.
            const auto& Points = Path.Path->GetPathPoints();
            FVector Next = Point.Location;
            for (const auto& Step : Points)
                if (FVector::Dist2D(Step.Location, Feet) > 5.f) { Next = Step.Location; break; }
            const FVector Step = (Next-Feet).GetClampedToMaxSize(90.f);
            FHitResult Hit;
            if (GetWorld()->SweepSingleByChannel(Hit, Hunter->GetActorLocation(),
                Hunter->GetActorLocation()+Step, FQuat::Identity, Capsule->GetCollisionObjectType(), Shape, Params, Response)) continue;
            double Cost = Path.Path->GetLength();
            if (Blocked && HadPath && FVector::Dist2D(Point.Location, OldGoal) < 65.f) Cost += 300.f;
            if (Cost < BestCost) { BestCost = Cost; BestGoal = Point.Location; Found = true; }
        }
    }
    if (Found)
    {
        const auto Result = MoveToLocation(BestGoal, 10.f, false, true, false, false, nullptr, false);
        if (Result != EPathFollowingRequestResult::Failed)
        {
            bNavigationFailed = false;
            return Result == EPathFollowingRequestResult::RequestSuccessful;
        }
    }
    StopMovement();
    bNavigationFailed = true;
    return false;
}
