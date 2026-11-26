#pragma once
#include "Commandlets/Commandlet.h"
#include "ColdSteelPlantingAuditCommandlet.generated.h"

/** Isolated profile/transaction fixtures. No map, viewport, PIE or game process. */
UCLASS()
class UColdSteelPlantingAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
    int32 RunNetworkAudit(const FString& Params);
};
