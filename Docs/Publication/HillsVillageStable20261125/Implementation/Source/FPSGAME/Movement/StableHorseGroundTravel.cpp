#include "StableRidingHorse.h"
#include "../FPSGAMECharacter.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "GameFramework/CharacterMovementComponent.h"

namespace
{
    // The movement component owns the central capsule and the actual step.
    // These queries cover only the projecting body, rider and short follow routes.
    struct FHorseGroundQuery
    {
        const UCharacterMovementComponent& Move;
        const UCapsuleComponent& Capsule;
        const UWorld& World;
        FCollisionQueryParams Query;
        FCollisionResponseParams Response;
        TArray<FHitResult> Hits;

        FHorseGroundQuery(const AStableRidingHorse& InHorse, const AActor* Ignore)
            : Move(*InHorse.GetCharacterMovement()), Capsule(*InHorse.GetCapsuleComponent()),
              World(*InHorse.GetWorld()), Query(SCENE_QUERY_STAT(HorseGroundTravel), false, &InHorse)
        {
            Capsule.InitSweepCollisionParams(Query, Response);
            if (Ignore) Query.AddIgnoredActor(Ignore);
            Query.bIgnoreTouches = true;
        }

        bool Blocked(const FVector& From, const FVector& To, const FCollisionShape& Hull, FHitResult* Obstruction=nullptr)
        {
            Hits.Reset();
            World.SweepMultiByChannel(Hits, From, To, FQuat::Identity, Capsule.GetCollisionObjectType(), Hull, Query, Response);
            for (const FHitResult& Hit : Hits)
            {
                if (!Hit.bBlockingHit) continue;
                // Either end may already touch a jamb. Allow a motion out of it,
                // while still considering the other contacts returned by the sweep.
                if (Hit.Time <= UE_KINDA_SMALL_NUMBER && FVector::DotProduct(To-From, Hit.ImpactNormal) > UE_KINDA_SMALL_NUMBER)
                    continue;
                if (Obstruction) *Obstruction = Hit;
                return true;
            }
            return false;
        }

        // Work from the last accepted floor, never from the height of a hit on
        // a fence. Limit the horizontal stride so a valid ramp rises by at most one step.
        template<typename CheckSpan>
        bool AlongFloor(FVector& Floor, const FVector& Target, CheckSpan Check) const
        {
            const FVector Start = Floor;
            const float Step = Move.MaxStepHeight;
            if (Step <= UE_KINDA_SMALL_NUMBER) return false;
            const double FloorZ = Move.GetWalkableFloorZ();
            if (FloorZ <= UE_KINDA_SMALL_NUMBER) return false;
            const double MaxGrade = FMath::Sqrt(FMath::Max(0., 1. - FloorZ*FloorZ)) / FloorZ;
            const double Stride = Step / FMath::Max(1., MaxGrade);
            const int32 Count = FMath::Max(1, FMath::CeilToInt(FVector::Dist2D(Start, Target) / Stride));
            const FVector Reach(0, 0, Step + UCharacterMovementComponent::MAX_FLOOR_DIST);
            for (int32 I=1; I<=Count; ++I)
            {
                FVector Sample = FMath::Lerp(Start, Target, double(I)/Count);
                Sample.Z = Floor.Z;
                FHitResult Hit;
                if (!World.LineTraceSingleByChannel(Hit, Sample+Reach, Sample-Reach, Capsule.GetCollisionObjectType(), Query, Response)
                    || !Move.IsWalkable(Hit) || (Hit.GetActor() && Hit.GetActor()->IsA<APawn>()))
                    return false;
                const FVector Next = Hit.ImpactPoint;
                if (FMath::Abs(Next.Z-Floor.Z) > Step + UE_KINDA_SMALL_NUMBER) return false;
                const FVector& N = Hit.ImpactNormal;
                const double RampRise = -(N.X*(Next.X-Floor.X) + N.Y*(Next.Y-Floor.Y))/N.Z;
                if (Next.Z-Floor.Z > FMath::Max(0., RampRise) + UCharacterMovementComponent::MAX_FLOOR_DIST
                    && !Move.CanStepUp(Hit))
                    return false;
                if (!Check(Floor, Next)) return false;
                Floor = Next;
            }
            return true;
        }
    };
}

bool AStableRidingHorse::ClearBody(const FVector& Delta, const FRotator& Rotation) const
{
    FHorseGroundQuery Trace(*this, Rider);
    const FVector Centre = GetActorLocation();
    const FVector Forward = GetActorForwardVector(), Facing = Rotation.Vector();
    const auto& Move = Trace.Move;
    const bool Grounded = FMath::IsNearlyZero(Delta.Z) && Move.IsMovingOnGround() && Move.CurrentFloor.IsWalkableFloor();
    const float Half = Trace.Capsule.GetScaledCapsuleHalfHeight();
    const FVector Feet = Centre - FVector(0,0, Half + (Grounded ? Move.CurrentFloor.GetDistanceToFloor() : 0.f));
    // A swept capsule rests uphill of its centre on a steep slope. Its lowest point
    // can be a full step above the terrain directly beneath it. Start floor probes
    // at the measured contact, so probing toward the hindquarters can descend too.
    const FVector Support = Grounded ? Move.CurrentFloor.HitResult.ImpactPoint : Feet;
    FVector Travel = Delta;
    if (Grounded && !Move.CurrentFloor.bLineTrace)
    {
        const FVector& N = Move.CurrentFloor.HitResult.ImpactNormal;
        if (N.Z > UE_KINDA_SMALL_NUMBER) Travel.Z = -(N.X*Delta.X + N.Y*Delta.Y)/N.Z;
    }

    constexpr float BodyRadius=30.f, BodyHalf=56.f;
    const auto Body = FCollisionShape::MakeCapsule(BodyRadius, BodyHalf);
    bool UsedGround = false;
    for (const float Offset : {-53.f, 56.f})
    {
        const FVector Start = Centre + Forward*Offset;
        const FVector End = Centre + Travel + Facing*Offset;
        FHitResult Obstacle;
        if (!Trace.Blocked(Start, End, Body, &Obstacle)) continue;
        if (!Grounded || Obstacle.ImpactNormal.Z < -UE_KINDA_SMALL_NUMBER) return false;
        if (!Obstacle.bStartPenetrating && !Move.IsWalkable(Obstacle))
        {
            // A riser has a walkable top just inside its edge. A rail or wall
            // with air beneath the contact must still block the projecting body.
            FVector Lip = Support;
            const FVector Inside = Obstacle.ImpactPoint - Obstacle.ImpactNormal.GetSafeNormal2D()*2.;
            if (!Move.CanStepUp(Obstacle) ||
                !Trace.AlongFloor(Lip, Inside, [](const FVector&, const FVector&){return true;}) ||
                Obstacle.ImpactPoint.Z > Lip.Z + UCharacterMovementComponent::MAX_FLOOR_DIST) return false;
        }

        // On a crest the shoulders may stand on a higher tread than the centre.
        // Sweep the torso over measured support; keep its roof and leave the
        // hoof-height band to CMC's StepUp, floor/perch and headroom checks.
        const float Top = Half + BodyHalf;
        const float Bottom = FMath::Clamp(Move.MaxStepHeight + UCharacterMovementComponent::MAX_FLOOR_DIST,
                                           Half-BodyHalf, Top-2.f*BodyRadius);
        const auto Torso = FCollisionShape::MakeCapsule(BodyRadius, (Top-Bottom)*.5f);
        const double Middle = (Top+Bottom)*.5 + UCharacterMovementComponent::MIN_FLOOR_DIST;
        FVector Floor = Support;
        if (!Trace.AlongFloor(Floor, Start, [](const FVector&, const FVector&){return true;})) return false;
        const auto AboveFloor = [&](FVector P)
        {
            // A lower floor must never let a probe duck under a rail or lintel.
            P.Z = FMath::Max(P.Z, Feet.Z) + Middle;
            return P;
        };
        if (!Trace.AlongFloor(Floor, End, [&](const FVector& A, const FVector& B)
            {return !Trace.Blocked(AboveFloor(A), AboveFloor(B), Torso);})) return false;
        UsedGround = true;
    }
    if (Rider)
    {
        if (UsedGround && !Delta.IsNearlyZero())
        {
            FVector Floor = Support;
            const auto AcceptFloor = [](const FVector&, const FVector&){return true;};
            if (Trace.AlongFloor(Floor, Centre, AcceptFloor))
            {
                const double StartZ = Floor.Z;
                if (Trace.AlongFloor(Floor, Centre+Delta, AcceptFloor)) Travel.Z = Floor.Z-StartZ;
            }
        }
        const FVector Head = Saddle()+Forward*14.f+FVector(0,0,77);
        if (Trace.Blocked(Head, Head+Travel+(Facing-Forward)*14.f, FCollisionShape::MakeSphere(13.f))) return false;
    }
    return true;
}

bool AStableRidingHorse::WalkableApproach(const FVector& Goal) const
{
    FHorseGroundQuery Trace(*this, Leader);
    FVector Floor = GetNavAgentLocation();
    if (FVector::DistSquared2D(Floor,Goal) > FMath::Square(460.)) return false;
    if (Trace.Move.CurrentFloor.IsWalkableFloor()) Floor.Z -= Trace.Move.CurrentFloor.GetDistanceToFloor();
    const float Half = Trace.Capsule.GetScaledCapsuleHalfHeight(), Radius = Trace.Capsule.GetScaledCapsuleRadius();
    const float Bottom = FMath::Min(Trace.Move.MaxStepHeight + UCharacterMovementComponent::MAX_FLOOR_DIST, 2.f*(Half-Radius));
    const auto Hull = FCollisionShape::MakeCapsule(Radius, Half-Bottom*.5f);
    const FVector CentreOffset(0,0,Half+Bottom*.5f+UCharacterMovementComponent::MIN_FLOOR_DIST);
    return Trace.AlongFloor(Floor, Goal, [&](const FVector& A, const FVector& B)
        {return !Trace.Blocked(A+CentreOffset, B+CentreOffset, Hull);})
        && FMath::Abs(Floor.Z-Goal.Z) <= Trace.Move.MaxStepHeight+UCharacterMovementComponent::MAX_FLOOR_DIST;
}
