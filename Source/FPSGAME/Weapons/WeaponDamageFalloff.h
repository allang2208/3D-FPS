#pragma once
#include "CoreMinimal.h"

namespace WeaponDamageFalloff
{
// Effective range is full damage; twice that range reaches the 10% floor.
inline float Multiplier(float DistanceCM,float EffectiveRangeCM)
{
    if(EffectiveRangeCM<=0.f)return 1.f;
    const float Progress=FMath::Clamp((DistanceCM-EffectiveRangeCM)/EffectiveRangeCM,0.f,1.f);
    return 1.f-.9f*Progress;
}
}
