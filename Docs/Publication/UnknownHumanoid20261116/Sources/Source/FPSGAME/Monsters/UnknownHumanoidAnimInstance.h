#pragma once

#include "Animation/AnimInstance.h"
#include "UnknownHumanoidAnimInstance.generated.h"

UCLASS(Transient)
class FPSGAME_API UUnknownHumanoidAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    UUnknownHumanoidAnimInstance();

protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
