#pragma once

class AActor;

namespace VillageShopTorches
{
    enum class EShop { Blacksmith, Carpenter, Herbalist, Tavern, Bakery };
    void Apply(AActor& Host, EShop Shop, bool bRepaired);
}
