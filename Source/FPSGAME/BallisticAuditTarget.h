#pragma once
#include "CoreMinimal.h"
#include "GameFramework/Pawn.h"
#include "BallisticAuditTarget.generated.h"
/** Local damage receiver used only by BallisticPresentationAudit. */
UCLASS()
class ABallisticAuditTarget : public APawn
{
    GENERATED_BODY()
public:
    ABallisticAuditTarget();
    virtual float TakeDamage(float Amount,const FDamageEvent&,AController*,AActor*) override;
    float Received=0;
};
