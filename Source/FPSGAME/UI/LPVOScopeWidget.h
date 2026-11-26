#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "LPVOScopeWidget.generated.h"

struct FPhysicalScopeScene;
// Owner-local physical gun lenses; combat HUD remains visible.
UCLASS()
class FPSGAME_API ULPVOScopeWidget : public UUserWidget
{
    GENERATED_BODY()
    TSharedPtr<FPhysicalScopeScene> PhysicalScene;
protected:
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
};
