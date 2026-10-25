#pragma once
#include "Commandlets/Commandlet.h"
#include "WarhammerNetworkAuditCommandlet.generated.h"

/** Isolated runtime authority/receipt regression, with no live connection or user save. */
UCLASS()
class UWarhammerNetworkAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
    int32 AuditSprint(const FString& Params);
};
