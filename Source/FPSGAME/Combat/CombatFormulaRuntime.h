#pragma once
#include "CoreMinimal.h"
#include "WeaponDamageTypes.h"
class UDamageType;
class AActor;
namespace CombatFormulaRuntime
{
struct MagicHit
{
    double Chance=0, Bonus=0, Penetration=0, DamageBonus=0;
    // Return the actual damage roll to the owning skill's reward transaction.
    bool* CriticalResult=nullptr;
    // Set separately for each victim, from that projectile's actual direct hit.
    // Splash victims keep false and retain their independent random critical roll.
    bool bWeakpoint=false;
};
extern thread_local const MagicHit* ActiveMagicHit;
struct WeaponHit
{
    AActor* Target=nullptr;
    FWeaponDamageParts Incoming,Mitigated;
    double PhysicalPenetration=0,MagicPenetration=0;
    bool bResolved=false;
};
extern thread_local WeaponHit* ActiveWeaponHit;
extern thread_local const double* ActivePhysicalPenetration;
bool IsMagic(const UDamageType* Type);
float MonsterDefense(const AActor* Target,bool Magic);
float MonsterCriticalResistance(const AActor* Target);
float MitigateMonster(AActor* Target,float Damage,const UDamageType* Type,AActor* Source);
}
