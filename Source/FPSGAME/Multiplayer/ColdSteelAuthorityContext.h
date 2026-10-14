#pragma once
#include "CoreMinimal.h"
class UColdSteelStatusModel;
class APawn;
namespace ColdSteelAuthority
{
    UColdSteelStatusModel* ForPawn(const APawn* Pawn);
    UColdSteelStatusModel* Model(const UObject* Context);
    // Synchronous game-thread scope only. Async work retains its own explicit model.
    struct FScope
    {
        explicit FScope(UColdSteelStatusModel* Model);
        ~FScope();
    private: UColdSteelStatusModel* Previous;
    };
}
