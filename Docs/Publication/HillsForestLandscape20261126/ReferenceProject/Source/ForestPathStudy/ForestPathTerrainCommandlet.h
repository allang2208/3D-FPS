#pragma once
#include "Commandlets/Commandlet.h"
#include "ForestPathTerrainCommandlet.generated.h"

UCLASS()
class UForestPathTerrainCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
