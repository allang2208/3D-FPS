#include "MantisM27Monster.h"
#include "../Skills/IlluminationMarkComponent.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Components/CapsuleComponent.h"
#include "CoreGlobals.h"
#include "Navigation/PathFollowingComponent.h"
#include "NavigationData.h"
#include "NavigationPath.h"
#include "NavigationSystem.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"

void AMantisM27Monster::NotifyCloakEncounter(APawn* Victim)
{
    if (!HasAuthority() || !HasActorBegunPlay() || bEncounterCloakUsed || !IsValid(Victim) || Health <= 0.f) return;
    bEncounterCloakUsed = true;
    SetCloaked(true);
}

float AMantisM27Monster::TakeDamage(float Damage, const FDamageEvent& Event, AController* EventInstigator, AActor* Causer)
{
    const float Before = Health;
    const float Applied = Super::TakeDamage(Damage, Event, EventInstigator, Causer);
    if (!HasAuthority()) return Applied;
    if (Applied > 0.f && Health > 0.f && GetWorld()->GetTimeSeconds()-LastMantisHurtAudioAt >= .22)
    {
        LastMantisHurtAudioAt = GetWorld()->GetTimeSeconds();
        MulticastMantisAccent(TEXT("Hurt"), ServerClock());
    }
    if (Health <= 0.f)
    {
        SetCloaked(false);
        RestoreCloakVisuals();
    }
    else if (Applied > 0.f && !bInjuryCloakUsed && Before > MaxHealth * CloakInjuryThreshold && Health <= MaxHealth * CloakInjuryThreshold)
    {
        bInjuryCloakUsed = true;
        // A half-health hit during the opening cloak spends the second charge
        // and refreshes its retreat, without an opaque flash between charges.
        SetCloaked(true);
    }
    return Applied;
}

void AMantisM27Monster::RevealByIllumination()
{
    if(!HasAuthority())return;
    ActiveAttackDamageScale=1.f;SetCloaked(false);RestoreCloakVisuals();
}
void AMantisM27Monster::SetCloaked(bool Enabled)
{
    if (!HasAuthority()) return;
    if(Enabled&&UIlluminationMarkComponent::IsMarked(this))return;
    if (Enabled)
    {
        CancelPounce();
        ActiveAttackDamageScale = 1.f;
        if (!bCloaked) UncloakedMoveSpeed = GetCharacterMovement()->MaxWalkSpeed;
        CloakStartedAt = GetWorld()->GetTimeSeconds();
        bCloakAttackCommitted = false;
        ResetCloakNavigation();
        CloakOrbitDirection = (GetUniqueID() & 1) ? 1.f : -1.f;
        bContactConsumed = true;
        CancelAttackForLocomotion(); // Keep existing stuns and knockdowns intact.
        GetCharacterMovement()->MaxWalkSpeed = CloakMoveSpeed;
        if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->StopMovement();
    }
    else if (bCloaked)
    {
        ResetCloakNavigation();
        GetCharacterMovement()->MaxWalkSpeed = UncloakedMoveSpeed;
        if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->StopMovement();
    }
    const bool Changed = bCloaked != Enabled;
    bCloaked = Enabled;
    if (Changed)
    {
        OnRep_Cloaked(); ForceNetUpdate();
        if (Health > 0.f && State != ENurseState::Dead)
            MulticastMantisAccent(Enabled ? TEXT("CloakEnter") :
                ActiveAttackDamageScale > 1.f ? TEXT("ShadowBreak") : TEXT("CloakExit"), ServerClock());
    }
}

void AMantisM27Monster::OnRep_Cloaked()
{
    if (bCloaked) PrepareCloakVisuals();
    else RestoreCloakVisuals(); // Attack starts fully visible on every peer.
}

bool AMantisM27Monster::IsCloakRecoveryReady() const
{
    return !bCloaked || bCloakAttackCommitted;
}

void AMantisM27Monster::BeginShadowStrike()
{
    ActiveAttackDamageScale = bCloaked ? ShadowStrikeMultiplier : 1.f;
    SetCloaked(false);
    RestoreCloakVisuals();
}

void AMantisM27Monster::PrepareCloakVisuals()
{
    if (bCloakVisualsApplied || GetNetMode() == NM_DedicatedServer || !CloakMaterial) return;
    auto* BodyMesh = GetMesh();
    if (!CloakInstance) CloakInstance = UMaterialInstanceDynamic::Create(CloakMaterial, this);
    if (!CloakInstance) return;
    UncloakedMaterials.Reset();
    for (int32 Slot = 0; Slot < BodyMesh->GetNumMaterials(); ++Slot) UncloakedMaterials.Add(BodyMesh->GetMaterial(Slot));
    bUncloakedCastsShadow = BodyMesh->CastShadow;
    if (!CloakShadow)
    {
        CloakShadow = NewObject<USkeletalMeshComponent>(this, TEXT("M27CloakShadow"));
        CloakShadow->SetupAttachment(BodyMesh);
        CloakShadow->SetSkeletalMeshAsset(BodyMesh->GetSkeletalMeshAsset());
        CloakShadow->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        CloakShadow->SetGenerateOverlapEvents(false);
        CloakShadow->SetCanEverAffectNavigation(false);
        CloakShadow->SetLeaderPoseComponent(BodyMesh);
        CloakShadow->bUseBoundsFromLeaderPoseComponent = true;
        CloakShadow->SetRenderInMainPass(false);
        CloakShadow->SetRenderInDepthPass(false);
        CloakShadow->SetHiddenInGame(true);
        CloakShadow->SetCastHiddenShadow(true);
        CloakShadow->RegisterComponent();
    }
    for (int32 Slot = 0; Slot < UncloakedMaterials.Num(); ++Slot)
    {
        CloakShadow->SetMaterial(Slot, UncloakedMaterials[Slot]);
        BodyMesh->SetMaterial(Slot, CloakInstance);
    }
    // Opaque, pose-following geometry owns the shadow during translucency.
    // It adds no independent animation evaluation or collision body.
    CloakShadow->SetCastShadow(bUncloakedCastsShadow);
    BodyMesh->SetCastShadow(false);
    CloakInstance->SetScalarParameterValue(TEXT("CloakAmount"), CloakBlend);
    bCloakVisualsApplied = true;
}

void AMantisM27Monster::RestoreCloakVisuals()
{
    if (!bCloakVisualsApplied) return;
    for (int32 Slot = 0; Slot < UncloakedMaterials.Num(); ++Slot) GetMesh()->SetMaterial(Slot, UncloakedMaterials[Slot]);
    GetMesh()->SetCastShadow(bUncloakedCastsShadow);
    if (CloakShadow) CloakShadow->SetCastShadow(false);
    CloakBlend = 0.f;
    bCloakVisualsApplied = false;
}

void AMantisM27Monster::TickCloak(float DeltaSeconds)
{
    if (Health <= 0.f || State == ENurseState::Dead)
    {
        if (HasAuthority()) CancelPounce();
        if (HasAuthority() && bCloaked) SetCloaked(false);
        RestoreCloakVisuals();
        return;
    }
    if (HasAuthority() && bCloaked)
    {
        Health = FMath::Min(MaxHealth, Health + MaxHealth * CloakHealFractionPerSecond * DeltaSeconds);
        if (!bCloakAttackCommitted && GetWorld()->GetTimeSeconds() - CloakStartedAt >= CloakMinimumSeconds &&
            Health >= MaxHealth * CloakRecoveryThreshold)
        {
            bCloakAttackCommitted = true;
            ResetCloakNavigation();
            // Drop the escape route once, then let the existing tree pick a
            // pounce or a real melee approach. Do not wait to hit full health.
            if (auto* AI = Cast<AMonsterAIController>(GetController()))
            {
                AI->StopMovement();
                AI->UpdateKnowledge();
            }
        }
        // Regenerated hunters approach/choose a pounce while concealed. The
        // attack itself breaks cloak and captures its one-attack bonus.
        if (!CombatTarget() && IsCloakRecoveryReady())
            SetCloaked(false);
    }
    if (!bCloaked && !bCloakVisualsApplied) return;
    if (bCloaked && !bCloakVisualsApplied) PrepareCloakVisuals();
    const float NextBlend = FMath::FInterpConstantTo(CloakBlend, bCloaked ? 1.f : 0.f, DeltaSeconds, 1.f / FMath::Max(.01f, CloakFadeSeconds));
    if (CloakInstance && NextBlend != CloakBlend) CloakInstance->SetScalarParameterValue(TEXT("CloakAmount"), NextBlend);
    CloakBlend = NextBlend;
    if (!bCloaked && CloakBlend <= 0.f) RestoreCloakVisuals();
}

namespace
{
// Recovery is uncommon but several hunters may cloak on the same damage frame.
// At most one bounded candidate batch / four full path queries per frame.
bool TakeCloakRouteSlot()
{
    static uint64 Frame = MAX_uint64;
    if (Frame == GFrameCounter) return false;
    Frame = GFrameCounter;
    return true;
}

struct FCloakCandidate
{
    FVector Feet;
    double Score;
};
}

void AMantisM27Monster::ResetCloakNavigation()
{
    bHasCloakRoute = false;
    CloakGoal = FVector::ZeroVector;
    CloakProgressFeet = GetNavAgentLocation();
    CloakProgressAt = CloakNavigationTickAt = GetWorld()->GetTimeSeconds();
    CloakRouteDeadline = CloakFailedGoalUntil = NextCloakGoalAt = 0.;
    CloakRouteSearchPass = 0;
    CloakBlockedAttempts = 0;
}

void AMantisM27Monster::CounterattackFromBlockedCloak(AMonsterAIController* AI)
{
    if (!HasAuthority() || !bCloaked || !AI || !Combat || Combat->IsBusy()) return;
    // Being trapped is an explicit early exit, independent of minimum cloak
    // time and healing. A legal attack still owns its existing shadow bonus.
    bCloakAttackCommitted = true;
    ResetCloakNavigation();
    AI->StopMovement();
    Combat->SetLocomotion(false);
    if (Combat->TryAttack(CombatTarget()))
    {
        AI->ActiveAction = TEXT("M27: trapped / shadow counterattack");
    }
    else
    {
        // A cooldown, wall or distant victim must not keep us regenerating in
        // place. Reveal now and let normal pursuit choose the next legal attack.
        // No stored bonus is granted to a later unrelated visible attack.
        ActiveAttackDamageScale = 1.f;
        SetCloaked(false);
        RestoreCloakVisuals();
        AI->ActiveAction = TEXT("M27: trapped / revealed pursuit");
    }
    AI->UpdateKnowledge();
}

bool AMantisM27Monster::ChooseCloakRoute(AMonsterAIController* AI, const FVector& TargetFeet)
{
    TRACE_CPUPROFILER_EVENT_SCOPE(M27_ChooseCloakRoute);
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const FVector Feet = GetNavAgentLocation();
    const auto& Agent = AI->GetNavAgentPropertiesRef();
    const auto* Data = Nav ? Nav->GetNavDataForProps(Agent, Feet) : nullptr;
    if (!Data) return false;
    const double Now = GetWorld()->GetTimeSeconds();
    const auto* Capsule = GetCapsuleComponent();
    const float Radius = Capsule->GetScaledCapsuleRadius();
    const float HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
    const float StepHeight = GetCharacterMovement()->MaxStepHeight;
    const FVector CenterOffset = GetActorLocation() - Feet;
    const FCollisionShape Body = FCollisionShape::MakeCapsule(Radius, FMath::Max(Radius, HalfHeight - 2.f));
    FCollisionQueryParams Params(SCENE_QUERY_STAT(M27CloakRoute), false, this);
    const FCollisionResponseParams Response(Capsule->GetCollisionResponseToChannels());
    const ECollisionChannel Channel = Capsule->GetCollisionObjectType();
    FVector Away = (Feet - TargetFeet).GetSafeNormal2D();
    if (Away.IsNearlyZero()) Away = -GetActorForwardVector().GetSafeNormal2D();
    const FVector Tangent = Away.RotateAngleAxis(90.f * CloakOrbitDirection, FVector::UpVector);
    const double Distance = FVector::Dist2D(Feet, TargetFeet);
    const bool Retreating = Now - CloakStartedAt < .85 || Distance < CloakOrbitRadius * .85;
    const FVector Heading = Retreating ? Away : (Tangent + Away * .2).GetSafeNormal2D();
    // The shared hunter chase may already have travelled beyond its home leash.
    // Do not clamp a local escape all the way across the room to the spawn point.
    const double HomeLimit = FMath::Max(double(Combat->LeashRange() - 180.f), FVector::Dist2D(Feet, Combat->Home()) + 100.);
    const float LongStep = FMath::Clamp(CloakOrbitRadius * .5f, 240.f, 400.f);
    TArray<FCloakCandidate, TInlineAllocator<24>> Candidates;
    for (float Travel : {LongStep, 180.f, 90.f})
    {
        for (float Angle : {0.f, 45.f, -45.f, 90.f, -90.f, 135.f, -135.f, 180.f})
        {
            // Sample around the hunter's own floor, not a distant player's floor.
            const FVector Desired = Feet + Heading.RotateAngleAxis(Angle, FVector::UpVector) * Travel;
            FNavLocation Point;
            const float XY = FMath::Max(35.f, Radius);
            if (!Nav->ProjectPointToNavigation(Desired, Point, FVector(XY, XY, StepHeight + 25.f), Data)) continue;
            const double Moved = FVector::Dist2D(Feet, Point.Location);
            if (Moved < 60. || FMath::Abs(Point.Location.Z - Feet.Z) > StepHeight + 25.f ||
                FVector::Dist2D(Point.Location, Combat->Home()) > HomeLimit) continue;
            bool Duplicate = false;
            for (const auto& Candidate : Candidates)
                if (FVector::DistSquared(Candidate.Feet, Point.Location) < FMath::Square(35.f)) { Duplicate = true; break; }
            if (Duplicate || GetWorld()->OverlapBlockingTestByChannel(Point.Location + CenterOffset,
                FQuat::Identity, Channel, Body, Params, Response)) continue;
            const double Separation = FVector::Dist2D(Point.Location, TargetFeet);
            const double Lateral = FVector::DotProduct((Point.Location - Feet).GetSafeNormal2D(), Tangent);
            double Score = Retreating ? (Separation - Distance) * 2. + Moved * .15
                : -FMath::Abs(Separation - CloakOrbitRadius) + Lateral * 140. + Moved * .1;
            // Temporarily avoid the same obstructed destination, but do not
            // permanently blacklist the only exit after a blocking pawn moves.
            if (Now < CloakFailedGoalUntil && FVector::Dist2D(Point.Location, CloakFailedGoal) < 100.) Score -= 1000.;
            Candidates.Add({Point.Location, Score});
        }
    }
    Candidates.Sort([](const FCloakCandidate& A, const FCloakCandidate& B) { return A.Score > B.Score; });
    if (Candidates.IsEmpty()) return false;
    // If the best four were unreachable, admit the next four on the next batch.
    // A disconnected attractive point cannot starve a nearby sideways escape.
    const int32 Offset = (int32(CloakRouteSearchPass) * 4) % Candidates.Num();
    const int32 Count = FMath::Min(4, Candidates.Num());
    for (int32 Index = 0; Index < Count; ++Index)
    {
        const FVector Goal = Candidates[(Offset + Index) % Candidates.Num()].Feet;
        FPathFindingQuery Query(AI, *Data, Feet, Goal, Data->GetDefaultQueryFilter());
        Query.SetAllowPartialPaths(false);
        ++AI->NavigationRequests;
        const FPathFindingResult Path = Nav->FindPathSync(Agent, Query);
        if (!Path.IsSuccessful() || !Path.Path.IsValid() || Path.Path->IsPartial()) continue;
        // A local sidestep must not become a long tour around a disconnected
        // wall/landing merely because its endpoint is nearby in straight line.
        if (Path.Path->GetLength() > FMath::Max(450., FVector::Dist2D(Feet, Goal) * 3.)) continue;
        FVector FirstStep = Goal;
        for (const auto& Point : Path.Path->GetPathPoints())
            if (FVector::Dist2D(Point.Location, Feet) > 5.) { FirstStep = Point.Location; break; }
        const FVector Delta = (FirstStep - Feet).GetClampedToMaxSize(75.f);
        // Leave the walking step band to CharacterMovement so a valid stair
        // riser is not mistaken for a full-height wall. Pawns remain blockers.
        const FVector Start = GetActorLocation() + FVector(0, 0, StepHeight * .5f);
        const FCollisionShape WalkingBody = FCollisionShape::MakeCapsule(Radius,
            FMath::Max(Radius, HalfHeight - StepHeight * .5f - 2.f));
        FHitResult Hit;
        if (GetWorld()->SweepSingleByChannel(Hit, Start, Start + Delta, FQuat::Identity,
            Channel, WalkingBody, Params, Response)) continue;
        FAIMoveRequest Request(Goal);
        Request.SetAcceptanceRadius(25.f);
        Request.SetReachTestIncludesAgentRadius(false);
        Request.SetReachTestIncludesGoalRadius(false);
        Request.SetAllowPartialPath(false);
        Request.SetProjectGoalLocation(false);
        // Follow the complete path already computed; no second path search.
        if (!AI->RequestMove(Request, Path.Path).IsValid()) continue;
        CloakGoal = Goal;
        bHasCloakRoute = true;
        CloakProgressFeet = Feet;
        CloakProgressAt = Now;
        CloakRouteDeadline = Now + FMath::Clamp(Path.Path->GetLength() /
            FMath::Max(20.f, GetCharacterMovement()->GetMaxSpeed()) * 2. + 1., 2., 8.);
        CloakRouteSearchPass = 0;
        AI->bNavigationFailed = false;
        return true;
    }
    ++CloakRouteSearchPass;
    return false;
}

void AMantisM27Monster::NavigateWhileCloaked(AMonsterAIController* AI, const FVector& TargetFeet)
{
    if (!HasAuthority() || !bCloaked || IsCloakRecoveryReady() || !AI || !Combat || Combat->IsBusy()) return;
    const double Now = GetWorld()->GetTimeSeconds();
    const FVector Feet = GetNavAgentLocation();
    // Control/falling is not a navigation stall. Resume progress sampling once
    // the existing BT and movement mode allow this recovery branch again.
    if (Now - CloakNavigationTickAt > .5)
    {
        CloakProgressFeet = Feet;
        CloakProgressAt = Now;
        CloakBlockedAttempts = 0;
    }
    CloakNavigationTickAt = Now;
    if (!GetCharacterMovement()->IsMovingOnGround())
    { CloakBlockedAttempts = 0; CloakProgressAt = Now; return; }
    if (bHasCloakRoute)
    {
        const float ProgressDistance = FMath::Clamp(GetCharacterMovement()->GetMaxSpeed() * .35f, 3.f, 20.f);
        if (FVector::DistSquared2D(Feet, CloakProgressFeet) >= FMath::Square(ProgressDistance))
        { CloakProgressFeet = Feet; CloakProgressAt = Now; CloakBlockedAttempts = 0; }
        const bool Arrived = FVector::Dist2D(Feet, CloakGoal) <= 35. && FMath::Abs(Feet.Z - CloakGoal.Z) <= 60.;
        const bool Stalled = Now - CloakProgressAt >= .9;
        const bool Ended = AI->GetMoveStatus() != EPathFollowingStatus::Moving;
        if (!Arrived && Stalled)
        {
            CounterattackFromBlockedCloak(AI);
            return;
        }
        if (!Arrived && !Stalled && !Ended && Now < CloakRouteDeadline)
        {
            AI->ActiveAction = TEXT("Cloak: following reachable retreat / flank");
            Combat->SetLocomotion(true);
            return;
        }
        if (!Arrived)
        {
            if (++CloakBlockedAttempts >= 2)
            {
                CounterattackFromBlockedCloak(AI);
                return;
            }
            CloakFailedGoal = CloakGoal;
            CloakFailedGoalUntil = Now + 2.;
            CloakOrbitDirection *= -1.f;
        }
        AI->StopMovement();
        bHasCloakRoute = false;
        NextCloakGoalAt = FMath::Max(NextCloakGoalAt, Now + .08);
    }
    Combat->SetLocomotion(false);
    AI->ActiveAction = TEXT("Cloak: recovering / selecting local escape");
    if (Now < NextCloakGoalAt) return;
    if (!TakeCloakRouteSlot())
    {
        NextCloakGoalAt = Now + .06 + (GetUniqueID() % 7) * .013;
        return;
    }
    NextCloakGoalAt = Now + .65;
    if (ChooseCloakRoute(AI, TargetFeet))
    {
        Combat->SetLocomotion(true);
        AI->ActiveAction = TEXT("Cloak: following reachable retreat / flank");
    }
    else
    {
        AI->StopMovement();
        AI->bNavigationFailed = true;
        AI->ActiveAction = TEXT("Cloak: no clear local route / recovering");
        // Two actual failed batches distinguish a sealed corner from a single
        // transient nav/pawn obstruction. Budget waits do not count as failure.
        if (++CloakBlockedAttempts >= 2)
        {
            CounterattackFromBlockedCloak(AI);
            return;
        }
    }
}
