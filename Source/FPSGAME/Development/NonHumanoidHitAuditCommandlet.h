#pragma once
#include "Commandlets/Commandlet.h"
#include "NonHumanoidHitAuditCommandlet.generated.h"

/** Read-only isolated surface/query/damage audit for the remaining F6 monsters. */
UCLASS()
class UNonHumanoidHitAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
