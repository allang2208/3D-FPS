#pragma once
#include "Commandlets/Commandlet.h"
#include "LargeLambMealAuditCommandlet.generated.h"

/** Explicit opt-in production-path checks in a separate UserDir and unique profile. */
UCLASS()
class ULargeLambMealAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
