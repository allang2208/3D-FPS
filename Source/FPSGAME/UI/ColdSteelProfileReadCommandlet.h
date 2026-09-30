#pragma once
#include "Commandlets/Commandlet.h"
#include "ColdSteelProfileReadCommandlet.generated.h"

/** Read and diagnose the existing profile in memory, without creating a game instance or writing saves. */
UCLASS()
class UColdSteelProfileReadCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
