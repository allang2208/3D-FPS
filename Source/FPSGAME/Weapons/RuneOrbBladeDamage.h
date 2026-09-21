// Magic damage marker for the rune sword's orbiting blades. Registered with
// CombatFormulaRuntime::IsMagic so it flows through the same magic pipeline
// (mdef, magic vulnerability) as fireball/ice/lightning.
#pragma once
#include "CoreMinimal.h"
#include "GameFramework/DamageType.h"
#include "RuneOrbBladeDamage.generated.h"

UCLASS()
class FPSGAME_API URuneOrbBladeDamage : public UDamageType
{
    GENERATED_BODY()
};
