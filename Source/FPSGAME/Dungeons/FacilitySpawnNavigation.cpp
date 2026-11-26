#include "FacilityHallEncounter.h"
#include "AuthoredDungeonGenerator.h"
#include "DungeonThemeEncounter.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/CapsuleComponent.h"
#include "Engine/World.h"
#include "NavigationData.h"
#include "NavigationSystem.h"

bool AFacilityHallEncounter::HasObjectiveSlot() const
{
    for(int32 Index:{ObjectiveEliteSlot,MedicalBossSlot,FreightBossSlot,EcologyBossSlot,PowerBossSlot,
        IncinerationBossSlot,StaffLivingBossSlot,FinalBossSlot})
        if(Slots.IsValidIndex(Index)&&!Slots[Index].bDefeated&&!Slots[Index].Monster.IsValid())return true;
    return false;
}

int32 AFacilityHallEncounter::SpawnPriority() const
{
    if(!bConfigured||bStopping||bCleared||!HasAuthority()||!Run.IsValid()||!Run->IsRunActive()
        ||!Generator.IsValid()||Generator->IsPreparationPending()||!Theme.IsValid()||!Theme->HasStarted()
        ||GetWorld()->GetTimeSeconds()<NextSpawnAttemptAt)return INDEX_NONE;
    double Distance=0.;const int32 Area=Theme->PreparationPriority(Distance);
    if(Area!=0&&Area!=1&&!(Area==2&&Theme->IsPlayerOnSpawnApproach()))return INDEX_NONE;
    return Area*2+(HasObjectiveSlot()?0:1);
}

void AFacilityHallEncounter::CacheSpawnNavigationAnchors()
{
    SpawnNavigationAnchors=Room.NavigationAnchors;
    // Older manifests still have real doorway normals. Keep the target inside
    // the room, beyond the telescopic gate and its collision collar.
    if(SpawnNavigationAnchors.IsEmpty())
        for(const auto& Door:Room.Doors)SpawnNavigationAnchors.Add(Door.FloorCenter-Door.OutwardNormal*300.);
    // These ranged positions intentionally defend their own authored galleries.
    // Require a path along that gallery, not through a narrower ground-floor door.
    const FTransform Frame(FRotator(0,Room.Yaw,0),Room.Origin);
    if(Room.Module==TEXT("FacilityReceptionHall"))
        for(double Y:{-1350.,1350.})SpawnNavigationAnchors.Add(Frame.TransformPosition(FVector(-100,Y,450)));
    else if(Room.Module==TEXT("FacilityTransit"))
        for(double Y:{-1425.,1425.})SpawnNavigationAnchors.Add(Frame.TransformPosition(FVector(-2000,Y,420)));
    else if(Room.Module==TEXT("AbandonedTransitStation"))
        for(double Y:{-1200.,-400.,400.,1200.})SpawnNavigationAnchors.Add(Frame.TransformPosition(FVector(2495,Y,480)));
}

bool AFacilityHallEncounter::HasSpawnRoute(const ACharacter* Defaults,const FVector& Floor,const ANavigationData* Data) const
{
    auto* Nav=FNavigationSystem::GetCurrent<UNavigationSystemV1>(GetWorld());
    if(!Nav||!Data||SpawnNavigationAnchors.IsEmpty())return false;
    const float Radius=Defaults->GetCapsuleComponent()->GetScaledCapsuleRadius();
    TArray<FVector,TInlineAllocator<32>> Candidates;
    for(const FVector& Anchor:SpawnNavigationAnchors)
        if(FMath::Abs(Anchor.Z-Floor.Z)<=150.)Candidates.Add(Anchor);
    Candidates.Sort([&Floor](const FVector& A,const FVector& B){return FVector::DistSquared2D(A,Floor)<FVector::DistSquared2D(B,Floor);});
    for(const FVector& Anchor:Candidates)
    {
        if(SpawnPathQueriesRemaining<=0)break;
        FNavLocation End;
        if(!Nav->ProjectPointToNavigation(Anchor,End,FVector(FMath::Max(80.f,Radius),FMath::Max(80.f,Radius),80),Data)
            ||FMath::Abs(End.Location.Z-Anchor.Z)>60.)continue;
        --SpawnPathQueriesRemaining;
        FPathFindingQuery Query(this,*Data,Floor,End.Location);
        Query.SetAllowPartialPaths(false);
        if(Nav->TestPathSync(Query,EPathFindingMode::Regular))return true;
    }
#if WITH_EDITOR
    if(SpawnAuditFailure)SpawnAuditFailure(TEXT("navigation_connectivity"),Floor);
#endif
    return false;
}
