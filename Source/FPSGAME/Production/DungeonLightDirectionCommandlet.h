#pragma once
#include "Commandlets/Commandlet.h"
#include "DungeonLightDirectionCommandlet.generated.h"

/** Isolated direct-light comparison of native spot spawning and the final world-pose fix. */
UCLASS()
class UDungeonLightDirectionCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
