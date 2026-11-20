#pragma once
#include "CoreMinimal.h"

class APawn;
class UWorld;

namespace MonsterTargeting
{
    bool IsActiveArtisan(const APawn* Pawn);
    bool IsDownedArtisan(const APawn* Pawn);
    bool IsOpponentPawn(const APawn* Pawn);
    bool IsLivingOpponent(const APawn* Pawn);
    void GatherAreaOpponents(UWorld* World, const FVector& Origin, float Radius, TArray<APawn*>& Out);
}
