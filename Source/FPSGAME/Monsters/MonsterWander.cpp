#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "LurkerM08Monster.h"
#include "HangingBellM09.h"
#include "BehaviorTree/BlackboardComponent.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "Engine/World.h"
#include "CoreGlobals.h"

namespace
{
// AI tasks run on the game thread. Bound new idle route work across all monsters,
// including physical surface probes; no actor scans, manager tick or extra timer.
bool TakeWanderQuerySlot()
{
    static uint64 Frame = MAX_uint64;
    static uint8 Queries = 0;
    if (Frame != GFrameCounter) { Frame = GFrameCounter; Queries = 0; }
    if (Queries >= 2) return false;
    ++Queries;
    return true;
}
}

void AMonsterAIController::StopWander()
{
    if (!bWanderActive) return;
    bWanderActive = bWanderMoving = false;
    StopMovement();
    if (auto* M08 = Cast<ALurkerM08Monster>(GetPawn())) M08->StopSurfaceNavigation();
    if (auto* M09 = Cast<AHangingBellM09>(GetPawn())) M09->StopCeiling();
    if (auto* C = Combat(); C && !C->IsBusy()) C->SetLocomotion(false);
    // Combat must be free to request its first path immediately after this abort.
    LastMove = -100.f;
    NextWanderMove = GetWorld()->GetTimeSeconds() + WanderRandom.FRandRange(1.5f, 4.5f);
    NextWanderUpdate = 0.f;
}

void AMonsterAIController::PauseWander(float Now, bool Failed)
{
    bWanderMoving = false;
    StopMovement();
    if (auto* M08 = Cast<ALurkerM08Monster>(GetPawn())) M08->StopSurfaceNavigation();
    if (auto* M09 = Cast<AHangingBellM09>(GetPawn())) M09->StopCeiling();
    Combat()->SetLocomotion(false);
    WanderFailures = Failed ? FMath::Min<int32>(WanderFailures + 1, 4) : 0;
    const float Delay = Failed ? WanderRandom.FRandRange(.8f, 1.5f) * WanderFailures
        : WanderRandom.FRandRange(1.5f, 4.5f);
    NextWanderMove = Now + Delay;
    ActiveAction = Failed ? TEXT("Wander: waiting for a clear route") : TEXT("Wander: pause");
}

bool AMonsterAIController::ChooseWanderDestination()
{
    APawn* MonsterPawn = GetPawn();
    auto* C = Combat();
    auto* M08 = Cast<ALurkerM08Monster>(MonsterPawn);
    auto* M09 = Cast<AHangingBellM09>(MonsterPawn);
    const FVector Position = MonsterPawn->GetActorLocation();
    const FVector Normal = M08 && M08->bSurfaceAttached ? M08->SurfaceNormal : FVector::UpVector;
    const float Radius = FMath::Min(FMath::Max(100.f, WanderRadius), FMath::Max(100.f, C->LeashRange() * .7f));
    FVector Heading = FVector::VectorPlaneProject(MonsterPawn->GetActorForwardVector(), Normal).GetSafeNormal();
    if (Heading.IsNearlyZero()) Heading = FVector::CrossProduct(MonsterPawn->GetActorRightVector(), Normal).GetSafeNormal();
    // Near the home boundary favour an inward stroll rather than bouncing off it.
    if (FVector::DistSquared(Position, C->Home()) > FMath::Square(Radius * .7f))
    {
        const FVector Inward = FVector::VectorPlaneProject(C->Home() - Position, Normal).GetSafeNormal();
        if (!Inward.IsNearlyZero()) Heading = Inward;
    }
    const float Angle = WanderFailures > 0 || WanderRandom.FRand() < .2f
        ? WanderRandom.FRandRange(-180.f, 180.f) : WanderRandom.FRandRange(-80.f, 80.f);
    const float Distance = WanderRandom.FRandRange(FMath::Min(200.f, Radius * .35f), FMath::Min(500.f, Radius * .65f));
    const FVector Desired = Position + Heading.RotateAngleAxis(Angle, Normal) * Distance;
    if (FVector::DistSquared(Desired, C->Home()) > FMath::Square(Radius)) return false;

    // These species travel on physical walls/ceilings, never on the ground mesh.
    if (M08) return M08->TryWanderSurface(Desired, WanderGoal);
    if (M09) return M09->TryWanderCeiling(Desired, WanderGoal);

    const auto* MonsterCharacter = Cast<ACharacter>(MonsterPawn);
    if (!MonsterCharacter || !MonsterCharacter->GetCharacterMovement()->IsMovingOnGround()) return false;
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const FVector Feet = MonsterPawn->GetNavAgentLocation();
    const auto& Agent = GetNavAgentPropertiesRef();
    const auto* Data = Nav ? Nav->GetNavDataForProps(Agent, Feet) : nullptr;
    FNavLocation Goal;
    const FVector DesiredFeet = Desired - (Position - Feet);
    const float Extent = FMath::Max(80.f, Agent.AgentRadius);
    if (!Data || !Nav->ProjectPointToNavigation(DesiredFeet, Goal, FVector(Extent, Extent, 75.f), Data)) return false;
    const FVector HomeFeet = C->Home() - (Position - Feet);
    if (FVector::DistSquared2D(Goal.Location, HomeFeet) > FMath::Square(Radius)
        || FMath::Abs(Goal.Location.Z - HomeFeet.Z) > 100.f
        || FVector::DistSquared2D(Goal.Location, Feet) < FMath::Square(100.f)) return false;
    // One full path request establishes reachability. Do not accept a partial
    // path or issue a second random-reachable flood search for the same point.
    ++NavigationRequests;
    C->SetLocomotion(true);
    const auto Result = MoveToLocation(Goal.Location, 45.f, false, true, false, false, nullptr, false);
    bNavigationFailed = Result == EPathFollowingRequestResult::Failed;
    if (Result != EPathFollowingRequestResult::RequestSuccessful) return false;
    WanderGoal = Goal.Location + (Position - Feet);
    return true;
}

void AMonsterAIController::TickWander()
{
    APawn* MonsterPawn = GetPawn();
    auto* C = Combat();
    const auto* B = GetBlackboardComponent();
    if (!HasAuthority() || !MonsterPawn || !C || !B || !bDecisionEnabled || !MonsterPawn->IsActorTickEnabled()
        || C->IsBusy() || bReturning || B->GetValueAsBool(TEXT("HasTarget")))
    { StopWander(); return; }
    const float Now = GetWorld()->GetTimeSeconds();
    if (Now < NextWanderUpdate) return;
    NextWanderUpdate = Now + .2f;
    if (!bWanderActive)
    {
        bWanderActive = true;
        StopMovement();
        C->SetLocomotion(false);
        ActiveAction = TEXT("Wander: pause");
    }
    if (bWanderMoving)
    {
        const FVector Position = MonsterPawn->GetActorLocation();
        const bool SpecialMovement = MonsterPawn->IsA<ALurkerM08Monster>() || MonsterPawn->IsA<AHangingBellM09>();
        const bool Reached = FVector::DistSquared(Position, WanderGoal) <= FMath::Square(55.f);
        if (Reached) { PauseWander(Now, false); return; }
        if ((!SpecialMovement && GetMoveStatus() == EPathFollowingStatus::Idle) || Now > WanderDeadline)
        { PauseWander(Now, true); return; }
        if (FVector::DistSquared(Position, WanderProgressPosition) > FMath::Square(20.f))
        { WanderProgressPosition = Position; WanderProgressTime = Now; }
        else if (Now - WanderProgressTime > 4.f) { PauseWander(Now, true); return; }
        return;
    }
    if (Now < NextWanderMove) return;
    if (!TakeWanderQuerySlot())
    { NextWanderUpdate = Now + WanderRandom.FRandRange(.08f, .3f); return; }
    if (!ChooseWanderDestination()) { PauseWander(Now, true); return; }
    bWanderMoving = true;
    WanderFailures = 0;
    WanderProgressPosition = MonsterPawn->GetActorLocation();
    WanderProgressTime = Now;
    const auto* MonsterCharacter = Cast<ACharacter>(MonsterPawn);
    const float Speed = MonsterCharacter ? MonsterCharacter->GetCharacterMovement()->GetMaxSpeed() : 40.f;
    WanderDeadline = Now + FMath::Clamp(float(FVector::Distance(WanderGoal, WanderProgressPosition)) / FMath::Max(20.f, Speed) * 2.f + 5.f, 12.f, 60.f);
    ActiveAction = TEXT("Wander: moving at 50%");
}
