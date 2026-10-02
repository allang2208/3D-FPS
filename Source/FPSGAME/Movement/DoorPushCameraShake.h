#pragma once

#include "Camera/CameraShakeBase.h"
#include "DoorPushCameraShake.generated.h"

/** A brief contact impulse in camera space; it never modifies ControlRotation or FOV. */
UCLASS()
class FPSGAME_API UDoorPushContactShakePattern : public UCameraShakePattern
{
    GENERATED_BODY()
private:
    static constexpr float DurationSeconds=.18f;
    virtual void GetShakePatternInfoImpl(FCameraShakeInfo& OutInfo) const override;
    virtual void StartShakePatternImpl(const FCameraShakePatternStartParams& Params) override { Age=0.f; }
    virtual void UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params,
        FCameraShakePatternUpdateResult& OutResult) override;
    virtual bool IsFinishedImpl() const override { return Age>=DurationSeconds; }
    virtual void StopShakePatternImpl(const FCameraShakePatternStopParams& Params) override { Age=DurationSeconds; }
    float Age=0.f;
};

UCLASS()
class FPSGAME_API UDoorPushCameraShake : public UCameraShakeBase
{
    GENERATED_BODY()
public:
    UDoorPushCameraShake(const FObjectInitializer& ObjectInitializer);
};
