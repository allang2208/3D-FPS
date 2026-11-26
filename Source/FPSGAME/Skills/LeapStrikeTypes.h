#pragma once
#include "CoreMinimal.h"
#include "LeapStrikeTypes.generated.h"

struct FLeapStrikeTuning
{
    float DamageBase=1.6f,DamageMax=3.2f;
    float CooldownBase=30.f,CooldownMin=20.f;
    float StaminaBase=45.f,StaminaMax=65.f;
    float RadiusBaseCM=250.f,RadiusMaxCM=400.f;
    float ReachBaseCM=900.f,ReachMaxCM=1500.f;
    int32 MultiKillExperience=20;
};

/** Server-authorized cast snapshot; animation timing remains independent. */
USTRUCT()
struct FLeapStrikeCast
{
    GENERATED_BODY()
    UPROPERTY() float DamageMultiplier=1.6f;
    UPROPERTY() float CooldownSeconds=30.f;
    UPROPERTY() float StaminaCost=45.f;
    UPROPERTY() float RadiusCM=250.f;
    UPROPERTY() float ReachCM=900.f;
};

namespace LeapStrike
{
inline FLeapStrikeCast Evaluate(const FLeapStrikeTuning& T,int32 Level,int32 MaxLevel=20)
{
    const float Alpha=float(FMath::Clamp(Level,1,MaxLevel)-1)/FMath::Max(1,MaxLevel-1);
    FLeapStrikeCast C;
    C.DamageMultiplier=FMath::Lerp(T.DamageBase,T.DamageMax,Alpha);
    C.CooldownSeconds=FMath::Lerp(T.CooldownBase,T.CooldownMin,Alpha);
    C.StaminaCost=FMath::Lerp(T.StaminaBase,T.StaminaMax,Alpha);
    C.RadiusCM=FMath::Lerp(T.RadiusBaseCM,T.RadiusMaxCM,Alpha);
    C.ReachCM=FMath::Lerp(T.ReachBaseCM,T.ReachMaxCM,Alpha);
    return C;
}
}
