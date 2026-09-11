#pragma once
#include "Commandlets/Commandlet.h"
#include "FPSTraversalRulesAuditCommandlet.generated.h"

UCLASS()
class UFPSTraversalRulesAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
