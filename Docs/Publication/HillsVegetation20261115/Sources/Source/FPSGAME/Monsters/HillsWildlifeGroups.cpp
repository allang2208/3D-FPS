#include "HillsWildlifeGroups.h"
#include "WildlifeSubsystem.h"
#include "WildlifeAnimal.h"
#include "../WorldGeneration/TemperateHillsWorld.h"
#include "../WorldGeneration/TemperateForestHabitat.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"

namespace
{
bool HerdSpecies(const FString& Id)
{
    return Id == TEXT("deer_doe") || Id == TEXT("deer_stag") || Id == TEXT("boar") || Id == TEXT("crow");
}

bool DryGround(const ATemperateHillsWorld& Hills, const FVector& P)
{
    const double Limit = Hills.SizeMeters * 50. - 160.;
    if (FMath::Abs(P.X) > Limit || FMath::Abs(P.Y) > Limit) return false;
    const auto River = Hills.SampleRiver(P.X, P.Y);
    return River.Distance > River.HalfWidth + 65. && !Hills.SampleForestWater(P.X, P.Y).Wet &&
        Hills.SurfaceNormal(P.X, P.Y).Z >= .76;
}

// Height includes the player's terrain edits. The trace also requires a streamed, walkable surface.
bool Footing(const ATemperateHillsWorld& Hills, FVector& P, float Radius, float HalfHeight)
{
    if (!DryGround(Hills, P)) return false;
    P.Z = Hills.Height(P.X, P.Y);
    FHitResult Hit;
    const UWorld* World = Hills.GetWorld();
    const FCollisionObjectQueryParams Solid(ECC_WorldStatic);
    if (!World->LineTraceSingleByObjectType(Hit, P + FVector::UpVector * 110.,
        P - FVector::UpVector * 140., Solid) || Hit.ImpactNormal.Z < .76) return false;
    P.Z = Hit.ImpactPoint.Z + HalfHeight + Radius * (1. / Hit.ImpactNormal.Z - 1.) + 3.;
    return !World->OverlapAnyTestByObjectType(P, FQuat::Identity, Solid, FCollisionShape::MakeCapsule(Radius, HalfHeight));
}

bool OnBoarRiverbank(const ATemperateHillsWorld& Hills, const FVector& Point)
{
    const auto River = Hills.SampleRiver(Point.X, Point.Y);
    const double FromWaterEdge = River.Distance - River.HalfWidth;
    return FromWaterEdge >= 800. && FromWaterEdge <= 3000. && River.Wet <= 0.;
}

bool BoarBankFooting(const ATemperateHillsWorld& Hills, const FWildlifeSpecies& Species,
    TConstArrayView<FVector> Players, FVector& Point)
{
    const double Region = Hills.RainforestWeight(Point.X, Point.Y);
    if (Region < .5 || !OnBoarRiverbank(Hills, Point)) return false;
    if (TemperateForestHabitat::Canopy(Point.X, Point.Y, Hills.Seed, Region, Hills.EcologyProfile()) < .55) return false;
    const double MinDistanceSq = FMath::Square(WildlifeCatalog::Get().Spawn.MinPlayerDistance);
    for (const FVector& Player : Players)
        if (FVector::DistSquared2D(Point, Player) < MinDistanceSq) return false;
    // Footing also rejects forest pools and requires loaded, walkable collision.
    return Footing(Hills, Point, Species.CapsuleRadius, Species.CapsuleHalfHeight);
}

bool GroundRoute(const ATemperateHillsWorld& Hills, const FVector& From, const FVector& To)
{
    const int32 Steps = FMath::Max(1, FMath::CeilToInt(FVector::Dist2D(From, To) / 240.));
    for (int32 Step = 1; Step <= Steps; ++Step)
        if (!DryGround(Hills, FMath::Lerp(From, To, double(Step) / Steps))) return false;
    return true;
}

bool ChooseSite(const ATemperateHillsWorld& Hills, const FHillsWildlifeGroup& G,
    const FVector& Center, bool bAlarm, const FHillsWildlifeSettings& Settings, FVector& Out)
{
    const auto* Species = G.Members[0].Animal->Species();
    const float Range = G.bCrows ? Settings.FlightDistance : bAlarm ? Settings.EscapeDistance : Settings.PastureDistance;
    FVector Axis = bAlarm ? (Center - G.Threat).GetSafeNormal2D() : FVector::ZeroVector;
    if (Axis.IsNearlyZero()) Axis = FVector::ForwardVector.RotateAngleAxis(FMath::FRandRange(-180.f, 180.f), FVector::UpVector);
    double Best = -DBL_MAX;
    for (int32 Attempt = 0; Attempt < 16; ++Attempt)
    {
        const float Angle = bAlarm ? (Attempt % 2 ? -1.f : 1.f) * ((Attempt / 2) * 11.f + FMath::FRandRange(0.f, 9.f))
                                   : Attempt * 137.5f;
        const float Radius = Range * FMath::FRandRange(.70f, 1.12f) * (Attempt < 10 ? 1.f : .45f);
        FVector P = Center + Axis.RotateAngleAxis(Angle, FVector::UpVector) * Radius;
        if (!Footing(Hills, P, Species->CapsuleRadius, Species->CapsuleHalfHeight)) continue;
        if (!G.bCrows && !GroundRoute(Hills, Center, P)) continue;
        const double Region = Hills.RainforestWeight(P.X,P.Y);
        const double Forest = TemperateForestHabitat::Canopy(P.X, P.Y, Hills.Seed, Region, Hills.EcologyProfile());
        const double Moist = TemperateForestHabitat::Moisture(P.X, P.Y, Hills.Seed, Region, Hills.EcologyProfile());
        const auto Land = TemperateForestHabitat::Upland(Hills.SurfaceNormal(P.X, P.Y), Forest, Moist, Region, Hills.EcologyProfile());
        double Habitat = Species->Id == TEXT("boar") ? 1. - FMath::Abs(Forest - .48) + .25 * Moist
            : (1. - Forest) + Land.Meadow;
        if (!bAlarm && Species->Id == TEXT("boar") && Region >= .5 && Forest >= .55 && OnBoarRiverbank(Hills, P))
            Habitat += 2.;
        const double Score = Habitat * (bAlarm ? .25 : 1.) + Radius / Range * .4 +
            (bAlarm ? 2. * FVector::DotProduct(Axis, (P - Center).GetSafeNormal2D()) : 0.) + FMath::FRandRange(0.f, .3f);
        if (Score > Best) { Best = Score; Out = P; }
    }
    return Best > -DBL_MAX;
}

// Keep the same relative slot even when one animal dies. Rotate only when picking a new route.
FVector Slot(const FHillsWildlifeGroup& G, const FHillsWildlifeMember& M)
{
    const FVector Axis = (G.Destination - G.Start).GetSafeNormal2D();
    return Axis.IsNearlyZero() ? M.Offset : Axis * M.Offset.X + FVector(-Axis.Y, Axis.X, 0.) * M.Offset.Y;
}

FVector StepAround(const ATemperateHillsWorld& Hills, const FHillsWildlifeGroup& G,
    const AColdSteelAnimal& Animal, const FVector& Goal, float Side)
{
    const FVector From = Animal.GetActorLocation();
    const FVector Forward = (Goal - From).GetSafeNormal2D();
    const FVector Right(-Forward.Y, Forward.X, 0.);
    FVector Dir = Forward;
    for (const auto& Other : G.Members)
    {
        if (Other.Animal.Get() == &Animal) continue;
        const FVector Nearby = Other.Animal->GetActorLocation() - From;
        const double Ahead = FVector::DotProduct(Nearby, Forward);
        const double Spacing = (Animal.Species()->CapsuleRadius + Other.Animal->Species()->CapsuleRadius) * 1.65;
        if (Ahead <= 0. || Ahead >= Spacing * 1.5 || Nearby.SizeSquared2D() > Spacing * Spacing * 2.25) continue;
        const double Lateral = FVector::DotProduct(Nearby, Right);
        if (FMath::Abs(Lateral) < Spacing)
            Dir += Right * (Lateral >= 0. ? -1. : 1.) * (1. - FMath::Abs(Lateral) / Spacing);
    }
    Dir = Dir.GetSafeNormal2D();
    const double Reach = FMath::Min(220., FVector::Dist2D(From, Goal));
    const float Radius = Animal.Species()->CapsuleRadius * .78f;
    for (float Angle : { 0.f, 38.f, -38.f, 76.f, -76.f, 108.f, -108.f })
    {
        const FVector Step = From + Dir.RotateAngleAxis(Angle * Side, FVector::UpVector) * Reach;
        if (!DryGround(Hills, Step)) continue;
        FVector ProbeEnd = Step;
        ProbeEnd.Z = From.Z + Hills.Height(Step.X, Step.Y) - Hills.Height(From.X, From.Y);
        FHitResult Hit;
        if (!Hills.GetWorld()->SweepSingleByObjectType(Hit, From, ProbeEnd, FQuat::Identity,
            FCollisionObjectQueryParams(ECC_WorldStatic), FCollisionShape::MakeSphere(Radius))) return Step;
    }
    return From;
}

void GuideHerd(const ATemperateHillsWorld& Hills, FHillsWildlifeGroup& G, const FVector& Center,
    double Now, const FHillsWildlifeSettings& Settings)
{
    double RearDistance = 0.;
    for (const auto& M : G.Members)
        if (!M.Animal->IsDistancePaused())
            RearDistance = FMath::Max(RearDistance, FVector::Dist2D(M.Animal->GetActorLocation(), G.Destination + Slot(G, M)));
    bool bAllAtPasture = true;
    for (auto& M : G.Members)
    {
        AColdSteelAnimal* Animal = M.Animal.Get();
        if (Animal->IsDistancePaused()) continue;
        const FVector Here = Animal->GetActorLocation();
        FVector Goal = G.Destination + Slot(G, M);
        if (!DryGround(Hills, Goal)) Goal = G.Destination;
        const double Distance = FVector::Dist2D(Here, Goal);
        const bool bAtSlot = Distance < 95.;
        bAllAtPasture &= bAtSlot;
        const bool bWaitForRear = !G.bEscaping && RearDistance - Distance > Settings.RegroupDistance;
        const bool bCatchUp = FVector::Dist2D(Here, Center) > Settings.RegroupDistance * .52 &&
            Distance > FVector::Dist2D(Center, G.Destination);
        const bool bHold = bAtSlot || bWaitForRear;
        const FVector Waypoint = bHold ? Here : StepAround(Hills, G, *Animal, Goal, M.Offset.Y >= 0 ? 1.f : -1.f);
        Animal->SetHerdOrder(Waypoint, bHold, bCatchUp, G.bEscaping);
    }
    if (G.bTravelling && bAllAtPasture)
    {
        G.bTravelling = false;
        G.NextMove = Now + Settings.ForageSeconds * FMath::FRandRange(.8f, 1.3f);
    }
}

// Move a slot to a nearby clear patch if a trunk or the bank overlaps it.
bool FindLanding(const ATemperateHillsWorld& Hills, const FVector& Wanted, const FWildlifeSpecies& Row,
    float Phase, FVector& Out)
{
    for (int32 I = 0; I < 12; ++I)
    {
        FVector Candidate = Wanted + FVector::ForwardVector.RotateAngleAxis(Phase * 38.f + I * 137.5f,
            FVector::UpVector) * (50.f * I);
        if (!Footing(Hills, Candidate, Row.CapsuleRadius, Row.CapsuleHalfHeight)) continue;
        FHitResult Hit;
        if (Hills.GetWorld()->SweepSingleByObjectType(Hit, Candidate, Candidate + FVector::UpVector * 350.,
            FQuat::Identity, FCollisionObjectQueryParams(ECC_WorldStatic), FCollisionShape::MakeSphere(Row.CapsuleRadius))) continue;
        Out = Candidate;
        return true;
    }
    return false;
}

void StartBirdFlight(const ATemperateHillsWorld& Hills, const FHillsWildlifeGroup& G, FHillsWildlifeMember& M, double Now)
{
    M.bLanded = false;
    const FVector Here = M.Animal->GetActorLocation();
    M.FlightOrigin = M.bNeedsFlightRoute ? Here : G.Start + Slot(G, M);
    M.bNeedsFlightRoute = false;
    M.FlightStart = Now + M.Phase * .19;
    M.StartClearance = M.Animal->InFlockFlight() ? FMath::Max(0., Here.Z -
        Hills.Height(Here.X, Here.Y) - M.Animal->Species()->CapsuleHalfHeight - 4.) : 0.;
    M.NextLandingSearch = M.FlightStart + G.Duration + 5.;
    M.Landing = G.Destination;
    FindLanding(Hills, G.Destination + Slot(G, M), *M.Animal->Species(), M.Phase, M.Landing);
}

void StartRoute(const ATemperateHillsWorld& Hills, FHillsWildlifeGroup& G, const FVector& Center, const FVector& Site, double Now,
    const FHillsWildlifeSettings& Settings, bool bAlarm)
{
    G.Start = Center;
    G.Destination = Site;
    G.RouteStart = Now;
    G.bTravelling = true;
    G.bEscaping = bAlarm;
    const FVector Delta = Site - Center;
    G.Bend = FVector(-Delta.Y, Delta.X, 0.) * FMath::FRandRange(-.24f, .24f);
    G.Duration = FMath::Max(4., (Delta.Size2D() + Settings.FlightHeight) / Settings.FlightSpeed);
    G.NextMove = Now + (G.bCrows ? G.Duration + 10. : Delta.Size2D() / G.Members[0].Animal->Species()->WalkSpeed * 2. + 12.);
    if (G.bCrows)
    {
        for (auto& M : G.Members)
        {
            if (M.Animal->IsDistancePaused()) M.bNeedsFlightRoute = true;
            else StartBirdFlight(Hills, G, M, Now);
        }
    }
}

// Sample the same curved route a little ahead of each bird's individual flight phase.
void GuideFlock(const ATemperateHillsWorld& Hills, FHillsWildlifeGroup& G, double Now, const FHillsWildlifeSettings& Settings)
{
    bool bAllLanded = true;
    for (auto& M : G.Members)
    {
        AColdSteelAnimal* Bird = M.Animal.Get();
        if (Bird->IsDistancePaused()) continue;
        if (M.bNeedsFlightRoute) StartBirdFlight(Hills, G, M, Now);
        if (M.bLanded) continue;
        const auto* Row = Bird->Species();
        const FVector Here = Bird->GetActorLocation();
        const double Age = Now - M.FlightStart;
        if (Age < 0.) { bAllLanded = false; continue; }
        const double T = FMath::Clamp((Age + .50) / G.Duration, 0., 1.);
        if (Now >= M.NextLandingSearch)
        {
            // A new terrain edit or another landing bird can close the original approach.
            const FVector Nearby = Here + (M.Landing - Here).GetClampedToMaxSize2D(280.);
            FindLanding(Hills, Nearby, *Row, M.Phase + float(Now), M.Landing);
            M.NextLandingSearch = Now + 4.;
        }
        const FVector Landing = M.Landing;
        const double Dist = FVector::Dist2D(Here, Landing);
        // Use the floor under this bird, including undulations between landing slots.
        if (T >= .94 && Dist < 95.)
        {
            FVector Contact = Here;
            if (Footing(Hills, Contact, Row->CapsuleRadius, Row->CapsuleHalfHeight) && FMath::Abs(Here.Z - Contact.Z) < 16.)
            {
                Bird->SetHerdOrder(Here, true, false, false);
                M.bLanded = true;
                continue;
            }
        }
        bAllLanded = false;
        const double Arc = FMath::Sin(PI * T);
        FVector Waypoint = FMath::Lerp(M.FlightOrigin, Landing, T) + G.Bend * Arc;
        const FVector Heading = (G.Destination - G.Start).GetSafeNormal2D();
        Waypoint += FVector(-Heading.Y, Heading.X, 0.) * (Arc * 75. * FMath::Sin(Age * .92 + M.Phase * 1.6));
        const double Clearance = Settings.FlightHeight * FMath::Pow(FMath::Max(0., Arc), .84) * (1. + .045 * FMath::Sin(M.Phase));
        Waypoint.Z = Hills.Height(Waypoint.X, Waypoint.Y) + Row->CapsuleHalfHeight + 4.
            + FMath::Max(Clearance, M.StartClearance * (1. - T));
        const bool bApproaching = T > .86 && Dist < 550.;
        if (T >= 1.) Waypoint = Landing;
        // A lagging bird first closes horizontal distance above the local terrain, then descends.
        if (T > .65 && Dist > 240.)
            Waypoint.Z = FMath::Max(Waypoint.Z, Hills.Height(Here.X, Here.Y) + Row->CapsuleHalfHeight + FMath::Min(Dist * .40, double(Settings.FlightHeight)));
        const FVector Ahead = (Waypoint - Here).GetClampedToMaxSize(320.);
        FHitResult Block;
        if ((!bApproaching || Dist > 110.) && Hills.GetWorld()->SweepSingleByObjectType(Block, Here, Here + Ahead,
            FQuat::Identity, FCollisionObjectQueryParams(ECC_WorldStatic), FCollisionShape::MakeSphere(Row->CapsuleRadius * .7f)))
        {
            Waypoint = Here + FVector::UpVector * 240. + Block.ImpactNormal.GetSafeNormal2D() * 110.;
        }
        const bool bLanding = bApproaching && Dist < 240. && Here.Z - Landing.Z < 210.;
        const bool bGlide = T > .20 && FMath::Fmod(Age + M.Phase * .47, 4.2) > 2.4;
        const EWildlifeState Phase = Age < 1.25 && M.StartClearance < 40.f ? EWildlifeState::TakeOff : bLanding ? EWildlifeState::Land :
            bGlide ? EWildlifeState::Glide : EWildlifeState::Fly;
        Bird->SetFlightOrder(Waypoint, Phase, G.bEscaping);
    }
    if (bAllLanded)
    {
        G.bTravelling = false;
        G.NextMove = Now + Settings.ForageSeconds * FMath::FRandRange(.55f, 1.1f);
    }
}
}

ATemperateHillsWorld* UWildlifeSubsystem::FindHills()
{
    if (Hills.IsValid()) return Hills.Get();
    if (!IsWildlifeMap(GetWorld())) return nullptr;
    for (TActorIterator<ATemperateHillsWorld> It(GetWorld()); It; ++It) { Hills = *It; break; }
    return Hills.Get();
}

bool UWildlifeSubsystem::ResolveSpawnCenter(const FWildlifeSpecies& Species, const FVector& Probe,
    FVector& OutLocation)
{
    const ATemperateHillsWorld* Terrain = FindHills();
    OutLocation = Probe;
    return Terrain && Terrain->bSurfaceReady && Footing(*Terrain, OutLocation, Species.CapsuleRadius, Species.CapsuleHalfHeight);
}

void UWildlifeSubsystem::SpawnRiverbankBoars(const ATemperateHillsWorld& Terrain, const FWildlifeSpecies& Species,
    TConstArrayView<FVector> Players, const FVector& Center, int32 Wanted)
{
    if (Wanted < Species.HerdMin) return;
    const auto& Settings = WildlifeCatalog::Get().Spawn;
    const float StartAngle = FMath::FRandRange(0.f, 360.f);
    TArray<FVector, TInlineAllocator<4>> Sites;
    // Sample around the player in different directions to find narrow stretches of wooded bank.
    for (int32 I = 0; I < 24; ++I)
    {
        const FVector Dir = FVector::ForwardVector.RotateAngleAxis(StartAngle + I * 137.5f, FVector::UpVector);
        FVector Anchor = Center + Dir * FMath::FRandRange(Settings.SpawnMinDistance, Settings.SpawnMaxDistance);
        if (!BoarBankFooting(Terrain, Species, Players, Anchor)) continue;
        Sites.Reset();
        Sites.Add(Anchor);
        const float Heading = FMath::FRandRange(0.f, 360.f);
        for (int32 J = 0; J < 8 && Sites.Num() < Wanted; ++J)
        {
            const FVector Offset = FVector::ForwardVector.RotateAngleAxis(Heading + J * 137.5f, FVector::UpVector);
            FVector Member = Anchor + Offset * FMath::FRandRange(180.f, 400.f);
            if (Sites.ContainsByPredicate([&](const FVector& Other) {
                return FVector::DistSquared2D(Other, Member) < FMath::Square(2. * Species.CapsuleRadius + 30.);
            })) continue;
            if (BoarBankFooting(Terrain, Species, Players, Member) && GroundRoute(Terrain, Anchor, Member))
                Sites.Add(Member);
        }
        if (Sites.Num() >= Species.HerdMin) break;
    }
    if (Sites.Num() < Species.HerdMin) return;
    TArray<AColdSteelAnimal*> Members;
    for (const FVector& Site : Sites)
    {
        const FRotator Facing(0., FMath::FRandRange(0.f, 360.f), 0.);
        // Collisions may refuse a slot but must never move it off the approved bank.
        if (auto* Animal = Cast<AColdSteelAnimal>(SpawnOne(Species, Site, Facing,
            ESpawnActorCollisionHandlingMethod::DontSpawnIfColliding))) Members.Add(Animal);
    }
    if (Members.Num() < Species.HerdMin)
    {
        for (auto* Animal : Members) { Spawned.Remove(Animal); Animal->Destroy(); }
        return;
    }
    RegisterHillsGroup(Members);
}

void UWildlifeSubsystem::RegisterHillsGroup(const TArray<AColdSteelAnimal*>& Animals)
{
    if (Animals.IsEmpty() || !GetWorld() || GetWorld()->GetNetMode() == NM_Client || !FindHills()) return;
    const AColdSteelAnimal* First = Animals[0];
    if (!IsValid(First) || !First->Species() || !HerdSpecies(First->Species()->Id)) return;
    FHillsWildlifeGroup Group;
    Group.bCrows = First->Species()->Id == TEXT("crow");
    const float Yaw = FMath::FRandRange(-180.f, 180.f);
    for (AColdSteelAnimal* Animal : Animals)
    {
        if (!IsValid(Animal) || Animal->IsDead() || Animal->Species() != First->Species()) continue;
        const int32 Index = Group.Members.Num();
        auto& Member = Group.Members.AddDefaulted_GetRef();
        Member.Animal = Animal;
        Member.Phase = Index + FMath::FRandRange(0.f, .55f);
        const float Radius = Animals.Num() == 1 ? 0.f : (Group.bCrows ? 120.f : 155.f) * FMath::Sqrt(Index + .6f);
        Member.Offset = FVector::ForwardVector.RotateAngleAxis(Yaw + Index * 137.5f, FVector::UpVector) * Radius;
        Group.Destination += Animal->GetActorLocation();
        Animal->SetHerdOrder(Animal->GetActorLocation(), true, false, false);
    }
    if (Group.Members.IsEmpty()) return;
    Group.Destination /= Group.Members.Num();
    Group.Start = Group.Destination;
    Group.NextMove = GetWorld()->GetTimeSeconds() + FMath::FRandRange(2.f, 5.f);
    HillsGroups.Add(MoveTemp(Group));
}

void UWildlifeSubsystem::AlarmHillsGroup(AColdSteelAnimal* Animal, const FVector& Source)
{
    for (auto& G : HillsGroups)
        if (G.Members.ContainsByPredicate([Animal](const auto& M) { return M.Animal.Get() == Animal; }))
        {
            G.Threat = Source;
            G.AlarmUntil = GetWorld()->GetTimeSeconds() + 6.;
            break;
        }
}

bool UWildlifeSubsystem::FindEscapeStep(const ACharacter& Animal, const FVector& Threat, FVector& Out)
{
    const auto* Terrain = FindHills();
    if (!Terrain || !Terrain->bSurfaceReady) return false;
    const FVector Here = Animal.GetActorLocation();
    const FVector Away = (Here - Threat).GetSafeNormal2D(UE_SMALL_NUMBER, Animal.GetActorForwardVector());
    const double Side = (Animal.GetUniqueID() & 1) ? 1. : -1.;
    const float Radius = Animal.GetSimpleCollisionRadius();
    const float HalfHeight = Animal.GetSimpleCollisionHalfHeight();
    FCollisionQueryParams Query(SCENE_QUERY_STAT(WildlifeEscape), false, &Animal);
    for (double Angle : {0., 30., -30., 58., -58., 85., -85.})
    {
        FVector Step = Here + Away.RotateAngleAxis(Angle * Side, FVector::UpVector) * 370.;
        if (!GroundRoute(*Terrain, Here, Step) || !Footing(*Terrain, Step, Radius, HalfHeight)) continue;
        FHitResult Block;
        if (GetWorld()->SweepSingleByObjectType(Block, Here, Step, FQuat::Identity,
            FCollisionObjectQueryParams(ECC_WorldStatic), FCollisionShape::MakeSphere(Radius * .8f), Query)) continue;
        Out = Step;
        return true;
    }
    Out = Here;
    return false;
}

void UWildlifeSubsystem::TickHillsGroups(TConstArrayView<FVector> LivingPlayers)
{
    if (HillsGroups.IsEmpty() || !Hills.IsValid() || !Hills->bSurfaceReady) return;
    const double Now = GetWorld()->GetTimeSeconds();
    const auto& Settings = WildlifeCatalog::Get().HillsGroups;
    for (int32 Index = HillsGroups.Num() - 1; Index >= 0; --Index)
    {
        auto& G = HillsGroups[Index];
        G.Members.RemoveAll([](const auto& M) { return !M.Animal.IsValid() || M.Animal->IsDead(); });
        if (G.Members.IsEmpty()) { HillsGroups.RemoveAtSwap(Index); continue; }
        FVector Center = FVector::ZeroVector;
        int32 ActiveCount = 0;
        double Closest = DBL_MAX;
        for (auto& M : G.Members)
        {
            if (M.Animal->IsDistancePaused())
            {
                if (G.bCrows && G.bTravelling && !M.bLanded) M.bNeedsFlightRoute = true;
                continue;
            }
            ++ActiveCount;
            // The active birds may have landed while this one was suspended.
            if (M.bNeedsFlightRoute) G.bTravelling = true;
            const FVector Here = M.Animal->GetActorLocation();
            Center += Here;
            const auto* Species = M.Animal->Species();
            const double Radius = FMath::Max(Species->AggroRadius, Species->FleeRadius);
            for (const FVector& Player : LivingPlayers)
            {
                const double Distance = FVector::DistSquared(Here, Player);
                if (Distance < Radius * Radius && Distance < Closest)
                {
                    Closest = Distance;
                    G.Threat = Player;
                    G.AlarmUntil = FMath::Max(G.AlarmUntil, Now + 3.);
                }
            }
        }
        if (ActiveCount == 0)
        {
            if (G.PausedSince < 0.) G.PausedSince = Now;
            continue;
        }
        if (G.PausedSince >= 0.)
        {
            const double PausedTime = Now - G.PausedSince;
            G.NextMove += PausedTime;
            G.RouteStart += PausedTime;
            G.PausedSince = -1.;
        }
        Center /= ActiveCount;
        const bool bAlarm = Now < G.AlarmUntil;
        const bool bReachedEscape = FVector::Dist2D(Center, G.Destination) < 380.;
        const bool bRetargetEscape = bAlarm && G.bEscaping && (bReachedEscape ||
            FVector::DotProduct(G.Destination - Center, Center - G.Threat) < 0.);
        const bool bNewAlarm = bAlarm && !G.bEscaping;
        const bool bNeedsRoute = Now >= G.NextMove || bNewAlarm || (bRetargetEscape && Now - G.RouteStart > 1.5);
        if (bNeedsRoute && (!G.bCrows || !G.bTravelling || bNewAlarm ||
            (bRetargetEscape && !bReachedEscape && Now - G.RouteStart > 1.5)))
        {
            FVector Site;
            if (ChooseSite(*Hills, G, Center, bAlarm, Settings, Site))
                StartRoute(*Hills, G, Center, Site, Now, Settings, bAlarm);
            else
            {
                G.NextMove = Now + 1.5;
                G.bEscaping = bAlarm;
            }
        }
        if (G.bCrows)
        {
            if (G.bTravelling) GuideFlock(*Hills, G, Now, Settings);
            else if (!bAlarm) G.bEscaping = false;
        }
        else
        {
            if (!bAlarm && G.bEscaping && (bReachedEscape || Now - G.RouteStart > 5.))
                G.bEscaping = false;
            GuideHerd(*Hills, G, Center, Now, Settings);
        }
    }
}
