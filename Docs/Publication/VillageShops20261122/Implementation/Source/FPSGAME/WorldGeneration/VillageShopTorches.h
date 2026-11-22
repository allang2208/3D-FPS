#pragma once

class AActor;
class ABronzeTorch;

namespace VillageShopTorches
{
    // Direct specular response of a village flame or lantern; diffuse light uses its authored lumens.
    inline constexpr float FixtureSpecular = .18f;
    enum class EShop { Blacksmith, Carpenter, Herbalist, Tavern, Bakery, Gunshop };
    void ConfigureWallTorch(ABronzeTorch& Torch,float Lumens,float Radius);
    void Apply(AActor& Host, EShop Shop, bool bRepaired);
}
