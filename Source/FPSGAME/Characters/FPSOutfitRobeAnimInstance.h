#pragma once
#include "CoreMinimal.h"
#include "Animation/AnimInstance.h"
#include "FPSOutfitRobeAnimInstance.generated.h"

/** Copies the final body pose while retaining this garment's own cloth update. */
UCLASS(Transient)
class FPSGAME_API UFPSOutfitRobeAnimInstance : public UAnimInstance
{
    GENERATED_BODY()
protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
    virtual void DestroyAnimInstanceProxy(FAnimInstanceProxy* Proxy) override;
};
