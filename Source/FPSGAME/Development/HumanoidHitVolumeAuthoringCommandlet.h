#pragma once
#include "Commandlets/Commandlet.h"
#include "HumanoidHitVolumeAuthoringCommandlet.generated.h"

/** Builds and saves per-model query geometry without starting gameplay. */
UCLASS()
class UHumanoidHitVolumeAuthoringCommandlet : public UCommandlet
{
    GENERATED_BODY()
public:
    virtual int32 Main(const FString& Params) override;
};
