#pragma once
#include "Commandlets/Commandlet.h"
#include "ColdSteelIncineratorAuditCommandlet.generated.h"

/** Explicit transaction tests: forced unique audit profile before subsystem initialization. */
UCLASS()
class UColdSteelIncineratorAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
