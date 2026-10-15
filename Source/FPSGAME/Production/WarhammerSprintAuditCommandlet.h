#pragma once
#include "Commandlets/Commandlet.h"
#include "WarhammerSprintAuditCommandlet.generated.h"

/** Explicit diagnosis of hammer readiness with an isolated temporary profile. */
UCLASS()
class UWarhammerSprintAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
