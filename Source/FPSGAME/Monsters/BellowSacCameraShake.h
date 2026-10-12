#pragma once
#include "Camera/CameraShakeBase.h"
#include "BellowSacCameraShake.generated.h"

UCLASS()
class FPSGAME_API UBellowSacShakePattern : public UCameraShakePattern
{
    GENERATED_BODY()
    float Age = 0.f;
    virtual void GetShakePatternInfoImpl(FCameraShakeInfo& Info) const override;
    virtual void StartShakePatternImpl(const FCameraShakePatternStartParams&) override { Age=0.f; }
    virtual void UpdateShakePatternImpl(const FCameraShakePatternUpdateParams&, FCameraShakePatternUpdateResult&) override;
    virtual bool IsFinishedImpl() const override { return Age>=.22f; }
    virtual void StopShakePatternImpl(const FCameraShakePatternStopParams&) override { Age=.22f; }
};
UCLASS()
class FPSGAME_API UBellowSacCameraShake : public UCameraShakeBase
{
    GENERATED_BODY()
public:
    UBellowSacCameraShake(const FObjectInitializer& Initializer);
};
