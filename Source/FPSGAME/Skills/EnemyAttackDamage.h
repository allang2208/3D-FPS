#pragma once
#include "CoreMinimal.h"
#include "GameFramework/DamageType.h"
#include "EnemyAttackDamage.generated.h"

// Direct enemy attacks declare their delivery; damage-over-time remains separate.
UCLASS()
class FPSGAME_API UEnemyMeleeDamage : public UDamageType { GENERATED_BODY() };
UCLASS()
class FPSGAME_API UEnemyRangedDamage : public UDamageType { GENERATED_BODY() };
