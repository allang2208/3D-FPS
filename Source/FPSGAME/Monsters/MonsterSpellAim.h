#pragma once

#include "CoreMinimal.h"

class APawn;

namespace MonsterSpellAim
{
    bool ClearSegment(const APawn* Caster, const APawn* Target, const FVector& Start, const FVector& End);

    // Sample at release. Use the direct aim if the intercept is out of range or behind cover.
    FVector LaunchAim(const APawn* Caster, const APawn* Target, const FVector& Origin,
        const FVector& TargetPoint, float Speed, float Range, float DownwardGravity = 0.f);
}
