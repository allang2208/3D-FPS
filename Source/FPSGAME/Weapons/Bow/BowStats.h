#pragma once
#include "../GunsmithSystem.h"
#include "../WeaponDamagePanel.h"
class UColdSteelStatusModel;
namespace ColdSteelBow
{
inline constexpr float MinimumFireDrawFraction = .5f;
// Below half draw no arrow can launch. Half draw deals 50%, full draw 150%.
float DrawDamageMultiplier(float DrawFraction);
struct FStats
{
    // Full-draw panel; the shot snapshot remains the uncharged weapon baseline.
    FWeaponDamageParts Damage;
    double Draw=1.4,Nock=.68,Hold=2.2,Speed=98,Stamina=3,Sway=.9,Spread=.035,ADS=.24;
};
FStats Evaluate(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile,const FGunsmithParts* Override=nullptr);
}
