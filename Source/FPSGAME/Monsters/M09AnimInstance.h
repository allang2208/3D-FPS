#pragma once
#include "FatZombieAnimInstance.h"
#include "M09AnimInstance.generated.h"
/** Authored body/organ clips with a dedicated final ceiling-hand support solve. */
UCLASS(Transient)
class FPSGAME_API UM09AnimInstance : public UFatZombieAnimInstance
{
 GENERATED_BODY()
protected:
 virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
 virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
