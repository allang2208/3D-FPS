#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelForgeActionWidget.generated.h"
class UTextBlock;
class UBorder;
class UBackgroundBlur;
class USizeBox;
class UProgressBar;
class UHorizontalBoxSlot;
class UVerticalBoxSlot;
class UColdSteelForgingSystem;
UCLASS()
class FPSGAME_API UColdSteelForgeActionWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Refresh(const UColdSteelForgingSystem* System,bool Finishing,bool Feedback,bool Hit);
protected:
    virtual void NativeOnInitialized() override;
private:
    UTextBlock* Text(const FString& Caption,float Pixels,bool bNumeric=false);
    void UpdateLayout();
    struct FLabel {TWeakObjectPtr<UTextBlock> Widget;float Pixels;bool Numeric;};
    TArray<FLabel> Labels;
    TArray<TWeakObjectPtr<UBorder>> Cards;
    TArray<TWeakObjectPtr<UHorizontalBoxSlot>> CardSlots;
    float Scale=0,Width=0;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Heading;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> TimeLabel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> TimeValue;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> HitsValue;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> QualityValue;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Hint;
    UPROPERTY(Transient) TObjectPtr<UBorder> Panel;
    UPROPERTY(Transient) TObjectPtr<UBorder> Content;
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> Blur;
    UPROPERTY(Transient) TObjectPtr<USizeBox> PanelSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> TimerSize;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> Timer;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> HeadingSlot;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> TimerSlot;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> HintSlot;
};
