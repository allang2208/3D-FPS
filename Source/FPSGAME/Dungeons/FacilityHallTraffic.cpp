#include "FacilityHallEncounter.h"
#include "DungeonThemeEncounter.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/MonsterNavigationCache.h"
#include "../Monsters/NurseZombie.h"
#include "Components/CapsuleComponent.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "NavigationSystem.h"
#include "NavigationData.h"
#include "Engine/World.h"
#include "CoreGlobals.h"

namespace FacilityHallTraffic
{
// Reuse the BT update, with no new tick or timer. At most two actors choose a
// new goal per engine frame; each choice projects at most four candidates.
bool TakeQuerySlot()
{
    static uint64 Frame = MAX_uint64;
    static int32 Choices = 0;
    if (Frame != GFrameCounter) { Frame = GFrameCounter; Choices = 0; }
    if (Choices >= 2) return false;
    ++Choices;
    return true;
}
}

void AFacilityHallEncounter::CacheHallTrafficAreas()
{
    HallTrafficAreas.Reset();
    if (!IsHall(Room.Module)) return;
    if (const auto* Authored = Run->HallTrafficClearance(Room.Module)) HallTrafficAreas = *Authored;
    const FTransform Frame(FRotator(0,Room.Yaw,0),Room.Origin);
    auto DoorArea = [&](const FVector& Center, const FVector& Inward, double Width)
    {
        const FVector Side = FVector::CrossProduct(FVector::UpVector, Inward).GetSafeNormal();
        FBox Box(ForceInit);
        for (double X : {-80.,320.}) for (double Y : {-Width*.5,Width*.5}) for (double Z : {-45.,90.})
            Box += Frame.InverseTransformPosition(Center + Inward*X + Side*Y + FVector(0,0,Z));
        HallTrafficAreas.Add(Box);
    };
    for (const auto& Door : Room.Doors) DoorArea(Door.FloorCenter, -Door.OutwardNormal, Door.Width);
    for (const auto& Door : Doors) DoorArea(Door.FloorCenter, Door.Inward, 180.);

    // The same local authoring contract as the gallery spawn anchors. These
    // are rest exclusions, never NavModifiers or blockers. Source geometry:
    // SourceAssets/HallStairCorner20261010/author.py, reception()/transit().
    const bool Reception = Room.Module == TEXT("FacilityReceptionHall");
    for (double Sign : {-1.,1.})
    {
        const double Y = Sign * (Reception ? 880. : 1590.);
        const double HalfWidth = Reception ? 150. : 158.;
        auto StairArea = [&](double X0, double X1, double Z0, double Z1)
        { HallTrafficAreas.Add(FBox(FVector(X0,Y-HalfWidth,Z0-45.),FVector(X1,Y+HalfWidth,Z1+45.))); };
        if (Reception)
        {
            StairArea(-1000.,-800.,0.,0.);
            StairArea(-800.,-324.,0.,225.);
            StairArea(-324.,-164.,225.,225.);
            StairArea(-164.,312.,225.,450.);
            // The top landing turns toward the side gallery.
            HallTrafficAreas.Add(FBox(FVector(312.,FMath::Min(Y-150.,Sign*1100.),405.),
                FVector(552.,FMath::Max(Y+150.,Sign*1100.),495.)));
        }
        else
        {
            StairArea(-500.,-300.,0.,0.);
            StairArea(-970.,-500.,0.,210.);
            StairArea(-1130.,-970.,210.,210.);
            StairArea(-1600.,-1130.,210.,420.);
            StairArea(-1800.,-1600.,420.,420.);
        }
    }
}

bool AFacilityHallEncounter::IsHallRestPointClear(const FVector& Feet, float Radius) const
{
    const FVector Local = FTransform(FRotator(0,Room.Yaw,0),Room.Origin).InverseTransformPosition(Feet);
    for (const FBox& Area : HallTrafficAreas)
        if (Area.ExpandBy(FVector(Radius,Radius,0)).IsInsideOrOn(Local)) return false;
    return true;
}

bool AFacilityHallEncounter::HasHallSpace(const FVector& Feet, float Radius, const ACharacter* Ignore,
    float Gap, bool Reservations) const
{
    const double Now = GetWorld()->GetTimeSeconds();
    for (const auto& Slot : Slots)
    {
        const auto* Other = Slot.Monster.Get();
        if (Slot.bDefeated || !Other || Other == Ignore || Other->IsActorBeingDestroyed()) continue;
        const double Distance = Radius + Other->GetSimpleCollisionRadius() + Gap;
        const FVector OtherFeet = Other->GetNavAgentLocation();
        if (FMath::Abs(OtherFeet.Z-Feet.Z) < 80.
            && FVector::DistSquared2D(OtherFeet,Feet) < FMath::Square(Distance)) return false;
        if (Reservations && Slot.ApproachTarget.IsValid() && Slot.ApproachExpires > Now
            && FMath::Abs(Slot.ApproachGoal.Z-Feet.Z) < 80.
            && FVector::DistSquared2D(Slot.ApproachGoal,Feet) < FMath::Square(Distance)) return false;
    }
    return true;
}

bool ADungeonThemeEncounter::AllowsHallRestPoint(const FVector& Feet, float Radius) const
{
    if (!ContainsLocation(Feet)) return false;
    for (const auto& Hall : Halls)
        if (Hall.IsValid() && !Hall->IsHallRestPointClear(Feet,Radius)) return false;
    return true;
}

bool ADungeonThemeEncounter::HasHallSpace(const FVector& Feet, float Radius, const ACharacter* Ignore,
    float Gap, bool Reservations) const
{
    // Both halls share one encounter. Include neighbours even after a staff
    // member has followed a player through the connecting passage.
    for (const auto& Hall : Halls)
        if (Hall.IsValid() && !Hall->HasHallSpace(Feet,Radius,Ignore,Gap,Reservations)) return false;
    return true;
}

bool AFacilityHallEncounter::AllowsStaffIdleGoal(const ACharacter* Staff, const FVector& Feet) const
{
    if (!Staff || !Staff->IsA<ANurseZombie>() || !IsHall(Room.Module) || !Theme.IsValid()) return true;
    // Some elites also derive from ANurseZombie. Opt in by encounter slot,
    // not by base class, just as for pursuit and spawn spacing.
    if (!Slots.ContainsByPredicate([Staff](const auto& S)
        { return S.Monster.Get() == Staff && !S.bDefeated && !S.bObjectiveElite && S.BellowPosition == INDEX_NONE; })) return true;
    return Theme->AllowsHallRestPoint(Feet,Staff->GetSimpleCollisionRadius())
        && Theme->HasHallSpace(Feet,Staff->GetSimpleCollisionRadius(),Staff,25.f,false);
}

bool AFacilityHallEncounter::GetStaffPursuitGoal(ACharacter* Staff, APawn* Target, float StopRange,
    FVector& Goal, float& Acceptance)
{
    if (!HasAuthority() || bStopping || !Staff || !Target || !Theme.IsValid() || !IsHall(Room.Module)
        || !Staff->IsA<ANurseZombie>() || !Staff->GetCharacterMovement()->IsMovingOnGround()) return false;
    const int32 Index = Slots.IndexOfByPredicate([Staff](const auto& S)
        { return S.Monster.Get() == Staff && !S.bDefeated && !S.bObjectiveElite && S.BellowPosition == INDEX_NONE; });
    if (Index == INDEX_NONE) return false;
    auto& Slot = Slots[Index];
    const FVector Feet = Staff->GetNavAgentLocation(), TargetFeet = Target->GetNavAgentLocation();
    const float Radius = Staff->GetSimpleCollisionRadius();
    const double Now = GetWorld()->GetTimeSeconds();
    const auto* AI = Cast<AMonsterAIController>(Staff->GetController());
    if (FMath::Abs(Feet.Z-TargetFeet.Z) > 75. || FVector::DistSquared2D(Feet,TargetFeet) > FMath::Square(1000.)
        || !Theme->ContainsLocation(TargetFeet))
    { Slot.ApproachExpires = 0.; return false; }
    if (Slot.ApproachTarget.Get() != Target)
    { Slot.ApproachExpires = Slot.NextApproachUpdate = 0.; Slot.ApproachTarget = Target; }
    // Match the failed request's actual destination, not whichever slot goal
    // happened to be cached when its asynchronous Blocked result arrived.
    const bool Cached = Slot.ApproachExpires > Now
        && !(AI && AI->ShouldAvoidNavigationGoal(Slot.ApproachGoal))
        && FMath::Abs(Slot.ApproachGoal.Z-TargetFeet.Z) < 75.
        && FVector::DistSquared2D(Slot.ApproachGoal,TargetFeet) < FMath::Square(StopRange+Radius*2.+120.);
    if (Now < Slot.NextApproachUpdate)
    {
        if (!Cached) return false;
        Goal = Slot.ApproachGoal; Acceptance = 15.f; return true;
    }
    if (!FacilityHallTraffic::TakeQuerySlot())
    {
        Slot.NextApproachUpdate = Now + .03 + (Index%7)*.01;
        if (!Cached) return false;
        Goal = Slot.ApproachGoal; Acceptance = 15.f; return true;
    }
    TRACE_CPUPROFILER_EVENT_SCOPE(FacilityHall_StaffApproach);
    Slot.NextApproachUpdate = Now + .65 + (Index%5)*.025;
    const bool HadGoal = Slot.ApproachExpires > 0.;
    Slot.ApproachExpires = 0.;
    const double Inner = FMath::Max(double(Radius+Target->GetSimpleCollisionRadius()+12.f), double(StopRange-20.f));
    if (Inner > StopRange) return false;
    const double Outer = Inner + Radius*2. + 45.;
    FVector NearSide = (Feet-TargetFeet).GetSafeNormal2D();
    if (NearSide.IsNearlyZero()) NearSide = Staff->GetActorForwardVector().GetSafeNormal2D();
    struct FCandidate { FVector Feet; double Score; };
    TArray<FCandidate,TInlineAllocator<20>> Candidates;
    for (int32 Ring = 0; Ring < 2; ++Ring)
        for (double Angle : {0.,35.,-35.,70.,-70.,110.,-110.,145.,-145.,180.})
        {
            const FVector Point = TargetFeet + NearSide.RotateAngleAxis(Angle,FVector::UpVector)*(Ring ? Outer : Inner);
            if (!Theme->AllowsHallRestPoint(Point,Radius) || !Theme->HasHallSpace(Point,Radius,Staff,22.f,true)) continue;
            // MoveTo already rejects partial routes. Do not repeat the same failed
            // destination while the original navigation backoff is in force.
            if (AI && AI->ShouldAvoidNavigationGoal(Point)) continue;
            double Score = FVector::DistSquared2D(Point,Feet) + (Ring ? FMath::Square(180.) : 0.);
            if (HadGoal && FVector::DistSquared2D(Point,Slot.ApproachGoal) < FMath::Square(60.)) Score -= FMath::Square(90.);
            Candidates.Add({Point,Score});
        }
    Candidates.Sort([](const auto& A,const auto& B){return A.Score < B.Score;});
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const auto* Data = Nav ? Nav->GetNavDataForProps(Staff->GetNavAgentPropertiesRef(),Feet) : nullptr;
    if (!Data) return false;
    FCollisionQueryParams Query(SCENE_QUERY_STAT(HallStaffApproach),false,Staff);
    Query.AddIgnoredActor(Target);
    const float HalfHeight = Staff->GetSimpleCollisionHalfHeight();
    for (int32 I = 0; I < FMath::Min(4,Candidates.Num()); ++I)
    {
        FNavLocation Projected;
        if (!GetWorld()->GetSubsystem<UMonsterNavigationCache>()->Project(Nav,Data,Candidates[I].Feet,FVector(45,45,60),Projected)
            || FMath::Abs(Projected.Location.Z-TargetFeet.Z) > 60.
            || FVector::DistSquared2D(Projected.Location,Candidates[I].Feet) > FMath::Square(45.)
            || (AI && AI->ShouldAvoidNavigationGoal(Projected.Location))
            || !Theme->AllowsHallRestPoint(Projected.Location,Radius)
            || !Theme->HasHallSpace(Projected.Location,Radius,Staff,22.f,true)) continue;
        if (GetWorld()->OverlapBlockingTestByChannel(Projected.Location+FVector(0,0,HalfHeight+3.f),FQuat::Identity,
                ECC_Pawn,FCollisionShape::MakeCapsule(Radius,HalfHeight),Query)
            || GetWorld()->LineTraceTestByChannel(TargetFeet+FVector(0,0,70),Projected.Location+FVector(0,0,70),ECC_Visibility,Query)) continue;
        Slot.ApproachGoal = Projected.Location;
        Slot.ApproachExpires = Now + 1.;
        Goal = Slot.ApproachGoal; Acceptance = 15.f;
        return true;
    }
    // No safe stand point: retain ordinary chase/attack behaviour. Do not freeze
    // a pursuer, change aggro, or make a doorway/corner an invulnerability spot.
    return false;
}
