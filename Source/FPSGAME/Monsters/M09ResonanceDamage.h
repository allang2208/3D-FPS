#pragma once
#include "../Combat/CombatStatusFormula.h"
#include "M09ResonanceDamage.generated.h"

/** M09 magic pulse; SAN is charged once after the player accepts this hit. */
UCLASS()
class FPSGAME_API UM09ResonanceDamage : public UStatusMagicDamage
{
 GENERATED_BODY()
public:
 static constexpr float SanityLoss=2.f;
};
