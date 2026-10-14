#pragma once
#include "../Skills/EnemyAttackDamage.h"
#include "RootCrownMineDamage.generated.h"

/** The mine keeps ranged damage mitigation; only an accepted hit applies cripple. */
UCLASS()
class FPSGAME_API URootCrownMineDamage : public UEnemyRangedDamage
{
    GENERATED_BODY()
public:
    static constexpr float CrippleSeconds=5.f;
};
