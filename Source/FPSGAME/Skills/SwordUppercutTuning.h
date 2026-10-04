#pragma once
#include "CoreMinimal.h"

namespace SwordUppercut
{
    // Apply after the complete heavy modifier, including the additive ballast bonus.
    inline constexpr float HeavyDamageScale=.7f;
    inline constexpr uint8 AttackMeta=0x14; // Heavy formula family, independent uppercut level.
}
