#pragma once
#include "Camera/CameraShakeBase.h"
#include "Mutant3PounceCameraShake.generated.h"

UCLASS()
class FPSGAME_API UMutant3PounceShakePattern : public UCameraShakePattern
{
    GENERATED_BODY()
private:
    virtual void GetShakePatternInfoImpl(FCameraShakeInfo& OutInfo) const override;
    virtual void StartShakePatternImpl(const FCameraShakePatternStartParams& Params) override { Age=0.f; }
    virtual void UpdateShakePatternImpl(const FCameraShakePatternUpdateParams& Params, FCameraShakePatternUpdateResult& OutResult) override;
    virtual bool IsFinishedImpl() const override { return Age>=.18f; }
    virtual void StopShakePatternImpl(const FCameraShakePatternStopParams& Params) override { Age=.18f; }
    float Age=0.f;
};

UCLASS()
class FPSGAME_API UMutant3PounceCameraShake : public UCameraShakeBase
{
    GENERATED_BODY()
public:
    UMutant3PounceCameraShake(const FObjectInitializer& ObjectInitializer);
};
