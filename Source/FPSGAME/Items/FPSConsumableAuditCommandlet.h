#pragma once
#include "Commandlets/Commandlet.h"
#include "FPSConsumableAuditCommandlet.generated.h"

/** Explicit opt-in, isolated held-weapon state checks; no player profile or saves. */
UCLASS()
class UFPSConsumableAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
