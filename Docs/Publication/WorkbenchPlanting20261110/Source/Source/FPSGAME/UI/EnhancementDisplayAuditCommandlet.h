#pragma once
#include "Commandlets/Commandlet.h"
#include "EnhancementDisplayAuditCommandlet.generated.h"
/** Opt-in structural review, not final visual certification. */
UCLASS()
class UEnhancementDisplayAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
