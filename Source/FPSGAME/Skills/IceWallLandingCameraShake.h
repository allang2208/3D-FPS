#pragma once
#include "Camera/CameraShakeBase.h"
#include "IceWallLandingCameraShake.generated.h"

/** Short ground impact feedback; camera offsets never change the aim controller. */
UCLASS()
class FPSGAME_API UIceWallLandingShakePattern : public UCameraShakePattern
{
    GENERATED_BODY()
private:
    virtual void GetShakePatternInfoImpl(FCameraShakeInfo& OutInfo) const override;
    virtual void StartShakePatternImpl(const FCameraShakePatternStartParams& Params) override { Age=0.f; }
    virtual void UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params,FCameraShakePatternUpdateResult& OutResult) override;
    virtual bool IsFinishedImpl() const override { return Age>=.23f; }
    virtual void StopShakePatternImpl(const FCameraShakePatternStopParams& Params) override { Age=.23f; }
    float Age=0.f;
};

UCLASS()
class FPSGAME_API UIceWallLandingCameraShake : public UCameraShakeBase
{
    GENERATED_BODY()
public:
    UIceWallLandingCameraShake(const FObjectInitializer& ObjectInitializer);
};
