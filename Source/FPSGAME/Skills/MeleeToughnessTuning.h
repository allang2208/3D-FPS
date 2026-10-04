#pragma once
#include "CoreMinimal.h"
#include "SwordUppercutTuning.h"

namespace MeleeToughness
{
    inline constexpr float Heavy=400.f;
    inline constexpr float Whirlwind=200.f;
    inline constexpr float Uppercut=300.f;

    // Both local and server-reconstructed hits carry these existing action bits.
    // Secondary waves and quick melee retain their own damage-derived poise.
    inline float FixedBaseFor(uint8 AttackMeta)
    {
        if(AttackMeta&(0x40|0x80))return -1.f;
        if(AttackMeta==SwordUppercut::AttackMeta)return Uppercut;
        if(AttackMeta&0x20)return Whirlwind;
        if(AttackMeta&0x10)return Heavy;
        return -1.f;
    }
}
