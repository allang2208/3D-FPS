#pragma once
#include "Commandlets/Commandlet.h"
#include "FoodSpoilageAuditCommandlet.generated.h"

/** Explicit opt-in regression suite, restricted to a unique profile under the food audit UserDir. */
UCLASS()
class UFoodSpoilageAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
