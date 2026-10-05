#include "LurkerSurfaceRoute.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "NavigationData.h"
#include "NavigationPath.h"
#include "NavigationSystem.h"

namespace LurkerSurfaceRoute
{
bool Clear(UWorld* World, const AActor* Owner, FVector Center, float Radius)
{
    FCollisionQueryParams Query(SCENE_QUERY_STAT(M08SurfaceRoom), false, Owner);
    return World && !World->OverlapBlockingTestByChannel(Center, FQuat::Identity, ECC_Pawn,
        FCollisionShape::MakeSphere(Radius), Query);
}
bool Support(UWorld* World, const AActor* Owner, FVector From, FVector To, float Radius, FLurkerSurfacePoint& Out)
{
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(M08SurfaceSupport), false, Owner);
    if (!World || !World->LineTraceSingleByChannel(Hit, From, To, ECC_Pawn, Query)
        || Hit.bStartPenetrating || !Hit.GetActor() || Hit.GetActor()->IsA<APawn>()) return false;
    Out.Normal = Hit.ImpactNormal.GetSafeNormal();
    Out.Center = Hit.ImpactPoint + Out.Normal * (Radius + 3.f);
    return Clear(World, Owner, Out.Center, Radius);
}
bool Segment(UWorld* World, const AActor* Owner, FVector From, FVector To, float Radius)
{
    FHitResult Hit; FCollisionQueryParams Query(SCENE_QUERY_STAT(M08SurfaceSweep), false, Owner);
    return World && !World->SweepSingleByChannel(Hit, From, To, FQuat::Identity, ECC_Pawn,
        FCollisionShape::MakeSphere(Radius), Query);
}
FVector Arc(FVector Start, FVector End, FVector Outward, float Height, float Alpha)
{
    // Wall launches first separate from the support; all arcs still obey world gravity direction.
    return FMath::Lerp(Start, End, Alpha) + FVector::UpVector * (Height * FMath::Sin(PI * Alpha))
        + Outward * (80.f * FMath::Sin(PI * Alpha));
}
bool ClearArc(UWorld* World, const AActor* Owner, FVector Start, FVector End, FVector Outward, float Height, float Radius)
{
    FVector Previous = Start;
    for (int32 Step = 1; Step <= 20; ++Step)
    {
        const FVector Next = Arc(Start, End, Outward, Height, Step / 20.f);
        if (!Segment(World, Owner, Previous, Next, Radius)) return false;
        Previous = Next;
    }
    return true;
}

bool GroundGuide(UWorld* World, const AActor* Owner, const FLurkerSurfacePoint& Start,
    FVector Goal, float Radius, FVector& Guide)
{
    if (Start.Normal.Z < .65f) return false;
    const auto* Pawn = Cast<APawn>(Owner);
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(World);
    if (!Pawn || !Nav) return false;
    const FVector Feet = Start.Center - FVector::UpVector * (Radius + 3.f);
    const FVector GoalFeet = Goal - FVector::UpVector * (Radius + 3.f);
    const auto& Agent = Pawn->GetNavAgentPropertiesRef();
    const auto* Data = Nav->GetNavDataForProps(Agent, Feet);
    FNavLocation Projected;
    if (!Data || !Nav->ProjectPointToNavigation(GoalFeet, Projected, FVector(100, 100, 70), Data)) return false;
    FPathFindingQuery Query(Pawn, *Data, Feet, Projected.Location, Data->GetDefaultQueryFilter());
    Query.SetAllowPartialPaths(false);
    const FPathFindingResult Path = Nav->FindPathSync(Agent, Query);
    if (!Path.IsSuccessful() || !Path.Path.IsValid() || Path.Path->IsPartial()) return false;
    // Follow a complete corridor around walls instead of repeatedly picking
    // a locally closer point on the wrong side. No separate MoveTo competes
    // with the monster's swept surface movement.
    const auto& Points = Path.Path->GetPathPoints();
    for (int32 I = 1; I < Points.Num(); ++I)
    {
        if (FVector::DistSquared(Points[I].Location, Feet) < FMath::Square(55.f)) continue;
        Guide = I == Points.Num() - 1 ? Goal : Points[I].Location + FVector::UpVector * (Radius + 3.f);
        return true;
    }
    return false;
}

bool Build(UWorld* World, const AActor* Owner, const FLurkerSurfacePoint& Start, FVector Goal,
    float Radius, const TArray<FVector>& Recent, TArray<FLurkerSurfacePoint>& Out)
{
    Out.Reset();
    struct FNode
    {
        FLurkerSurfacePoint Point;
        TArray<FLurkerSurfacePoint, TInlineAllocator<2>> Bridge;
        float Cost = 0.f, Estimate = 0.f;
        int32 Parent = INDEX_NONE;
        bool Closed = false;
    };
    TArray<FNode> Nodes; Nodes.Reserve(160);
    FNode First; First.Point = Start; First.Estimate = FVector::Distance(Start.Center, Goal); Nodes.Add(First);
    int32 Best = INDEX_NONE; float BestDistance = First.Estimate;
    constexpr float Stride = 115.f;
    // Bounded receding-horizon search; no global actor scans or unbounded per-frame graph build.
    for (int32 Iteration = 0; Iteration < 40 && Nodes.Num() < 156; ++Iteration)
    {
        int32 At = INDEX_NONE; float Score = FLT_MAX;
        for (int32 I = 0; I < Nodes.Num(); ++I)
            if (!Nodes[I].Closed && Nodes[I].Cost + Nodes[I].Estimate < Score)
            { Score = Nodes[I].Cost + Nodes[I].Estimate; At = I; }
        if (At == INDEX_NONE) break;
        Nodes[At].Closed = true;
        const FLurkerSurfacePoint Current = Nodes[At].Point;
        const float Remaining = FVector::Distance(Current.Center, Goal);
        if (At && Remaining < BestDistance) { BestDistance = Remaining; Best = At; }
        if (At && Remaining < 40.f) { Best = At; break; }
        FVector Forward = FVector::VectorPlaneProject(Goal - Current.Center, Current.Normal).GetSafeNormal();
        if (Forward.IsNearlyZero()) Forward = FVector::VectorPlaneProject(FVector::UpVector, Current.Normal).GetSafeNormal();
        if (Forward.IsNearlyZero()) Forward = FVector::ForwardVector;
        const FVector Side = FVector::CrossProduct(Current.Normal, Forward).GetSafeNormal();
        const FVector Directions[] = {Forward, (Forward + Side).GetSafeNormal(), (Forward - Side).GetSafeNormal(), Side, -Side, -Forward};
        for (const FVector Direction : Directions)
        {
            FLurkerSurfacePoint Next;
            const float StepLength = FMath::Clamp(Remaining, 35.f, Stride);
            const FVector Ahead = Current.Center + Direction * StepLength;
            // Prefer the same support plane. A low object in front is not an
            // invitation to climb when a clear floor approach is available.
            bool Found = Support(World, Owner, Ahead + Current.Normal * 20.f,
                Ahead - Current.Normal * (Radius + 60.f), Radius, Next);
            if (Found && FVector::DotProduct(Current.Normal, Next.Normal) > .8f
                && !Segment(World, Owner, Current.Center, Next.Center, Radius)) Found = false;
            if (!Found) Found = Support(World, Owner, Current.Center, Ahead + Direction * Radius, Radius, Next);
            if (!Found)
            {
                // Around a convex lip: look back toward the newly exposed side.
                const FVector OverLip = Ahead - Current.Normal * (Radius + Stride * .65f);
                Found = Support(World, Owner, OverLip, OverLip - Direction * (Stride + Radius + 30.f), Radius, Next);
            }
            if (!Found || FVector::DistSquared(Current.Center, Next.Center) < FMath::Square(18.f)) continue;
            bool Duplicate = false;
            for (const FNode& Node : Nodes)
                if (FVector::DistSquared(Node.Point.Center, Next.Center) < FMath::Square(48.f)
                    && FVector::DotProduct(Node.Point.Normal, Next.Normal) > .7f) { Duplicate = true; break; }
            if (Duplicate) continue;
            FNode Candidate; Candidate.Point = Next; Candidate.Parent = At;
            if (!Segment(World, Owner, Current.Center, Next.Center, Radius))
            {
                if (FVector::DotProduct(Current.Normal, Next.Normal) > .8f) continue;
                const FVector A = Current.Center + Next.Normal * (Radius + 12.f);
                const FVector B = Next.Center + Current.Normal * (Radius + 12.f);
                if (!Segment(World, Owner, Current.Center, A, Radius) || !Segment(World, Owner, A, B, Radius)
                    || !Segment(World, Owner, B, Next.Center, Radius)) continue;
                Candidate.Bridge.Add({A, Current.Normal}); Candidate.Bridge.Add({B, Next.Normal});
            }
            float Travel = FVector::Distance(Current.Center, Next.Center);
            Travel += (1.f - FMath::Clamp(float(FVector::DotProduct(Current.Normal, Next.Normal)), -1.f, 1.f)) * 90.f;
            if (Next.Normal.Z < .65f && FMath::Abs(Goal.Z - Start.Center.Z) < 100.f) Travel += 45.f;
            for (const FVector Visited : Recent)
                if (FVector::DistSquared(Visited, Next.Center) < FMath::Square(70.f)) { Travel += 180.f; break; }
            Candidate.Cost = Nodes[At].Cost + Travel;
            Candidate.Estimate = FVector::Distance(Next.Center, Goal) * 1.25f;
            Nodes.Add(MoveTemp(Candidate));
            if (Nodes.Num() >= 156) break;
        }
    }
    // Permit a committed wall detour when it is needed to get over an obstacle,
    // but never choose arbitrary outward floor frontiers around a reached goal.
    if (First.Estimate > 200.f && (Best == INDEX_NONE || BestDistance >= First.Estimate - 25.f))
    {
        float Frontier = FLT_MAX;
        for (int32 I = 1; I < Nodes.Num(); ++I)
        {
            const auto& Node = Nodes[I];
            if (Node.Point.Normal.Z > .65f || Node.Cost < 120.f
                || FVector::Distance(Node.Point.Center, Start.Center) > 500.f) continue;
            bool Visited = false;
            for (const FVector Point : Recent)
                if (FVector::DistSquared(Point, Node.Point.Center) < FMath::Square(90.f)) { Visited = true; break; }
            if (!Visited && Node.Cost + Node.Estimate < Frontier)
            { Best = I; Frontier = Node.Cost + Node.Estimate; }
        }
    }
    if (Best == INDEX_NONE) return false;
    TArray<int32> Chain;
    for (int32 I = Best; I > 0; I = Nodes[I].Parent) Chain.Insert(I, 0);
    for (int32 I : Chain)
    {
        for (const auto& Bridge : Nodes[I].Bridge) Out.Add(Bridge);
        Out.Add(Nodes[I].Point);
        if (Out.Num() >= 8) break;
    }
    return !Out.IsEmpty();
}
}
