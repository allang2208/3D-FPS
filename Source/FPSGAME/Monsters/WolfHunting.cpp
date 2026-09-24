#include "WolfMonster.h"
#include "QuadrupedAnimationTemplate.h"
#include "FPSCombatHealthComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

bool AWolfMonster::HuntingSightFrom(const APawn* Victim, const FVector& From) const
{
    if (!IsValid(Victim)) return false;
    if (const auto* Vitals = Victim->FindComponentByClass<UFPSCombatHealthComponent>())
        if (Vitals->IsDead()) return false;
    FHitResult Hit;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(CanineSight), false, this);
    Params.AddIgnoredActor(Victim);
    return !GetWorld()->LineTraceSingleByChannel(Hit, From+FVector(0,0,15),
        Victim->GetActorLocation(), ECC_Visibility, Params);
}

bool AWolfMonster::CanBiteFrom(const APawn* Victim, const FVector& From, float Range) const
{
    if (!IsValid(Victim)) return false;
    float Radius, HalfHeight;
    Victim->GetSimpleCollisionCylinder(Radius, HalfHeight);
    const float FeetZ = From.Z-GetCapsuleComponent()->GetScaledCapsuleHalfHeight();
    return FMath::Abs(Victim->GetNavAgentLocation().Z-FeetZ) <= HuntingHeightTolerance &&
        FVector::DistSquared2D(From, Victim->GetActorLocation()) <= FMath::Square(FMath::Max(0.f, Range)+Radius) &&
        HuntingSightFrom(Victim, From);
}

FVector AWolfMonster::PredictHuntingTarget(APawn* Victim, float Seconds, float MaxDistance) const
{
    const FVector Position = Victim->GetActorLocation();
    const FVector Velocity = Victim->GetVelocity();
    FVector Lead = (FVector(Velocity.X, Velocity.Y, 0)*FMath::Max(0.f, Seconds))
        .GetClampedToMaxSize(FMath::Max(0.f, MaxDistance));
    // The same bounded velocity forecast used by Mutant3: a player's own
    // collision shape prevents the predicted position from crossing a wall.
    if (const auto* Character = Cast<ACharacter>(Victim); Character && !Lead.IsNearlyZero(1.f))
    {
        const auto* Capsule = Character->GetCapsuleComponent();
        const FCollisionShape Shape = FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),
            FMath::Max(Capsule->GetScaledCapsuleRadius(), Capsule->GetScaledCapsuleHalfHeight()-2.f));
        FCollisionQueryParams Params(SCENE_QUERY_STAT(CaninePrediction), false, this);
        Params.AddIgnoredActor(Victim);
        FHitResult Hit;
        if (GetWorld()->SweepSingleByChannel(Hit, Position, Position+Lead, FQuat::Identity,
            Capsule->GetCollisionObjectType(), Shape, Params,
            FCollisionResponseParams(Capsule->GetCollisionResponseToChannels())))
            Lead *= FMath::Max(0.f, Hit.Time-.02f);
    }
    return Position+Lead;
}

bool AWolfMonster::BuildHuntingPounce(APawn* Victim, FVector& Landing) const
{
    if (!IsValid(Victim) || !HuntingSightFrom(Victim, GetActorLocation())) return false;
    const FVector Start = GetActorLocation();
    const FVector Position = Victim->GetActorLocation();
    const float Distance = FVector::Dist2D(Start, Position);
    const float Duration = PounceTravelEnd-PounceTravelStart;
    if (Distance < PounceMinRange || Distance > PounceMaxRange || Duration <= SMALL_NUMBER) return false;
    const auto* Capsule = GetCapsuleComponent();
    const auto* Move = GetCharacterMovement();
    const float HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
    float TargetRadius, TargetHalfHeight;
    Victim->GetSimpleCollisionCylinder(TargetRadius, TargetHalfHeight);
    const float StandOff = FMath::Max(PounceStandOff, Capsule->GetScaledCapsuleRadius()+TargetRadius+4.f);
    const FVector Lead = PredictHuntingTarget(Victim,
        Duration*FMath::Clamp(PounceLeadStrength, 0.f, 1.5f), PounceMaxLeadDistance)-Position;
    FCollisionQueryParams Params(SCENE_QUERY_STAT(CaninePouncePlan), false, this);
    Params.AddIgnoredActor(Victim);
    const FCollisionShape Shape = FCollisionShape::MakeCapsule(Capsule->GetScaledCapsuleRadius(),
        FMath::Max(Capsule->GetScaledCapsuleRadius(), HalfHeight-1.f));
    const FCollisionResponseParams Response(Capsule->GetCollisionResponseToChannels());
    const int32 Candidates = Lead.IsNearlyZero(1.f) ? 1 : 3;
    for (int32 Candidate = 0; Candidate < Candidates; ++Candidate)
    {
        const FVector Aim = Position+Lead*(1.f-.5f*Candidate);
        const FVector Direction = (Aim-Start).GetSafeNormal2D();
        FVector End = Aim-Direction*StandOff;
        FVector Travel(End.X-Start.X, End.Y-Start.Y, 0);
        Travel = Travel.GetClampedToMaxSize(FMath::Max(1.f, PounceMaxRange));
        End.X = Start.X+Travel.X;
        End.Y = Start.Y+Travel.Y;
        if (FVector::Dist2D(End, Aim) > PounceContactReach+TargetRadius) continue;
        // Search around target feet, not torso height; do not pick another floor.
        End.Z = Victim->GetNavAgentLocation().Z;
        FHitResult Floor;
        if (!GetWorld()->LineTraceSingleByChannel(Floor, End+FVector(0,0,100),
            End-FVector(0,0,160), ECC_Visibility, Params) || !Move->IsWalkable(Floor)) continue;
        End = Floor.ImpactPoint+FVector(0,0,HalfHeight+2.f);
        if (FMath::Abs(End.Z-Start.Z) > HuntingHeightTolerance ||
            FMath::Abs(Floor.ImpactPoint.Z-Victim->GetNavAgentLocation().Z) > HuntingHeightTolerance) continue;
        bool Clear = true;
        FVector Previous = Start;
        for (int32 Step = 1; Step <= 16; ++Step)
        {
            const float Alpha = Step/16.f;
            const FVector Next = FMath::Lerp(Start, End, Alpha)+FVector(0,0,FMath::Sin(Alpha*PI)*PounceArcHeight);
            FHitResult Hit;
            if (GetWorld()->SweepSingleByChannel(Hit, Previous, Next, FQuat::Identity,
                Capsule->GetCollisionObjectType(), Shape, Params, Response))
            {
                Clear = false;
                break;
            }
            Previous = Next;
        }
        if (!Clear) continue;
        Landing = End;
        return true;
    }
    return false;
}

void AWolfMonster::TrackHuntingWindup(float PreviousSeconds)
{
    if (!Target.IsValid()) return;
    const bool Pouncing = State == EWolfState::Pounce;
    const auto* Definition = AnimationSet ? AnimationSet->FindAction(Pouncing ? TEXT("AttackPounce") : TEXT("AttackBite")) : nullptr;
    if (!Definition) return;
    const float LockTime = Pouncing ? PounceWindup+PounceTravelStart : BiteWindup+Definition->ContactStartSeconds;
    const float TurnSeconds = FMath::Max(0.f, FMath::Min(StateSeconds, LockTime)-PreviousSeconds);
    if (TurnSeconds <= 0.f) return;
    const float LeadTime = Pouncing ? 0.f : FMath::Clamp(LockTime-StateSeconds, 0.f, .2f);
    const FVector Aim = PredictHuntingTarget(Target.Get(), LeadTime, 65.f);
    const FRotator Facing(0,(Aim-GetActorLocation()).Rotation().Yaw,0);
    SetActorRotation(FMath::RInterpConstantTo(GetActorRotation(), Facing, TurnSeconds, AttackTrackingYawRate));
    AttackDirection = GetActorForwardVector().GetSafeNormal2D();
}

bool AWolfMonster::HuntingContact(const APawn* Victim, bool bPounce) const
{
    const float Reach = bPounce ? PounceContactReach : BiteTriggerRange+BiteContactSlack;
    if (!CanBiteFrom(Victim, GetActorLocation(), Reach)) return false;
    float Radius, HalfHeight;
    Victim->GetSimpleCollisionCylinder(Radius, HalfHeight);
    const FVector Offset = Victim->GetActorLocation()-GetActorLocation();
    const FVector Planar(Offset.X, Offset.Y, 0);
    const float HalfAngle = FMath::Clamp(bPounce ? PounceContactAngle : BiteContactAngle, 1.f, 180.f)*.5f;
    const FVector Forward = AttackDirection.GetSafeNormal2D();
    if (Planar.IsNearlyZero(1.f) || FVector::DotProduct(Forward, Planar.GetSafeNormal()) >= FMath::Cos(FMath::DegreesToRadians(HalfAngle)))
        return true;
    // Include capsule edges touching the cone, while retaining an avoidable rear.
    for (float Angle : {-HalfAngle, HalfAngle})
        if (FMath::PointDistToSegmentSquared(Planar, FVector::ZeroVector,
            Forward.RotateAngleAxis(Angle, FVector::UpVector)*Reach) <= FMath::Square(Radius)) return true;
    return false;
}
