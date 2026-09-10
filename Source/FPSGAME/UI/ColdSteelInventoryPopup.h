#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelInventoryPopup.generated.h"
class UColdSteelInventoryWidget;
class UColdSteelStatusModel;
class UVerticalBox;
class UEditableTextBox;
class UTextBlock;
UCLASS()
class FPSGAME_API UColdSteelInventoryPopup : public UUserWidget
{
    GENERATED_BODY()
public:
    void Open(UColdSteelInventoryWidget* Board,UColdSteelStatusModel* Model,const FString& Id,FVector2D Anchor,bool SplitOnly);
    void Close(bool RestoreFocus=true);
protected:
    virtual FReply NativeOnPreviewKeyDown(const FGeometry&,const FKeyEvent&)override;
    virtual FReply NativeOnKeyDown(const FGeometry&,const FKeyEvent&)override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&)override;
private:
    friend class UColdSteelHUDWidget;
    TWeakObjectPtr<UColdSteelInventoryWidget> OwnerBoard;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY() TObjectPtr<UVerticalBox> Stack;
    UPROPERTY() TObjectPtr<UEditableTextBox> Quantity;
    UPROPERTY() TObjectPtr<UTextBlock> Message;
    UPROPERTY() TObjectPtr<UTextBlock> DropCaption;
    FString ItemId;
    float Scale=1;
    bool bConfirmDrop=false;
    UTextBlock* Label(const FString& Text);
    class UButton* Button(const FString& Text);
    UFUNCTION() void Use();
    UFUNCTION() void Split();
    UFUNCTION() void ConfirmSplit();
    UFUNCTION() void Drop();
    UFUNCTION() void OpenGunsmith();
    UFUNCTION() void Details();
    UFUNCTION() void SortBag();
    UFUNCTION() void SaveBag();
    UFUNCTION() void Cancel();
    UFUNCTION() void QuantityCommitted(const FText& Text,ETextCommit::Type Type);
};
