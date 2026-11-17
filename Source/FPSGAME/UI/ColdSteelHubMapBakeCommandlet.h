#pragma once

#include "Commandlets/Commandlet.h"
#include "ColdSteelHubMapBakeCommandlet.generated.h"

/** Bakes the saved hub's M-map texture without starting gameplay or saving the source level. */
UCLASS()
class UColdSteelHubMapBakeCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
