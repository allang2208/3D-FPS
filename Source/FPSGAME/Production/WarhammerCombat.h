#pragma once
#include "../Combat/WeaponDamageTypes.h"

class UColdSteelStatusModel;
class AActor;
struct FColdSteelItem;

namespace WarhammerCombat
{
    constexpr float HeavyStunSeconds=2.f;
    float ShockwaveRadius(const FColdSteelItem& Item,const UColdSteelStatusModel* Profile);
    FWeaponDamageParts Damage(const FWeaponDamageParts& Base,const UColdSteelStatusModel* Profile,
        bool bSprint,bool bHeavy,float HeavyMultiplier,int32 Stage);
    void ApplyHeavyStun(AActor* Target,float Seconds);
}
