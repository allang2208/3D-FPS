#pragma once
#include "CoreMinimal.h"
#include "IceSpikeDamage.h"
#include "AbsoluteZeroDamage.generated.h"

/** Ultimate Ice Nova primary wave: inherits ice-magic chain without fire hooks. */
UCLASS()
class FPSGAME_API UAbsoluteZeroDamage : public UIceSpikeDamage
{
    GENERATED_BODY()
};

/** Physical shatter & IceWall shrapnel burst: consumes target physical defense and Frozen x1.5 multiplier. */
UCLASS()
class FPSGAME_API UAbsoluteZeroShatterDamage : public UDamageType
{
    GENERATED_BODY()
};
