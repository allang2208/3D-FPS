#pragma once
#include "CoreMinimal.h"
class AActor;

/** Receipt of accepted damage, separate from stagger/animation presentation. */
struct FMonsterHitFeedback
{
    TWeakObjectPtr<AActor> Target;
    FText Name;
    float Damage = 0.f;
    float Health = 0.f;
    float MaxHealth = 0.f;
    float Opacity = 0.f;
    bool bKilled = false;
};
