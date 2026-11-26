#pragma once

#include "../FPSGAMECharacter.h"
#include "../Combat/WeaponDamageTypes.h"
#include "../Monsters/MonsterCombatComponent.h"

namespace ColdSteelSpellFeedback
{
// Call after the spell's damage/status handling and before its training counters.
// Query death before the player cast, matching the original notification sequence.
inline void NotifyHit(AActor* Shooter,AActor* Target,float Applied,
    const UMonsterCombatComponent& Combat,bool bCritical,bool bMagicDamage=true)
{
    FWeaponDamageResult HitResult;
    HitResult.bResolved=true;
    HitResult.Applied=FWeaponDamageParts::FromChannels(Applied,bMagicDamage?Applied:0.f);
    HitResult.bCritical=bCritical;
    HitResult.bKilled=Combat.IsDead();
    if(auto* Player=::Cast<AFPSGAMECharacter>(Shooter))
        Player->NotifyConfirmedWeaponHit(Target,Applied,&HitResult);
}
}
