#pragma once

#include "CoreMinimal.h"

class ATemperateHillsWorld;
struct FTemperatePlacement;

namespace TemperateIronOutcrops
{
    struct FSearch
    {
        TArray<FVector2D> Sites;
        FVector2D From=FVector2D::ZeroVector;
        int32 Seed=0;
        double Edge=0.;
        int32 Next=0;
    };
    void Gather(const ATemperateHillsWorld& Hills,const FBox& Bounds,TArray<FTemperatePlacement>& Out);
    inline bool IsVeinRock(uint64 Id) { return (Id >> 48) == 0x4956; }
}
