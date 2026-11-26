#pragma once
#include "CoreMinimal.h"
class APawn;
class AActor;
class UDamageType;
class UColdSteelStatusModel;
namespace UnknownSpell
{
    struct FWeaponSnapshot { float MagicFraction=0,PhysicalPenetration=0,MagicPenetration=0; };
    extern thread_local const FWeaponSnapshot* ActiveWeapon;
    bool IsCaster(const AActor* Actor);
    bool IsTarget(const AActor* Caster,const AActor* Target);
    UColdSteelStatusModel* Model(APawn* Pawn);
    bool Hit(APawn* Caster,AActor* Target,float Amount,float Chance,float Bonus,float DamageBonus,float Penetration,
        TSubclassOf<UDamageType> Type,bool Weak=false);
}
