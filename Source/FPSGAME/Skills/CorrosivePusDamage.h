#pragma once
#include "CoreMinimal.h"
#include "GameFramework/DamageType.h"
#include "CorrosivePusDamage.generated.h"

/** Ground corrosion is magic damage, not a direct melee/ranged attack or a poison stack. */
UCLASS()
class FPSGAME_API UCorrosivePusDamage : public UDamageType { GENERATED_BODY() };
