#pragma once
#include "Commandlets/Commandlet.h"
#include "DungeonMaterialUsageRepairCommandlet.generated.h"

/** Persist the exact material usage corrections captured in a dungeon log. */
UCLASS()
class UDungeonMaterialUsageRepairCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
