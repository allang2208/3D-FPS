#pragma once

#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelGunRecipeOptionWidget.generated.h"

class USizeBox;
class UTextBlock;

/** SObjectWidget keeps each combo option's UMG tree alive while Slate displays it. */
UCLASS()
class FPSGAME_API UColdSteelGunRecipeOptionWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(const FString& Option, float PixelScale);
    void SetPixelScale(float PixelScale);
protected:
    virtual void NativeOnInitialized() override;
private:
    UPROPERTY(Transient) TObjectPtr<USizeBox> OptionBox;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Label;
};
