#include "MonsterTargeting.h"
#include "../Movement/HorseRiderComponent.h"
#include "../Movement/StableRidingHorse.h"
#include "../FPSGAMECharacter.h"
#include "../Characters/VillageArtisanVitalsComponent.h"
#include "FPSCombatHealthComponent.h"
#include "Engine/OverlapResult.h"
#include "Engine/World.h"
#include "GameFramework/Controller.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"

namespace
{
const UVillageArtisanVitalsComponent* ArtisanVitals(const APawn* Pawn)
{
    if (!IsValid(Pawn) || !Pawn->ActorHasTag(TEXT("NPC"))) return nullptr;
    return Pawn->FindComponentByClass<UVillageArtisanVitalsComponent>();
}
}

AActor* MonsterTargeting::DamageRecipient(AActor* HitActor)
{
    if(const auto* Horse=Cast<AStableRidingHorse>(HitActor);Horse&&IsValid(Horse->GetRider()))
        return Horse->GetRider();
    return HitActor;
}

const APawn* MonsterTargeting::ContactBody(const APawn* Target)
{
    if(const auto* Mount=UHorseRiderComponent::MountOf(Target))return Mount;
    return Target;
}

bool MonsterTargeting::IsActiveArtisan(const APawn* Pawn)
{
    const auto* Vitals = ArtisanVitals(Pawn);
    return Vitals && !Vitals->IsDowned();
}

bool MonsterTargeting::IsDownedArtisan(const APawn* Pawn)
{
    const auto* Vitals = ArtisanVitals(Pawn);
    return Vitals && Vitals->IsDowned();
}

bool MonsterTargeting::IsOpponentPawn(const APawn* Pawn)
{
    return IsValid(Pawn) && (Pawn->IsPlayerControlled() || IsActiveArtisan(Pawn));
}

bool MonsterTargeting::IsLivingOpponent(const APawn* Pawn)
{
    if (!IsValid(Pawn) || !Pawn->HasActorBegunPlay()) return false;
    if (!Pawn->IsPlayerControlled()) return IsActiveArtisan(Pawn);
    if (!Pawn->GetController() || Pawn->GetController()->GetPawn() != Pawn) return false;
    const auto* Health = Pawn->FindComponentByClass<UFPSCombatHealthComponent>();
    return !Health || !Health->IsDead();
}

void MonsterTargeting::GatherAreaOpponents(UWorld* World, const FVector& Origin, float Radius, TArray<APawn*>& Out)
{
    // Keep player contacts even when their capsule temporarily uses a different
    // collision profile. Artisans are ordinary Pawn query bodies in the village.
    Out.Reset();
    for (auto It = World->GetPlayerControllerIterator(); It; ++It)
        if (const auto* PC = It->Get())
            if (APawn* Player = PC->GetPawn()) Out.Add(Player);
    TArray<FOverlapResult> Hits;
    World->OverlapMultiByObjectType(Hits, Origin, FQuat::Identity, FCollisionObjectQueryParams(ECC_Pawn),
        FCollisionShape::MakeSphere(FMath::Max(1.f,Radius)));
    for (const auto& Hit : Hits)
        if (auto* Pawn = Cast<APawn>(Hit.GetActor()); IsActiveArtisan(Pawn)) Out.AddUnique(Pawn);
}
