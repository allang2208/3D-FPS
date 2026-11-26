#pragma once
#include "HorseRosterTypes.h"

struct FStableHorseOffer
{
    FStableMountRecord Horse;
    int32 Price=0;
};

namespace StableHorseMarket
{
    constexpr int32 DailyCount=4;
    bool IsSeller(const AActor* Actor);
    TArray<FStableHorseOffer> Stock(FGuid ProfileId,int32 Day);
}
