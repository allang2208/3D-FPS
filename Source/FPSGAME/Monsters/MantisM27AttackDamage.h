#pragma once
#include "../Skills/EnemyAttackDamage.h"
#include "MantisM27AttackDamage.generated.h"

/** Direct blade contact only; bleeding ticks use UCombatDirectDamage. */
UCLASS()
class FPSGAME_API UMantisM27MeleeDamage : public UEnemyMeleeDamage
{
    GENERATED_BODY()
public:
    static constexpr float BleedChance = .5f;
};

UCLASS()
class FPSGAME_API UMantisM27PounceDamage : public UMantisM27MeleeDamage
{
    GENERATED_BODY()
public:
    static constexpr float CrippleSeconds = 5.f;
};
