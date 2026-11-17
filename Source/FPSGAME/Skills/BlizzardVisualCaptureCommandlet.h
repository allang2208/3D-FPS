#pragma once
#include "Commandlets/Commandlet.h"
#include "BlizzardVisualCaptureCommandlet.generated.h"

/** Explicitly requested offscreen recording of the production Blizzard actor. */
UCLASS()
class UBlizzardVisualCaptureCommandlet : public UCommandlet
{
    GENERATED_BODY()
    virtual int32 Main(const FString& Params) override;
};
