#pragma once
#include "Commandlets/Commandlet.h"
#include "FacilitySpawnRecheckCommandlet.generated.h"

/** Offline production assembly/navigation/placement audit. Never calls BeginPlay or saves assets. */
UCLASS()
class UFacilitySpawnRecheckCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
