#pragma once
#include "Commandlets/Commandlet.h"
#include "CoreFormulaAuditCommandlet.generated.h"
UCLASS()
class UCoreFormulaAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
