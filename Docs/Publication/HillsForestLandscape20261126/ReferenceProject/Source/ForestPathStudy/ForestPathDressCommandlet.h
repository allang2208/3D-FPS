#pragma once
#include "Commandlets/Commandlet.h"
#include "ForestPathDressCommandlet.generated.h"

UCLASS()
class UForestPathDressCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
