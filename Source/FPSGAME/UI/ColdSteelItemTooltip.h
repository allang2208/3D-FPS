#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelItemTooltipData.h"
#include "ColdSteelItemTooltip.generated.h"
class USizeBox;
class UScrollBox;
class UHorizontalBox;
class UButton;
class UTextBlock;
class UVerticalBox;
class UColdSteelStatusModel;
/** One read-only inspector shared by inventory, equipment and warehouse. */
UCLASS()
class FPSGAME_API UColdSteelItemTooltip : public UUserWidget
{
    GENERATED_BODY()
public:
    void ShowItem(const FString& Id,FVector2D Anchor,bool Pin,UWidget* Source);
    void Hide(bool Force=false);
    bool IsPinned()const{return bPinned&&IsVisible();}
    const FString& ItemId()const{return InstanceId;}
    const FColdSteelTooltipContent& Content()const{return Presentation;}
    FVector2D Extent()const{return Size;}
    bool HasHorizontalOverflow()const{return bHorizontalOverflow;}
    bool HasVerticalOverflow()const{return bVerticalOverflow;}
    void ScrollToSideCards();
protected:
    virtual void NativeOnInitialized()override;
    virtual void NativeConstruct()override;
    virtual void NativeDestruct()override;
    virtual void NativeTick(const FGeometry&,float)override;
    virtual FReply NativeOnKeyDown(const FGeometry&,const FKeyEvent&)override;
private:
    friend class UColdSteelHUDWidget;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY() TObjectPtr<USizeBox> Frame;
    UPROPERTY() TObjectPtr<USizeBox> HorizontalHeight;
    UPROPERTY() TObjectPtr<UScrollBox> Horizontal;
    UPROPERTY() TObjectPtr<UScrollBox> Vertical;
    UPROPERTY() TObjectPtr<UHorizontalBox> Cards;
    UPROPERTY() TObjectPtr<UButton> Close;
    UPROPERTY() TArray<TObjectPtr<class UTexture2D>> Textures;
    TWeakObjectPtr<UWidget> ReturnFocus;
    FDelegateHandle ChangedHandle;
    FColdSteelTooltipContent Presentation;
    FString InstanceId,Signature;
    FVector2D At,Size,LastViewport;
    float Scale=1;
    int32 Settle=0;
    bool bPinned=false,bHorizontalOverflow=false,bVerticalOverflow=false;
    void Refresh();
    void BuildCards();
    void FitAndPlace(bool RevealMain);
    UTextBlock* Text(const FString&,float,const FLinearColor&,bool Numeric=false);
    void AddRow(UVerticalBox*,const FColdSteelTooltipRow&);
    UFUNCTION() void CloseClicked();
};
