#pragma once
#include "Commandlets/Commandlet.h"
#include "BackpackCapacityAuditCommandlet.generated.h"

/** Isolated backpack transactions plus read-only inspection of existing saves. */
UCLASS()
class UBackpackCapacityAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
