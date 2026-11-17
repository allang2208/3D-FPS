#pragma once

#include "Commandlets/Commandlet.h"
#include "ColdSteelDungeonFogCheckCommandlet.generated.h"

UCLASS()
class UColdSteelDungeonFogCheckCommandlet : public UCommandlet
{
    GENERATED_BODY()
    virtual int32 Main(const FString& Params) override;
    int32 CheckNetworkLifecycle();
};
