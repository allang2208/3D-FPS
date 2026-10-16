#pragma once
#include "Commandlets/Commandlet.h"
#include "AlchemyManualFlowAuditCommandlet.generated.h"

/** Opt-in, offscreen reader flow diagnosis with a separate audit profile. */
UCLASS()
class UAlchemyManualFlowAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
