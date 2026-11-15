#pragma once
#include "Commandlets/Commandlet.h"
#include "TemperateWetForestCheckCommandlet.generated.h"

/** Opt-in offline numeric and SM6 checks; never starts gameplay or writes saves. */
UCLASS()
class UTemperateWetForestCheckCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
