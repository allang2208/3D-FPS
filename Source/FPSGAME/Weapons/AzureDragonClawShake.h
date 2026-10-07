#pragma once
#include "Camera/CameraShakeBase.h"
#include "AzureDragonClawShake.generated.h"

/** Short rotational punch when an Azure Dragon claw rakes through its contact point. */
UCLASS()
class FPSGAME_API UAzureDragonClawShakePattern : public UCameraShakePattern
{
    GENERATED_BODY()
private:
    virtual void GetShakePatternInfoImpl(FCameraShakeInfo& OutInfo) const override;
    virtual void StartShakePatternImpl(const FCameraShakePatternStartParams& Params) override { Age=0.f; }
    virtual void UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params, FCameraShakePatternUpdateResult& OutResult) override;
    virtual bool IsFinishedImpl() const override { return Age>=.2f; }
    virtual void StopShakePatternImpl(const FCameraShakePatternStopParams& Params) override { Age=.2f; }
    float Age=0.f;
};

UCLASS()
class FPSGAME_API UAzureDragonClawShake : public UCameraShakeBase
{
    GENERATED_BODY()
public:
    UAzureDragonClawShake(const FObjectInitializer& ObjectInitializer);
};
