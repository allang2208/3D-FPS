#pragma once
#include "CoreMinimal.h"
namespace HolyLightTargets
{
    bool IsFriendly(const AActor* Target);
    bool IsAlive(AActor* Target);
    bool IsZombie(const AActor* Target);
    float Heal(AActor* Target,float Amount);
    float MaximumHealth(AActor* Target);
}
