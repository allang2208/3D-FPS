#pragma once
#include "CoreMinimal.h"
#include "FatZombieAnimInstance.h"
#include "BoundCongregateAnimInstance.generated.h"

UCLASS(Transient)
class FPSGAME_API UBoundCongregateAnimInstance : public UFatZombieAnimInstance
{
    GENERATED_BODY()
public:
    virtual void NativeInitializeAnimation() override;
    virtual void NativeUpdateAnimation(float Dt) override;
    float GaitPhase=0.f;
    bool bGait=false;
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
private:
    float PreviousYaw=0.f;
    bool bHaveYaw=false;
};
