#pragma once
#include "HandBrainMonster.h"
#include "M10HowlDamage.generated.h"

/** Inherits the existing ranged magic defense/dodge contract, with its own on-hit effects. */
UCLASS()
class FPSGAME_API UM10HowlDamage : public UHandBrainMagicDamage
{
    GENERATED_BODY()
public:
    static constexpr float SanityLoss=5.f;
    static constexpr float CrippleSeconds=5.f;
};
