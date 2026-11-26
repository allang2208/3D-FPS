#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimSingleNodeInstance.h"
#include "ResidentTurnAnimInstance.generated.h"

/** Evaluates the resident's own idle clip, then plants the feet during a local conversation turn. */
UCLASS(Transient)
class FPSGAME_API UResidentTurnAnimInstance : public UAnimSingleNodeInstance
{
    GENERATED_BODY()

public:
    TWeakObjectPtr<APlayerController> ConversationPlayer;

protected:
    virtual FAnimInstanceProxy* CreateAnimInstanceProxy() override;
};
