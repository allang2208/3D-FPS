#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "DevelopmentListOptionWidget.generated.h"

class UTextBlock;

/** Owns the text while UComboBoxString retains its Slate widget. */
UCLASS()
class FPSGAME_API UDevelopmentListOptionWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    UTextBlock* GetLabel() const { return Label; }
protected:
    virtual void NativeOnInitialized() override;
private:
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Label;
};
