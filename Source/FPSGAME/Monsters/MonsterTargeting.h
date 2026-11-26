#pragma once
#include "CoreMinimal.h"

class APawn;
class UWorld;

namespace MonsterTargeting
{
    // Geometry and combat identity differ for a rider. Preserve non-pawn blockers.
    AActor* DamageRecipient(AActor* HitActor);
    const APawn* ContactBody(const APawn* Target);
    bool IsActiveArtisan(const APawn* Pawn);
    bool IsDownedArtisan(const APawn* Pawn);
    bool IsOpponentPawn(const APawn* Pawn);
    bool IsLivingOpponent(const APawn* Pawn);
    void GatherAreaOpponents(UWorld* World, const FVector& Origin, float Radius, TArray<APawn*>& Out);
}
