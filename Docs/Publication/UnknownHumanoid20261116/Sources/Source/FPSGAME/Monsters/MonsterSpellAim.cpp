#include "MonsterSpellAim.h"
#include "../Combat/RangedAttackQuery.h"
#include "GameFramework/Pawn.h"

namespace
{
    // M-07 intercept: solve |R + V*t| = speed*t for the first positive time in range.
    double InterceptTime(const FVector& Offset, const FVector& Velocity, double Speed, double MaxTime)
    {
        const double VelocitySquared = Velocity.SizeSquared();
        const double A = VelocitySquared - Speed * Speed;
        const double B = 2. * FVector::DotProduct(Offset, Velocity);
        const double C = Offset.SizeSquared();
        if (C <= UE_DOUBLE_SMALL_NUMBER) return 0.;

        double Time = MaxTime + 1.;
        const auto Consider = [&](double Root)
        {
            if (Root > 0. && Root <= MaxTime && Root < Time) Time = Root;
        };
        if (FMath::Abs(A) <= 1.e-6 * FMath::Max(VelocitySquared, Speed * Speed))
        {
            if (FMath::Abs(B) > UE_DOUBLE_SMALL_NUMBER) Consider(-C / B);
        }
        else
        {
            const double Discriminant = B * B - 4. * A * C;
            if (Discriminant >= 0.)
            {
                const double Root = FMath::Sqrt(Discriminant);
                const double Q = -.5 * (B + (B >= 0. ? Root : -Root));
                if (FMath::Abs(Q) > UE_DOUBLE_SMALL_NUMBER)
                {
                    Consider(Q / A);
                    Consider(C / Q);
                }
            }
        }
        return Time;
    }
}

bool MonsterSpellAim::ClearSegment(const APawn* Caster, const APawn* Target, const FVector& Start, const FVector& End)
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(MonsterSpellSight), true, Caster);
    Query.AddIgnoredActor(Target);
    return !RangedAttackQuery::LineTraceTest(Caster->GetWorld(), Caster, Start, End, ECC_Visibility, Query);
}

FVector MonsterSpellAim::LaunchAim(const APawn* Caster, const APawn* Target, const FVector& Origin,
    const FVector& TargetPoint, float Speed, float Range, float DownwardGravity)
{
    if (!Caster || !Target || Speed <= 0.f || Range <= 0.f) return TargetPoint;
    const double MaxTime = double(Range) / Speed;
    const FVector Velocity = Target->GetVelocity();
    const FVector Offset = TargetPoint - Origin;
    double Time = InterceptTime(Offset, Velocity, Speed, MaxTime);
    const FVector HalfGravity(0., 0., .5 * DownwardGravity);
    // Raising the launch direction also changes flight time. Refine the low arc
    // with the same moving-target solver, then check cover at the actual target height.
    if (DownwardGravity > 0.f)
        for (int32 Step = 0; Step < 5 && Time <= MaxTime; ++Step)
        {
            const double Next = InterceptTime(Offset + HalfGravity * Time * Time, Velocity, Speed, MaxTime);
            const bool Converged = FMath::Abs(Next - Time) < .0001;
            Time = Next;
            if (Converged) break;
        }
    const FVector Predicted = TargetPoint + Velocity * Time;
    if (Time <= MaxTime && (Predicted.Equals(TargetPoint, .1f) || ClearSegment(Caster, Target, Origin, Predicted)))
        return Predicted + HalfGravity * Time * Time;

    const double DirectTime = FMath::Min(Offset.Size() / Speed, MaxTime);
    return TargetPoint + HalfGravity * DirectTime * DirectTime;
}
