#pragma once
#include "Animation/AnimSingleNodeInstance.h"
#include "StableHorseAnimInstance.generated.h"

UCLASS(Transient)
class FPSGAME_API UStableHorseAnimInstance : public UAnimSingleNodeInstance
{
    GENERATED_BODY()
protected:
    FAnimInstanceProxy* CreateAnimInstanceProxy() override;
};
