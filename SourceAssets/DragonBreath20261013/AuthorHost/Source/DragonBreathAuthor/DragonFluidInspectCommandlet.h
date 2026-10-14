#pragma once
#include "Commandlets/Commandlet.h"
#include "DragonFluidInspectCommandlet.generated.h"

/** Targeted CPU parameter read for the user's reversed/invisible jet report. */
UCLASS()
class UDragonFluidInspectCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
