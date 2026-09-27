#pragma once

#include "CoreMinimal.h"

class AActor;
class UMonsterCombatComponent;

namespace MonsterDamageAlert
{
/**
 * A direct silent shot defers only its victim's group alerts until TakeDamage
 * has finished. OnTakeAnyDamage can run before the monster enters its death
 * state, so checking IsDead inside that delegate would still alarm on a kill.
 */
class FScopedSilentShot
{
public:
    explicit FScopedSilentShot(AActor* Victim);
    ~FScopedSilentShot();
    FScopedSilentShot(const FScopedSilentShot&) = delete;
    FScopedSilentShot& operator=(const FScopedSilentShot&) = delete;

    /** True means queued for this shot; the caller must not broadcast yet. */
    static bool DeferGroupAlert(AActor* Victim, TFunction<void()> Alert);

private:
    static thread_local FScopedSilentShot* Active;
    FScopedSilentShot* Previous = nullptr;
    TWeakObjectPtr<AActor> Target;
    TWeakObjectPtr<UMonsterCombatComponent> Combat;
    bool bWasAlive = false;
    TArray<TFunction<void()>, TInlineAllocator<1>> DeferredAlerts;
};
}
