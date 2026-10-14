#pragma once
#include "Commandlets/Commandlet.h"
#include "ColdSteelAcquisitionAuditCommandlet.generated.h"

/** Explicit, isolated feed tests; no map, viewport, socket or production save. */
UCLASS()
class UColdSteelAcquisitionAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
