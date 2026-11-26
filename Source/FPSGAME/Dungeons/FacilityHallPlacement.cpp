#include "FacilityHallEncounter.h"
#include "../Monsters/HeQueMonster.h"
#include "HeQuePumpControl.h"
#include "FacilityMonsterGpuWarmup.h"
#include "FacilityHallSpawnSubsystem.h"
#include "../UI/FPSPerformanceMetrics.h"
#include "AuthoredDungeonGenerator.h"
#include "DungeonThemeEncounter.h"
#include "../Development/DevelopmentSpawnComponent.h"
#include "UObject/UnrealType.h"
#include "../Monsters/NurseZombie.h"
#include "../Monsters/BellowSacLobber.h"
#include "../Monsters/BoundCongregate.h"
#include "../Monsters/HangingBellM09.h"
#include "../Monsters/LurkerM08Monster.h"
#include "../Monsters/MantisM27Monster.h"
#include "../Monsters/BlindSupplicantMonster.h"
#include "../Monsters/M10Mawcrawler.h"
#include "../Monsters/RootCrownRigPreview.h"
#include "../Monsters/VortexCofferM25.h"
#include "../Monsters/M66IncineratorMonster.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "../Monsters/MonsterAIController.h"
#include "../Monsters/FPSCombatHealthComponent.h"
#include "../Monsters/HumanoidKnockdownComponent.h"
#include "Components/CapsuleComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/StaticMeshActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "EngineUtils.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "GameFramework/PlayerController.h"
#include "NavigationData.h"
#include "NavigationSystem.h"
#include "TimerManager.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"


bool AFacilityHallEncounter::FindSpawn(const ACharacter* Defaults, const FVector& Candidate, FVector& Location,
    float Footprint, const FBox* AuthoredSpawnFloor) const
{
    auto Reject = [&](const TCHAR* Stage)
    {
#if WITH_EDITOR
        if (SpawnAuditFailure) SpawnAuditFailure(Stage, Candidate);
#endif
        return false;
    };
    const auto* Capsule = Defaults->GetCapsuleComponent();
    const auto* Movement = Defaults->GetCharacterMovement();
    const float Radius = Capsule->GetScaledCapsuleRadius(), HalfHeight = Capsule->GetScaledCapsuleHalfHeight();
    FNavAgentProperties Agent = Movement->GetNavAgentPropertiesRef();
    Agent.AgentRadius = Movement->ShouldUpdateNavAgentWithOwnersCollision() ? Radius : FMath::Max(Agent.AgentRadius, Radius);
    Agent.AgentHeight = Movement->ShouldUpdateNavAgentWithOwnersCollision() ? HalfHeight * 2.f : FMath::Max(Agent.AgentHeight, HalfHeight * 2.f);
    // M08 traverses physical surfaces, matching the development spawner's
    // placement contract. It still needs clear space and supported floor below.
    const bool bSurfaceCrawler = Defaults->IsA<ALurkerM08Monster>();
    auto* Nav = FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    const ANavigationData* Data = Nav ? Nav->GetNavDataForProps(Agent, Candidate) : nullptr;
    if (!bSurfaceCrawler && (!Data || Data->GetConfig().AgentRadius + KINDA_SMALL_NUMBER < Agent.AgentRadius
        || Data->GetConfig().AgentHeight + KINDA_SMALL_NUMBER < Agent.AgentHeight)) return Reject(TEXT("navigation_profile"));
    FCollisionQueryParams Query(SCENE_QUERY_STAT(FacilityHallSpawn), false, this);
    FHitResult Ground;
    if (!GetWorld()->LineTraceSingleByChannel(Ground, Candidate + FVector(0,0,100), Candidate - FVector(0,0,100), ECC_Pawn, Query)
        || Ground.ImpactNormal.Z < FMath::Max(.72f, Movement->GetWalkableFloorZ())
        || FMath::Abs(Ground.ImpactPoint.Z - Candidate.Z) > 40.
        || (Ground.GetActor() && Ground.GetActor()->IsA<APawn>())
        || Room.DistanceSquared(Ground.ImpactPoint) > FMath::Square(20.)) return Reject(TEXT("ground_or_room"));
    // A designated interior bay can lie outside the catalog's through-route.
    // Keep its authored floor restriction and the full room boundary; only that
    // slot substitutes its explicit bay for the route's walk mask.
    if (AuthoredSpawnFloor ? AuthoredSpawnFloor->ComputeSquaredDistanceToPoint(Ground.ImpactPoint) > FMath::Square(20.)
        : !Room.AllowsSpawn(Ground.ImpactPoint)) return Reject(TEXT("spawn_area"));
    FNavLocation Projected;
    if (!bSurfaceCrawler && (!Nav->ProjectPointToNavigation(Ground.ImpactPoint, Projected, FVector(20,20,60), Data)
        || FVector::DistSquared2D(Projected.Location, Ground.ImpactPoint) > FMath::Square(20.)
        || FMath::Abs(Projected.Location.Z - Ground.ImpactPoint.Z) > 40.)) return Reject(TEXT("navigation_projection"));
    // Chaos turns a capsule into a sphere when radius >= half-height. For
    // BoundCongregate (225/225), the 3 cm radial margin previously consumed
    // the entire 3 cm floor gap, so the clearance query touched its own floor.
    // Lift by the query shape's actual half-height before adding the floor gap.
    const float ClearanceRadius = Radius + 3.f;
    const float ClearanceHalfHeight = FMath::Max(HalfHeight, ClearanceRadius);
    Location = Ground.ImpactPoint + FVector(0,0,ClearanceHalfHeight + 3.f);
    if (GetWorld()->OverlapBlockingTestByChannel(Location, FQuat::Identity, ECC_Pawn,
        FCollisionShape::MakeCapsule(ClearanceRadius, ClearanceHalfHeight), Query)) return Reject(TEXT("capsule_overlap"));
    const float SupportRadius = FMath::Max(Radius, Footprint);
    for (const FVector Offset : { FVector(SupportRadius,0,0), FVector(-SupportRadius,0,0), FVector(0,SupportRadius,0), FVector(0,-SupportRadius,0) })
    {
        FHitResult Edge;
        const FVector Probe = Ground.ImpactPoint + Offset;
        if (!GetWorld()->LineTraceSingleByChannel(Edge, Probe + FVector(0,0,40), Probe - FVector(0,0,50), ECC_Pawn, Query)
            || Edge.ImpactNormal.Z < Movement->GetWalkableFloorZ() || FMath::Abs(Edge.ImpactPoint.Z - Ground.ImpactPoint.Z) > 30.f
            || (Edge.GetActor() && Edge.GetActor()->IsA<APawn>())) return Reject(TEXT("support_edge"));
    }
    return bSurfaceCrawler || HasSpawnRoute(Defaults,Ground.ImpactPoint,Data);
}

bool AFacilityHallEncounter::FindInitialSpawn(const FFacilityHallSlot& Slot, const ACharacter* Defaults, FVector& Location, FRotator& Facing)
{
    if (bStaffLiving) return FindStaffLivingSpawn(Slot, Defaults, Location, Facing);
    if (bFinalBossRoom) return FindFinalBossSpawn(Defaults,Location,Facing);
    if (bMedical) return FindMedicalSpawn(Slot, Defaults, Location, Facing);
    if (bFreight) return FindFreightSpawn(Slot, Defaults, Location, Facing);
    if (bEcology) return FindEcologySpawn(Slot, Defaults, Location, Facing);
    if (bPower) return FindPowerSpawn(Slot, Defaults, Location, Facing);
    if (bIncineration) return FindIncinerationSpawn(Slot, Defaults, Location, Facing);
    const bool Bellow = Slot.BellowPosition != INDEX_NONE;
    const bool Upper = Slot.BellowPosition >= 2;
    const bool Reception = Room.Module == TEXT("FacilityReceptionHall");
    const FTransform HallTransform(FRotator(0, Room.Yaw, 0), Room.Origin);
    const auto& Cells = Room.WalkCells.IsEmpty() ? Room.Cells : Room.WalkCells;
    // Ground-floor staff and Bellow share the main hall, excluding connector sleeves.
    FBox Floor = Room.Volume;
    double Area = 0.;
    for (const FBox& Cell : Cells)
    {
        const FVector Size = Cell.GetSize();
        if (Size.X * Size.Y > Area) { Area = Size.X * Size.Y; Floor = Cell; }
    }
    if (Upper)
    {
        // Authoring contracts: reception's two open side galleries at 450 cm;
        // transit's west platform ends at 420 cm, outside the enclosed duty room.
        // These boxes are local to the module, not unrotated world coordinates.
        const bool PositiveSide = Slot.BellowPosition == 3;
        Floor = Reception
            ? FBox(FVector(-1600, PositiveSide ? 1050 : -1650, 450), FVector(1400, PositiveSide ? 1650 : -1050, 450))
            : FBox(FVector(-2400, PositiveSide ? 1050 : -1800, 420), FVector(-1600, PositiveSide ? 1800 : -1050, 420));
    }
    const float Footprint = Slot.bObjectiveElite ? ObjectiveEliteFootprint : 0.f;
    const double Margin = FMath::Max(Defaults->GetCapsuleComponent()->GetScaledCapsuleRadius(), Footprint) + 80.;
    for (int32 Attempt = 0; Attempt < 12; ++Attempt)
    {
        FVector Candidate(Placement.FRandRange(Floor.Min.X + Margin, Floor.Max.X - Margin),
            Placement.FRandRange(Floor.Min.Y + Margin, Floor.Max.Y - Margin), Upper ? Floor.Min.Z : Room.Origin.Z);
        if (Upper) Candidate = HallTransform.TransformPosition(Candidate);
        bool Occupied = false;
        for (auto It = GetWorld()->GetPlayerControllerIterator(); It; ++It)
            if (It->Get() && It->Get()->GetPawn()
                && FVector::DistSquared(It->Get()->GetPawn()->GetActorLocation(), Candidate) < FMath::Square(450.)) Occupied = true;
        if (Bellow) for (const auto& Other : Slots)
            if (Other.BellowPosition != INDEX_NONE && Other.Monster.IsValid()
                && FVector::DistSquared(Other.Monster->GetActorLocation(), Candidate) < FMath::Square(400.)) Occupied = true;
        // Reject obvious traffic/spacing conflicts before spending a navigation
        // query. FindSpawn still owns the final projected floor and capsule check.
        if (!Bellow && !Slot.bObjectiveElite && Theme.IsValid())
        {
            const float Radius = Defaults->GetSimpleCollisionRadius();
            if (!Theme->AllowsHallRestPoint(Candidate,Radius)
                || !Theme->HasHallSpace(Candidate,Radius,nullptr,70.f,false)) continue;
        }
        // Rejected upstairs positions stay upstairs; never fall back to the atrium floor.
        if (Occupied || !FindSpawn(Defaults, Candidate, Location, Footprint)) continue;
        if (!Bellow && !Slot.bObjectiveElite && Theme.IsValid())
        {
            const float Radius = Defaults->GetCapsuleComponent()->GetScaledCapsuleRadius();
            const FVector Feet = Location - FVector(0,0,Defaults->GetCapsuleComponent()->GetScaledCapsuleHalfHeight());
            if (!Theme->AllowsHallRestPoint(Feet, Radius)
                || !Theme->HasHallSpace(Feet, Radius, nullptr, 70.f, false)) continue;
        }
        Facing = FRotator(0, Placement.FRandRange(-180.f, 180.f), 0);
        if (Upper)
        {
            const FVector Inward = Reception ? FVector(0, Slot.BellowPosition == 3 ? -1 : 1, 0) : FVector::ForwardVector;
            Facing = HallTransform.TransformVectorNoScale(Inward).Rotation();
            Facing.Yaw += Placement.FRandRange(-25.f, 25.f);
        }
        return true;
    }
    return false;
}

AFacilityHallEncounter::~AFacilityHallEncounter() = default;

