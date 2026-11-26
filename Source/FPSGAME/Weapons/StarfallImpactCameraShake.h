#pragma once
#include "Camera/CameraShakeBase.h"
#include "StarfallImpactCameraShake.generated.h"

UCLASS()
class FPSGAME_API UStarfallImpactShakePattern : public UCameraShakePattern
{
    GENERATED_BODY()
private:
    virtual void GetShakePatternInfoImpl(FCameraShakeInfo& Info) const override;
    virtual void StartShakePatternImpl(const FCameraShakePatternStartParams& Params) override { Age=0.f; }
    virtual void UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params, FCameraShakePatternUpdateResult& Result) override;
    virtual bool IsFinishedImpl() const override { return Age>=.26f; }
    virtual void StopShakePatternImpl(const FCameraShakePatternStopParams& Params) override { Age=.26f; }
    float Age=0.f;
};

UCLASS()
class FPSGAME_API UStarfallImpactCameraShake : public UCameraShakeBase
{
    GENERATED_BODY()
public:
    UStarfallImpactCameraShake(const FObjectInitializer& Initializer);
};
