#include "MonsterDamageAlert.h"
#include "MonsterCombatComponent.h"
#include "GameFramework/Actor.h"

namespace MonsterDamageAlert
{
thread_local FScopedSilentShot* FScopedSilentShot::Active = nullptr;

FScopedSilentShot::FScopedSilentShot(AActor* Victim)
    : Previous(Active), Target(Victim)
{
    Combat = IsValid(Victim) ? Victim->FindComponentByClass<UMonsterCombatComponent>() : nullptr;
    bWasAlive = Combat.IsValid() && !Combat->IsDead();
    Active = this;
}

FScopedSilentShot::~FScopedSilentShot()
{
    Active = Previous;
    // Resolve actual post-defense, post-critical death, never a prediction
    // based on raw arrow damage. Destroyed victims cannot raise an alarm.
    const bool bKilled = bWasAlive && (!Target.IsValid() || !Combat.IsValid() || Combat->IsDead());
    if (!bKilled)
        for (auto& Alert : DeferredAlerts) Alert();
}

bool FScopedSilentShot::DeferGroupAlert(AActor* Victim, TFunction<void()> Alert)
{
    if (!Active || !Active->bWasAlive || Active->Target.Get() != Victim) return false;
    Active->DeferredAlerts.Add(MoveTemp(Alert));
    return true;
}
}
