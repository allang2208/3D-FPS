#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateTypes.h"
#include "ColdSteelSkillPage.generated.h"
class UColdSteelStatusModel;
class UTexture2D;
class SBox;
class SScrollBox;
class SButton;

/** Passive skills live in the existing drawer; their effects are owned by the profile model. */
UCLASS()
class FPSGAME_API UColdSteelSkillPage : public UUserWidget
{
    GENERATED_BODY()
public:
    bool GoBack();
protected:
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual void ReleaseSlateResources(bool bReleaseChildren) override;
    virtual void NativeTick(const FGeometry& Geometry,float Delta) override;
private:
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> IconTexture;
    TSharedPtr<SBox> Root;
    TSharedPtr<SScrollBox> Scroll;
    TSharedPtr<SButton> DetailButton,BackButton;
    TArray<TSharedPtr<SButton>> FilterButtons;
    FSlateBrush IconBrush,CardBrush;
    FButtonStyle ActionStyle;
    float Scale=1;
    int32 Category=0;
    bool bDetail=false;
    TSharedRef<SWidget> BuildPage();
    TSharedRef<SWidget> Overview(bool bCompact);
    TSharedRef<SWidget> EffectRow(const FString& Caption,int32 Index);
    TSharedRef<SWidget> Label(const FString& Value,float Pixels,const FLinearColor& Color,bool bNumeric=false) const;
    FString EffectValue(int32 Index,bool bNext) const;
    FReply SelectCategory(int32 Index);
    FReply OpenDetail();
    void RefreshLayout();
};
