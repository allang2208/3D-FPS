#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "FPSPlayerHeadAnimInstance.generated.h"

/** Copies shared body bones while preserving the head's independent facial rig. */
UCLASS(Transient)
class FPSGAME_API UFPSPlayerHeadAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
