#pragma once
#include "CoreMinimal.h"

// Outgoing monster damage only. Never changes an item, player sheet or defense formula.
namespace MonsterDamageBalance
{
    // Leave small attacks intact; compress large ones continuously without making
    // all strong weapons identical. Ceiling is before the victim's mitigation.
    inline float Limit(float Damage,float Ceiling)
    {
        Damage=FMath::Max(0.f,Damage);
        if(Ceiling<=0.f)return 0.f;
        const float Knee=Ceiling*.6f;
        if(Damage<=Knee)return Damage;
        const float Excess=Damage-Knee,Room=Ceiling-Knee;
        return Knee+Room*Excess/(Room+Excess);
    }
}

struct FFireballCast; struct FIceSpikeCast; struct FIceWallCast; struct FBlizzardCast;
struct FLightningCast; struct FHolyLightCast; struct FFireMagicCast; struct FElectricMagicCast;
struct FElementalArrowCast; struct FMagicArrowRainCast; struct FIlluminationArrowCast;
namespace UnknownDamageBalance
{
    float Tier(int32 Level,float At10,float At20,float At30);
    float Weapon(float Raw,FName Type,bool Gun,bool Automatic,int32 Level,float Interval,int32 Contacts=1);
    float Piercing(float Raw,int32 Level);
    void Tune(int32 Level,FFireballCast& Cast);
    void Tune(int32 Level,FIceSpikeCast& Cast);
    void Tune(int32 Level,FIceWallCast& Cast);
    void Tune(int32 Level,FBlizzardCast& Cast);
    void Tune(int32 Level,FLightningCast& Cast);
    void Tune(int32 Level,FHolyLightCast& Cast);
    void Tune(int32 Level,FFireMagicCast& Cast);
    void Tune(int32 Level,FElectricMagicCast& Cast,bool Lance);
    void Tune(int32 Level,FElementalArrowCast& Cast);
    void Tune(int32 Level,FMagicArrowRainCast& Cast);
    void Tune(int32 Level,FIlluminationArrowCast& Cast);
}
