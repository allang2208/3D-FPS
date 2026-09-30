#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "GunAssemblyActionWidget.generated.h"
class UTextBlock;
class UBorder;
class UBackgroundBlur;
class USizeBox;
class UProgressBar;
class UHorizontalBoxSlot;
class UVerticalBoxSlot;
class UGunAssemblySystem;
UCLASS()
class FPSGAME_API UGunAssemblyActionWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Refresh(const UGunAssemblySystem* System,const FString& Message,int32 Selected,bool Held);
    FVector2D Aim=FVector2D(.5,.45),Target=FVector2D(.5,.42);
    TArray<FVector2D> Markers;
    TArray<FString> Names;
    TArray<bool> Done;
    int32 Highlight=INDEX_NONE;
    bool bCalibration=false,bFinished=false,bInside=false;
protected:
    virtual void NativeOnInitialized() override;
    virtual int32 NativePaint(const FPaintArgs&,const FGeometry&,const FSlateRect&,FSlateWindowElementList&,int32,const FWidgetStyle&,bool) const override;
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
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Details;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Hint;
    UPROPERTY(Transient) TObjectPtr<UBorder> Panel;
    UPROPERTY(Transient) TObjectPtr<UBorder> Content;
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> Blur;
    UPROPERTY(Transient) TObjectPtr<USizeBox> PanelSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> TimerSize;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> Timer;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> DetailsSlot;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> HeadingSlot;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> TimerSlot;
    UPROPERTY(Transient) TObjectPtr<UVerticalBoxSlot> HintSlot;
};
