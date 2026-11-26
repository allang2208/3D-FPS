#pragma once

#include "UObject/NameTypes.h"
#include "VillageShopTorches.h"

class AActor;

namespace HillsVillageShopSite
{
    struct FShop
    {
        FName Ruin, Restored, Solid, Window, Service;
        VillageShopTorches::EShop Lighting;
    };

    extern const FShop Bakery;
    extern const FShop Gunshop;

    void Apply(AActor& Site, const FShop& Shop, bool bRepaired);
    bool IsOccupied(const AActor& Site, const FShop& Shop);
}
