#pragma once

#include "Commandlets/Commandlet.h"
#include "ColdSteelHillsMapCheckCommandlet.generated.h"

UCLASS()
class UColdSteelHillsMapCheckCommandlet : public UCommandlet
{
    GENERATED_BODY()
    virtual int32 Main(const FString& Params) override;
};
