#pragma once
#include "Commandlets/Commandlet.h"
#include "RuneSwordAuditCommandlet.generated.h"

UCLASS()
class URuneSwordAuditCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
