#pragma once

#include "Animation/AnimSingleNodeInstance.h"
#include "HerbalistRoamAnimInstance.generated.h"

/** Blends Lin Zhi's own idle with the walk pose reached at her current ground distance. */
UCLASS(Transient)
class UHerbalistRoamAnimInstance : public UAnimSingleNodeInstance
{
    GENERATED_BODY()

public:
    UPROPERTY(Transient) TObjectPtr<UAnimSequence> Walk;
    float WalkSeconds = 0.f;
    float WalkWeight = 0.f;

protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
};
