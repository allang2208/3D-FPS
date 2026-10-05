#include "LurkerM08Monster.h"
#include "MonsterAIController.h"
#include "MonsterCombatComponent.h"
#include "QuadrupedAnimationTemplate.h"
#include "FPSCombatHealthComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Math/RotationMatrix.h"
#include "Net/UnrealNetwork.h"

float ALurkerM08Monster::BodyRadius() const { return GetCapsuleComponent()->GetScaledCapsuleRadius(); }
FVector ALurkerM08Monster::GetNavAgentLocation() const
{
    return GetActorLocation() - (bSurfaceAttached ? SurfaceNormal : FVector::UpVector) * BodyRadius();
}
bool ALurkerM08Monster::Busy() const { return Super::Busy() || bTraversalJump || AirCannon.bActive; }
void ALurkerM08Monster::BeginPlay()
{
    InitialHomeSupport = GetActorLocation() - FVector::UpVector * BodyRadius();
    Super::BeginPlay();
    if (HasAuthority()) AttachNear(FVector::UpVector);
}
void ALurkerM08Monster::GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const
{
    Super::GetLifetimeReplicatedProps(OutLifetimeProps);
    DOREPLIFETIME(ALurkerM08Monster, SurfaceNormal);
    DOREPLIFETIME(ALurkerM08Monster, bSurfaceAttached);
    DOREPLIFETIME(ALurkerM08Monster, bTraversalJump);
    DOREPLIFETIME(ALurkerM08Monster, TraversalClock);
    DOREPLIFETIME(ALurkerM08Monster, TraversalFlightSeconds);
    DOREPLIFETIME(ALurkerM08Monster, AirCannon);
}
bool ALurkerM08Monster::AttachNear(FVector Normal, float Reach)
{
    FLurkerSurfacePoint Point;
    if (!LurkerSurfaceRoute::Support(GetWorld(), this, GetActorLocation() + Normal * 8.f,
        GetActorLocation() - Normal * Reach, BodyRadius(), Point)) return false;
    if (!LurkerSurfaceRoute::Segment(GetWorld(), this, GetActorLocation(), Point.Center, BodyRadius())) return false;
    FHitResult Hit; GetCharacterMovement()->SafeMoveUpdatedComponent(Point.Center - GetActorLocation(), GetActorQuat(), true, Hit);
    if (Hit.bBlockingHit) return false;
    SurfaceNormal = Point.Normal; bSurfaceAttached = true;
    // PhysCustom supplies no second velocity integration; this actor owns the swept surface step.
    GetCharacterMovement()->SetMovementMode(MOVE_Custom, 8);
    GetCharacterMovement()->bOrientRotationToMovement = false;
    GetCharacterMovement()->StopMovementImmediately();
    return true;
}
void ALurkerM08Monster::DetachSurface()
{
    bSurfaceAttached = false; SurfacePath.Reset();
    if (!Dead()) GetCharacterMovement()->SetMovementMode(MOVE_Falling);
}
void ALurkerM08Monster::NavigateSurface(FVector Destination, bool bReturning, APawn* VisibleTarget)
{
    if (Busy() || Combat->IsControlled()) return;
    FVector Goal = Destination + FVector::UpVector * (BodyRadius() + 3.f);
    if (VisibleTarget && !bReturning)
    {
        float TargetRadius, TargetHalfHeight;
        VisibleTarget->GetSimpleCollisionCylinder(TargetRadius, TargetHalfHeight);
        // Plan to a usable approach point, not inside the player's blocking capsule.
        FVector Away = (GetActorLocation() - Goal).GetSafeNormal2D();
        if (Away.IsNearlyZero()) Away = -GetActorForwardVector().GetSafeNormal2D();
        Goal += Away * FMath::Max(BodyRadius() + TargetRadius + 12.f, BiteTriggerRange - 35.f);
    }
    const bool ChangedIntent = bSurfaceReturning != bReturning
        || (SurfaceVictim.IsValid() && VisibleTarget && SurfaceVictim.Get() != VisibleTarget);
    if (ChangedIntent)
    {
        RecentSupports.Reset(); SurfacePath.Reset(); bHasSurfacePlan = false; RouteAge = 10.f;
    }
    else if (bHasSurfacePlan && RouteAge >= .45f
        && FVector::DistSquared(Goal, PlannedSurfaceGoal) > FMath::Square(100.f))
    { SurfacePath.Reset(); RouteAge = .7f; }
    SurfaceGoal = Goal; bSurfaceReturning = bReturning; SurfaceVictim = VisibleTarget;
    const bool Reached = VisibleTarget && !bReturning ? CanBiteFrom(VisibleTarget, GetActorLocation(), BiteTriggerRange - 25.f)
        : FVector::DistSquared(GetActorLocation(), Goal) < FMath::Square(60.f);
    bWantsSurfaceMove = !Reached;
    if (Reached)
    {
        StopSurfaceNavigation();
        if (VisibleTarget) FaceAttackDirection(VisibleTarget->GetActorLocation() - GetActorLocation());
    }
}
void ALurkerM08Monster::StopSurfaceNavigation()
{
    bWantsSurfaceMove = false; SurfacePath.Reset(); bHasSurfacePlan = false; StuckSeconds = 0.f;
    // A BT Hold waits for the jump to land; it must never freeze a body in the air.
    if (!bTraversalJump && bSurfaceAttached) GetCharacterMovement()->StopMovementImmediately();
    if (!Busy()) SetLocomotion(false, false);
}
void ALurkerM08Monster::OrientToSurface(FVector Direction, FVector Normal, float Dt)
{
    FVector Forward = FVector::VectorPlaneProject(Direction, Normal).GetSafeNormal();
    if (Forward.IsNearlyZero()) Forward = FVector::VectorPlaneProject(GetActorForwardVector(), Normal).GetSafeNormal();
    if (Forward.IsNearlyZero()) Forward = FVector::CrossProduct(GetActorRightVector(), Normal).GetSafeNormal();
    const FQuat Desired = FRotationMatrix::MakeFromXZ(Forward, Normal).ToQuat();
    SetActorRotation(FMath::QInterpConstantTo(GetActorQuat(), Desired, FMath::Max(0.f, Dt), FMath::DegreesToRadians(SurfaceTurnSpeed)));
}
void ALurkerM08Monster::Tick(float Dt)
{
    const FVector Before = GetActorLocation();
    // Native combat remains the only attack clock and damage owner.
    Super::Tick(Dt);
    TickAirCannon(Dt);
    auto* Movement = GetCharacterMovement();
    if (HasAuthority())
    {
        JumpCooldown = FMath::Max(0.f, JumpCooldown - Dt); RouteAge += Dt; SupportAge += Dt;
        Movement->bOrientRotationToMovement = false;
        if (Dead())
        {
            bWantsSurfaceMove = bSurfaceAttached = bTraversalJump = false; SurfacePath.Reset();
            // Preserve the current wall/ceiling death pose for the shared world-gravity ragdoll handoff.
            return;
        }
        if (Combat->IsControlled() || State == EWolfState::Stagger)
        {
            if (bTraversalJump || (bSurfaceAttached && SurfaceNormal.Z < .65f))
            { bTraversalJump = false; DetachSurface(); }
            StopSurfaceNavigation();
        }
        else if (bTraversalJump) TickTraversalJump(Dt);
        else if (State == EWolfState::Pounce)
        {
            if (Movement->MovementMode == MOVE_Flying || Movement->IsFalling()) bSurfaceAttached = false;
        }
        else
        {
            if (!bSurfaceAttached && Movement->Velocity.Z <= 0.f) AttachNear(FVector::UpVector, BodyRadius() + 14.f);
            if (bSurfaceAttached) TickSurface(Dt);
        }
        if (!bSurfaceAttached) OrientToSurface(GetActorForwardVector(), FVector::UpVector, Dt);
        if (bSurfaceAttached || bTraversalJump)
            Movement->Velocity = (GetActorLocation() - Before) / FMath::Max(.001f, Dt);
        else if (State == EWolfState::Pounce && Movement->MovementMode == MOVE_Flying)
            Movement->Velocity = FVector::ZeroVector; // The attack clock already swept this flight step.
    }
    if (auto* Anim = Cast<UQuadrupedTemplateAnimInstance>(GetMesh()->GetAnimInstance()))
    {
        // Vertical climbing must advance the gait, unlike the ground-only Size2D convention.
        Anim->bUseOwnerVelocity = false;
        Anim->ManualSpeed = HasAuthority() && State == EWolfState::Pounce
            ? FVector::Distance(Before, GetActorLocation()) / FMath::Max(.001f, Dt) : GetVelocity().Size();
    }
    if (!HasAuthority()) UpdateJumpPose();
}
void ALurkerM08Monster::TickSurface(float Dt)
{
    if (SupportAge >= .15f)
    {
        SupportAge = 0.f;
        FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(M08RetainSupport), false, this);
        if (!GetWorld()->LineTraceSingleByChannel(Hit, GetActorLocation(), GetActorLocation() - SurfaceNormal * (BodyRadius() + 150.f), ECC_Pawn, Query)
            || !Hit.GetActor() || Hit.GetActor()->IsA<APawn>()) { DetachSurface(); return; }
    }
    if (Busy() || !bWantsSurfaceMove) return;
    if (SurfacePath.IsEmpty() && RouteAge >= .7f)
    {
        RouteAge = 0.f;
        PlannedSurfaceGoal = SurfaceGoal; bHasSurfacePlan = true;
        // A clear jump can cross disconnected ledges. Otherwise search real surface continuity.
        if ((FMath::Abs(SurfaceGoal.Z - GetActorLocation().Z) > 100.f || StuckSeconds > .45f) && BeginTraversalJump()) return;
        FVector Guide = SurfaceGoal;
        LurkerSurfaceRoute::GroundGuide(GetWorld(), this, {GetActorLocation(), SurfaceNormal}, SurfaceGoal, BodyRadius(), Guide);
        LurkerSurfaceRoute::Build(GetWorld(), this, {GetActorLocation(), SurfaceNormal}, Guide, BodyRadius(), RecentSupports, SurfacePath);
        if (SurfacePath.IsEmpty() && BeginTraversalJump()) return;
    }
    if (SurfacePath.IsEmpty())
    {
        SetLocomotion(false, bSurfaceReturning); StuckSeconds += Dt;
        if (SurfaceVictim.IsValid()) FaceAttackDirection(SurfaceVictim->GetActorLocation() - GetActorLocation(), Dt);
        return;
    }
    const FLurkerSurfacePoint Next = SurfacePath[0];
    const FVector Delta = Next.Center - GetActorLocation();
    const float Speed = bSurfaceReturning ? WalkSpeed : Next.Normal.Z > .65f ? ChaseSpeed : ClimbSpeed;
    SetLocomotion(true, bSurfaceReturning);
    GetCharacterMovement()->bOrientRotationToMovement = false;
    const FVector Before = GetActorLocation();
    FHitResult Hit;
    GetCharacterMovement()->SafeMoveUpdatedComponent(Delta.GetClampedToMaxSize(Speed * Dt), GetActorQuat(), true, Hit);
    const float Travel = FVector::Distance(Before, GetActorLocation());
    StuckSeconds = Travel < .5f ? StuckSeconds + Dt : 0.f;
    const FVector BlendedNormal = FMath::VInterpNormalRotationTo(SurfaceNormal, Next.Normal, Dt, SurfaceTurnSpeed);
    SurfaceNormal = BlendedNormal.GetSafeNormal();
    OrientToSurface(Delta, SurfaceNormal, Dt);
    if (Hit.bBlockingHit) { SurfacePath.Reset(); RouteAge = FMath::Max(RouteAge, .65f); return; }
    if (FVector::DistSquared(GetActorLocation(), Next.Center) < FMath::Square(5.f))
    {
        SurfaceNormal = Next.Normal;
        RecentSupports.Add(Next.Center); if (RecentSupports.Num() > 12) RecentSupports.RemoveAt(0);
        SurfacePath.RemoveAt(0);
    }
}
bool ALurkerM08Monster::BeginTraversalJump()
{
    if (!bSurfaceAttached || JumpCooldown > 0.f || Super::Busy()) return false;
    const FVector Start = GetActorLocation();
    const FVector ToGoal = SurfaceGoal - Start;
    const FVector Direction = ToGoal.GetSafeNormal2D();
    const FVector Outward = SurfaceNormal.Z < .65f ? SurfaceNormal : FVector::ZeroVector;
    const float StopShort = SurfaceVictim.IsValid() ? PounceStandOff : 0.f;
    for (const float Distance : {float(FMath::Min(FMath::Max(0.f, ToGoal.Size2D() - StopShort), JumpRange)), 450.f, 270.f})
    {
        if (Distance < 140.f || Distance > JumpRange || Distance > ToGoal.Size2D() + 40.f) continue;
        const FVector Near = Start + Direction * Distance;
        TArray<FLurkerSurfacePoint, TInlineAllocator<3>> Landings;
        // Start inside the destination floor band before trying the high probe;
        // otherwise an indoor jump would select the roof above the room.
        for (const double ProbeZ : {SurfaceGoal.Z + 100., Start.Z + 100., Start.Z + JumpHeight})
        {
            FLurkerSurfacePoint Landing;
            if (LurkerSurfaceRoute::Support(GetWorld(), this, FVector(Near.X, Near.Y, FMath::Min(ProbeZ, Start.Z + JumpHeight)),
                FVector(Near.X, Near.Y, Start.Z - JumpHeight), BodyRadius(), Landing) && Landing.Normal.Z >= .5f)
                Landings.Add(Landing);
        }
        for (const auto& Landing : Landings)
        {
            if (FVector::Distance(Start, Landing.Center) > JumpRange) continue;
            for (const float Height : {100.f, 200.f, 320.f})
            {
                if (!LurkerSurfaceRoute::ClearArc(GetWorld(), this, Start, Landing.Center, Outward, Height, BodyRadius())) continue;
                JumpStart = Start; JumpEnd = Landing.Center; JumpLandingNormal = Landing.Normal; JumpOutward = Outward;
                JumpArcHeight = Height; TraversalFlightSeconds = FMath::Clamp(FVector::Distance(Start, JumpEnd) / 760.f + .16f, .44f, 1.05f);
                TraversalClock = 0.f; bTraversalJump = true; JumpCooldown = 1.6f;
                SurfacePath.Reset(); bWantsSurfaceMove = false;
                GetCharacterMovement()->SetMovementMode(MOVE_Custom, 9);
                UpdateJumpPose(); ForceNetUpdate(); return true;
            }
        }
    }
    return false;
}
void ALurkerM08Monster::UpdateJumpPose()
{
    auto* Anim = Cast<UQuadrupedTemplateAnimInstance>(GetMesh()->GetAnimInstance());
    if (!Anim) return;
    if (bTraversalJump)
    {
        if (Anim->ActiveAction != TEXT("TraverseJump")) Anim->PlayTemplateAction(TEXT("TraverseJump"), true);
        const float SourceTime = TraversalClock <= .24f ? TraversalClock : TraversalClock < .24f + TraversalFlightSeconds
            ? .24f + .50f * ((TraversalClock - .24f) / TraversalFlightSeconds)
            : .74f + TraversalClock - .24f - TraversalFlightSeconds;
        Anim->SetActionTime(SourceTime);
    }
    else if (Anim->ActiveAction == TEXT("TraverseJump")) Anim->ResumeLocomotion(.12f);
}
void ALurkerM08Monster::TickTraversalJump(float Dt)
{
    const float Previous = TraversalClock; TraversalClock += Dt;
    const float FlightEnd = .24f + TraversalFlightSeconds;
    float Time = FMath::Max(.24f, Previous);
    while (Time < FMath::Min(TraversalClock, FlightEnd) - SMALL_NUMBER)
    {
        Time = FMath::Min(Time + 1.f / 60.f, FMath::Min(TraversalClock, FlightEnd));
        bSurfaceAttached = false;
        const float Alpha = (Time - .24f) / TraversalFlightSeconds;
        const FVector Wanted = LurkerSurfaceRoute::Arc(JumpStart, JumpEnd, JumpOutward, JumpArcHeight, Alpha);
        FHitResult Hit; GetCharacterMovement()->SafeMoveUpdatedComponent(Wanted - GetActorLocation(), GetActorQuat(), true, Hit);
        if (Hit.bBlockingHit)
        {
            bTraversalJump = false; DetachSurface(); UpdateJumpPose(); return;
        }
    }
    OrientToSurface(JumpEnd - JumpStart, TraversalClock < .24f ? SurfaceNormal : FVector::UpVector, Dt);
    if (TraversalClock >= FlightEnd && !bSurfaceAttached)
    {
        if (!AttachNear(JumpLandingNormal, BodyRadius() + 24.f)) { bTraversalJump = false; DetachSurface(); UpdateJumpPose(); return; }
    }
    UpdateJumpPose();
    if (TraversalClock >= FlightEnd + .76f)
    {
        bTraversalJump = false; UpdateJumpPose(); RouteAge = 10.f; ForceNetUpdate();
        if (auto* AI = Cast<AMonsterAIController>(GetController())) AI->UpdateKnowledge();
    }
}

bool ALurkerM08Monster::HasAttackSupport() const { return bSurfaceAttached || Super::HasAttackSupport(); }
bool ALurkerM08Monster::CanBiteFrom(const APawn* Victim, const FVector& From, float Range) const
{
    if (!IsValid(Victim)) return false;
    if (const auto* Vitals = Victim->FindComponentByClass<UFPSCombatHealthComponent>(); Vitals && Vitals->IsDead()) return false;
    float Radius, HalfHeight; Victim->GetSimpleCollisionCylinder(Radius, HalfHeight);
    const FVector Axis = FVector::UpVector * FMath::Max(0.f, HalfHeight - Radius);
    if (FMath::PointDistToSegmentSquared(From, Victim->GetActorLocation() - Axis, Victim->GetActorLocation() + Axis)
        > FMath::Square(Range + Radius)) return false;
    if (bSurfaceAttached && SurfaceNormal.Z < .65f)
    {
        // Close in world space can still be far from the mouth on a ceiling.
        // Prefer a diving pounce unless a stationary surface bite can reach.
        const FVector Mouth = GetMesh()->GetSocketLocation(TEXT("Wolf_-Head")) + GetActorForwardVector() * 18.f + From - GetActorLocation();
        if (FMath::PointDistToSegmentSquared(Mouth, Victim->GetActorLocation() - Axis, Victim->GetActorLocation() + Axis)
            > FMath::Square(Radius + ContactRadius + 40.f)) return false;
    }
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(M08BiteSight), false, this); Query.AddIgnoredActor(Victim);
    return !GetWorld()->LineTraceSingleByChannel(Hit, From, Victim->GetActorLocation(), ECC_Pawn, Query);
}
void ALurkerM08Monster::FaceAttackDirection(const FVector& Direction, float TurnSeconds)
{
    FVector Facing = Direction;
    // On a vertical wall, a target directly below has no XY attack direction.
    if (Facing.IsNearlyZero()) Facing = GetActorForwardVector();
    OrientToSurface(Facing, bSurfaceAttached ? SurfaceNormal : FVector::UpVector,
        TurnSeconds < 0.f ? GetWorld()->GetDeltaSeconds() : TurnSeconds);
}
bool ALurkerM08Monster::BuildHuntingPounce(APawn* Victim, FVector& Landing) const
{
    if (!IsValid(Victim)) return false;
    const double Now = GetWorld()->GetTimeSeconds();
    // Knowledge/attack selection can ask repeatedly in one frame. The actual
    // takeoff always rebuilds against current collision and target position.
    if (State != EWolfState::Pounce && Now - AttackPlanTime < .2 && AttackPlanTarget.Get() == Victim
        && FVector::DistSquared(AttackPlanStart, GetActorLocation()) < FMath::Square(45.f)
        && FVector::DistSquared(AttackPlanTargetPosition, Victim->GetActorLocation()) < FMath::Square(45.f))
    { Landing = AttackPlanLanding; return bAttackPlanValid; }
    AttackPlanTime = Now; AttackPlanTarget = Victim; AttackPlanStart = GetActorLocation();
    AttackPlanTargetPosition = Victim->GetActorLocation();
    bAttackPlanValid = PlanHuntingPounce(Victim, AttackPlanLanding);
    Landing = AttackPlanLanding; return bAttackPlanValid;
}
bool ALurkerM08Monster::PlanHuntingPounce(APawn* Victim, FVector& Landing) const
{
    if (!IsValid(Victim)) return false;
    const FVector Start = GetActorLocation();
    const float Distance = FVector::Distance(Start, Victim->GetActorLocation());
    if (Distance < 145.f || Distance > JumpRange) return false;
    float Radius, HalfHeight; Victim->GetSimpleCollisionCylinder(Radius, HalfHeight);
    const float LeadSeconds = PounceFlightDuration(Start, Victim->GetActorLocation()) * PounceLeadStrength;
    const FVector Lead = (Victim->GetVelocity() * LeadSeconds).GetClampedToMaxSize(PounceMaxLeadDistance);
    const FVector Aim = Victim->GetActorLocation() + Lead;
    FVector Direction = (Aim - Start).GetSafeNormal2D();
    if (Direction.IsNearlyZero()) Direction = GetActorForwardVector().GetSafeNormal2D();
    if (Direction.IsNearlyZero()) Direction = FVector::ForwardVector;
    for (const float Angle : {0.f, 40.f, -40.f})
    {
        const FVector Near = Aim - Direction.RotateAngleAxis(Angle, FVector::UpVector) * FMath::Max(PounceStandOff, BodyRadius() + Radius + 6.f);
        FLurkerSurfacePoint Point;
        const float Feet = Victim->GetNavAgentLocation().Z;
        if (!LurkerSurfaceRoute::Support(GetWorld(), this, FVector(Near.X, Near.Y, Feet + 110.f),
            FVector(Near.X, Near.Y, Feet - 180.f), BodyRadius(), Point) || Point.Normal.Z < .5f) continue;
        const FVector Outward = bSurfaceAttached && SurfaceNormal.Z < .65f ? SurfaceNormal : FVector::ZeroVector;
        for (const float Height : {75.f, 160.f, 280.f})
            if (LurkerSurfaceRoute::ClearArc(GetWorld(), this, Start, Point.Center, Outward, Height, BodyRadius()))
            {
                Landing = Point.Center; PlannedAttackArc = Height; PlannedAttackOutward = Outward; return true;
            }
    }
    return false;
}
FVector ALurkerM08Monster::PouncePathPoint(const FVector& Start, const FVector& End, float Alpha) const
{
    return LurkerSurfaceRoute::Arc(Start, End, PlannedAttackOutward, PlannedAttackArc, Alpha);
}
float ALurkerM08Monster::PounceFlightDuration(const FVector& Start, const FVector& End) const
{
    return FMath::Clamp(float(FVector::Distance(Start, End)) / 760.f + .16f, .44f, .95f)
        / FMath::Max(.1f, PounceFlightSpeedMultiplier);
}
float ALurkerM08Monster::LeapPitchCorrection(bool Traversal, float SourceSeconds) const
{
    const float Phase=FMath::Clamp((SourceSeconds-.24f)/.50f,0.f,1.f);
    const FVector Delta=Traversal ? JumpEnd-JumpStart : AttackPlanLanding-AttackPlanStart;
    if (Delta.IsNearlyZero()) return 0.f;
    const float Height=Traversal ? JumpArcHeight : PlannedAttackArc;
    const FVector Outward=Traversal ? JumpOutward : PlannedAttackOutward;
    const FVector Tangent=Delta+(FVector::UpVector*Height+Outward*80.f)*(PI*FMath::Cos(PI*Phase));
    const float Pitch=FMath::Atan2(float(Tangent.Z),FMath::Max(1.f,float(Tangent.Size2D())));
    const float Blend=FMath::SmoothStep(0.f,.18f,Phase)*(1.f-FMath::SmoothStep(.78f,1.f,Phase));
    return FMath::Clamp(Pitch*.35f,-.18f,.18f)*Blend;
}
bool ALurkerM08Monster::HuntingContact(const APawn* Victim, bool bPounce) const
{
    if (!CanBiteFrom(Victim, GetActorLocation(), bPounce ? PounceContactReach : BiteTriggerRange + BiteContactSlack)) return false;
    const FVector Mouth = GetMesh()->GetSocketLocation(TEXT("Wolf_-Head")) + GetActorForwardVector() * 18.f;
    float Radius, HalfHeight; Victim->GetSimpleCollisionCylinder(Radius, HalfHeight);
    const FVector Axis = FVector::UpVector * FMath::Max(0.f, HalfHeight - Radius);
    if (FMath::PointDistToSegmentSquared(Mouth, Victim->GetActorLocation() - Axis, Victim->GetActorLocation() + Axis)
        > FMath::Square(Radius + ContactRadius + 20.f)) return false;
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(M08MouthContact), false, this); Query.AddIgnoredActor(Victim);
    return !GetWorld()->LineTraceSingleByChannel(Hit, Mouth, Victim->GetActorLocation(), ECC_Pawn, Query);
}
void ALurkerM08Monster::FinishPounceMovement()
{
    const bool InFlight = GetCharacterMovement()->MovementMode == MOVE_Flying;
    Super::FinishPounceMovement();
    if (InFlight)
    {
        bSurfaceAttached = false; SurfacePath.Reset(); RouteAge = 10.f;
        // Only retain a surface actually within the capsule's landing reach.
        // A blocked mid-air attack continues falling instead of pinning feet.
        if (!Dead()) AttachNear(FVector::UpVector, BodyRadius() + 10.f);
    }
}
