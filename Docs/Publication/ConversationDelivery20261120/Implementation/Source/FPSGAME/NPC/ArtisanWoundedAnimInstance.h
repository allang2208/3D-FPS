#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "ArtisanWoundedAnimInstance.generated.h"

/** Keeps the resident's breathing animation underneath a ground-supported wounded idle. */
UCLASS(Transient)
class FPSGAME_API UArtisanWoundedAnimInstance : public UAnimSingleNodeInstance
{
    GENERATED_BODY()

protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
};
