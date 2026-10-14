#include "RangedAttackQuery.h"
#include "../FPSGAMECharacter.h"
#include "../Monsters/MonsterCombatComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"
#include "GenericTeamAgentInterface.h"

namespace
{
const AActor* AttachedUnit(const AActor* Actor)
{
    // A player-owned ice wall, door or building remains solid. Only units and
    // their physically attached equipment share the unit's collision policy.
    for (const AActor* Part = Actor; IsValid(Part); Part = Part->GetAttachParentActor())
    {
        if (Part->ActorHasTag(TEXT("DefenseStructure"))) return nullptr;
        if (Part->IsA<APawn>() || Part->FindComponentByClass<UMonsterCombatComponent>()) return Part;
    }
    return nullptr;
}

FGenericTeamId Team(const AActor* Unit)
{
    if (const auto* Pawn = Cast<APawn>(Unit))
        if (const auto* Agent = Cast<IGenericTeamAgentInterface>(Pawn->GetController()))
            if (Agent->GetGenericTeamId() != FGenericTeamId::NoTeam) return Agent->GetGenericTeamId();
    if (const auto* Agent = Cast<IGenericTeamAgentInterface>(Unit)) return Agent->GetGenericTeamId();
    return FGenericTeamId::NoTeam;
}

int32 Side(const AActor* Unit)
{
    const auto* Pawn = Cast<APawn>(Unit);
    if (Unit->IsA<AFPSGAMECharacter>() || (Pawn && Pawn->IsPlayerControlled())
        || Unit->ActorHasTag(TEXT("Player")) || Unit->ActorHasTag(TEXT("Friendly"))
        || Unit->ActorHasTag(TEXT("Companion")) || Unit->ActorHasTag(TEXT("Summoned"))) return 1;
    if (Unit->FindComponentByClass<UMonsterCombatComponent>() || Unit->ActorHasTag(TEXT("Enemy"))) return 2;
    return 0;
}

bool SkipFriendly(const AActor* Source, const FHitResult& Hit, FCollisionQueryParams& Query)
{
    if (!RangedAttackQuery::IsFriendlyUnit(Source, Hit.GetActor())) return false;
    // Ignoring the hit actor removes all its body shapes. Attached child actors
    // are classified when encountered; no world-wide actor scans are needed.
    Query.AddIgnoredActor(Hit.GetActor());
    return true;
}
}

bool RangedAttackQuery::IsFriendlyUnit(const AActor* Source, const AActor* Candidate)
{
    const AActor* From = AttachedUnit(Source);
    const AActor* To = AttachedUnit(Candidate);
    if (!From || !To) return false;
    if (From == To) return true;
    const FGenericTeamId SourceTeam = Team(From), TargetTeam = Team(To);
    if (SourceTeam != FGenericTeamId::NoTeam && TargetTeam != FGenericTeamId::NoTeam)
        return FGenericTeamId::GetAttitude(SourceTeam, TargetTeam) == ETeamAttitude::Friendly;
    const int32 SourceSide = Side(From);
    return SourceSide != 0 && SourceSide == Side(To);
}

bool RangedAttackQuery::LineTraceSingle(UWorld* World, const AActor* Source, FHitResult& Hit,
    const FVector& Start, const FVector& End, ECollisionChannel Channel, const FCollisionQueryParams& Query)
{
    FCollisionQueryParams Filter = Query;
    while (World->LineTraceSingleByChannel(Hit, Start, End, Channel, Filter))
        if (!SkipFriendly(Source, Hit, Filter)) return true;
    return false;
}

bool RangedAttackQuery::LineTraceTest(UWorld* World, const AActor* Source,
    const FVector& Start, const FVector& End, ECollisionChannel Channel, const FCollisionQueryParams& Query)
{
    FHitResult Hit;
    return LineTraceSingle(World, Source, Hit, Start, End, Channel, Query);
}

bool RangedAttackQuery::SweepSingle(UWorld* World, const AActor* Source, FHitResult& Hit,
    const FVector& Start, const FVector& End, const FQuat& Rotation, ECollisionChannel Channel,
    const FCollisionShape& Shape, const FCollisionQueryParams& Query)
{
    FCollisionQueryParams Filter = Query;
    while (World->SweepSingleByChannel(Hit, Start, End, Rotation, Channel, Shape, Filter))
        if (!SkipFriendly(Source, Hit, Filter)) return true;
    return false;
}

bool RangedAttackQuery::SweepMulti(UWorld* World, const AActor* Source, TArray<FHitResult>& Hits,
    const FVector& Start, const FVector& End, const FQuat& Rotation, ECollisionChannel Channel,
    const FCollisionShape& Shape, const FCollisionQueryParams& Query)
{
    FCollisionQueryParams Filter = Query;
    // Channel multi-sweeps stop at the first blocker. Filtering that result
    // alone would lose the enemy/wall behind an allied blocking capsule.
    for (;;)
    {
        const bool Blocked = World->SweepMultiByChannel(Hits, Start, End, Rotation, Channel, Shape, Filter);
        bool Retry = false;
        for (const FHitResult& Hit : Hits)
            if (SkipFriendly(Source, Hit, Filter)) Retry = true;
        if (!Retry) return Blocked;
    }
}

bool RangedAttackQuery::SweepObjects(UWorld* World, const AActor* Source, TArray<FHitResult>& Hits,
    const FVector& Start, const FVector& End, const FQuat& Rotation, const FCollisionObjectQueryParams& Objects,
    const FCollisionShape& Shape, const FCollisionQueryParams& Query)
{
    // Object multi-queries already gather the full segment, unlike channel
    // multi-sweeps; remove allies before callers choose the earliest contact.
    World->SweepMultiByObjectType(Hits, Start, End, Rotation, Objects, Shape, Query);
    Hits.RemoveAll([Source](const FHitResult& Hit) { return IsFriendlyUnit(Source, Hit.GetActor()); });
    return !Hits.IsEmpty();
}
