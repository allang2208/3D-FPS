#pragma once
#include "FatZombieAnimInstance.h"
#include "M10AnimInstance.generated.h"

/** Keeps the shared reaction/combat clock, adds M10-only phase-synchronous turns. */
UCLASS(Transient)
class FPSGAME_API UM10AnimInstance : public UFatZombieAnimInstance
{
    GENERATED_BODY()
public:
    virtual void NativeUpdateAnimation(float DeltaSeconds) override;
    float GaitPhase=0.f,LocomotionWeight=0.f,CurveWeight=0.f,PivotWeight=0.f,RightWeight=.5f,IdleTime=0.f;
    bool LocomotionAllowed=false;
    float GaitRate=0.f;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
private:
    float LastYaw=0.f,SmoothedYawRate=0.f;
    bool HaveYaw=false;
};
