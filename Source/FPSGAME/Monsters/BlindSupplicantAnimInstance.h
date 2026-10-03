#pragma once

#include "CoreMinimal.h"
#include "FatZombieAnimInstance.h"
#include "BlindSupplicantAnimInstance.generated.h"

/** M07 pose presentation; the inherited shared player retains all control clocks. */
UCLASS(Transient)
class FPSGAME_API UBlindSupplicantAnimInstance : public UFatZombieAnimInstance
{
    GENERATED_BODY()
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
