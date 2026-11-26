#pragma once
#include "Commandlets/Commandlet.h"
#include "DragonBreathReadinessAuditCommandlet.generated.h"

/** Explicit, headless reproduction using a unique disposable profile. */
UCLASS()
class UDragonBreathReadinessAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
