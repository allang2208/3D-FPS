#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "ColdSteelEnhancementAuditTarget.generated.h"
/** Spawned only by the isolated enhancement audit. */
UCLASS()
class AColdSteelEnhancementAuditTarget : public APawn
{
    GENERATED_BODY()
public:
    AColdSteelEnhancementAuditTarget();
    virtual float TakeDamage(float Amount,const FDamageEvent&,AController*,AActor*)override;
    float Received=0;
};
