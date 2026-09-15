#pragma once
#include "CoreMinimal.h"
class UDamageType;
class AActor;
namespace CombatFormulaRuntime
{
struct MagicHit
{
    double Chance=0, Bonus=0, Penetration=0, DamageBonus=0;
    // Return the actual damage roll to the owning skill's reward transaction.
    bool* CriticalResult=nullptr;
};
extern thread_local const MagicHit* ActiveMagicHit;
extern thread_local const double* ActivePhysicalPenetration;
bool IsMagic(const UDamageType* Type);
float MonsterDefense(const AActor* Target,bool Magic);
float MonsterCriticalResistance(const AActor* Target);
float MitigateMonster(AActor* Target,float Damage,const UDamageType* Type,AActor* Source);
}
