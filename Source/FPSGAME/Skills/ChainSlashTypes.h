#pragma once
#include "CoreMinimal.h"

struct FChainSlashTuning
{
    float DamageBase=.4f,DamageMax=1.2f;
    float CooldownBase=25.f,CooldownMin=15.f;
    float StaminaBase=40.f,StaminaMax=60.f;
    int32 MultiKillExperience=20;
};

struct FChainSlashCast
{
    float DamageMultiplier=.4f,CooldownSeconds=25.f,StaminaCost=40.f;
};

namespace ChainSlash
{
inline FChainSlashCast Evaluate(const FChainSlashTuning& T,int32 Level,int32 MaxLevel=20)
{
    const float Alpha=float(FMath::Clamp(Level,1,MaxLevel)-1)/FMath::Max(1,MaxLevel-1);
    return {FMath::Lerp(T.DamageBase,T.DamageMax,Alpha),
        FMath::Lerp(T.CooldownBase,T.CooldownMin,Alpha),FMath::Lerp(T.StaminaBase,T.StaminaMax,Alpha)};
}
}
