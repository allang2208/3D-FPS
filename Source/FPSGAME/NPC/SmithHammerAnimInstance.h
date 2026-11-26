#pragma once

#include "Animation/AnimInstance.h"
#include "SmithHammerAnimInstance.generated.h"

/** Plays the two-handed guard stance, gait and hammer swing on the resident body. */
UCLASS(Transient)
class FPSGAME_API USmithHammerAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
public:
    static const FTransform HammerInRightHand;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
