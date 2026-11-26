#pragma once

#include "Commandlets/Commandlet.h"
#include "BakeTemperateHillsLayoutCommandlet.generated.h"

UCLASS()
class UBakeTemperateHillsLayoutCommandlet : public UCommandlet
{
    GENERATED_BODY()
    virtual int32 Main(const FString& Params) override;
};
