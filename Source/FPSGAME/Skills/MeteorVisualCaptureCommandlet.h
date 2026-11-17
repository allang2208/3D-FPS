#pragma once
#include "Commandlets/Commandlet.h"
#include "MeteorVisualCaptureCommandlet.generated.h"

/** Opt-in offscreen capture of the production meteor actor, without a player profile. */
UCLASS()
class UMeteorVisualCaptureCommandlet : public UCommandlet
{
    GENERATED_BODY()
    virtual int32 Main(const FString& Params) override;
};
