#pragma once
#include "Commandlets/Commandlet.h"
#include "WoodworkingAuditCommandlet.generated.h"

/** Isolated woodworking transactions and network payloads; no socket or viewport. */
UCLASS()
class UWoodworkingAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
