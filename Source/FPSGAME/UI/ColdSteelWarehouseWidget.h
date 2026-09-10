#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "ColdSteelInventoryWidget.h"
#include "ColdSteelWarehouseWidget.generated.h"
class UColdSteelStatusModel;
class UColdSteelHUDWidget;
class UTextBlock;
class UButton;
class UComboBoxString;
class UScrollBox;
UCLASS()
class UColdSteelWarehouseDrag : public UColdSteelItemDrag
{
    GENERATED_BODY()
public:
    TWeakObjectPtr<UWidget> SourceWidget;
    virtual void Drop_Implementation(const FPointerEvent&) override;
    virtual void DragCancelled_Implementation(const FPointerEvent&) override;
};
UCLASS()
class FPSGAME_API UColdSteelWarehouseCell : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelStatusModel* Source,int32 Index);
    void Refresh();
    void SetHUD(UColdSteelHUDWidget* Owner){HUD=Owner;}
    UWidget* MakeDetails();
protected:
    virtual void NativeOnInitialized() override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&) override;
    virtual FReply NativeOnMouseButtonUp(const FGeometry&,const FPointerEvent&) override;
    virtual FReply NativeOnMouseButtonDoubleClick(const FGeometry&,const FPointerEvent&) override;
    virtual FReply NativeOnKeyDown(const FGeometry&,const FKeyEvent&) override;
    virtual void NativeOnDragDetected(const FGeometry&,const FPointerEvent&,UDragDropOperation*&) override;
    virtual bool NativeOnDragOver(const FGeometry&,const FDragDropEvent&,UDragDropOperation*) override;
    virtual bool NativeOnDrop(const FGeometry&,const FDragDropEvent&,UDragDropOperation*) override;
    virtual void NativeOnDragLeave(const FDragDropEvent&,UDragDropOperation*) override;
    virtual FReply NativeOnFocusReceived(const FGeometry&,const FFocusEvent&) override;
    virtual void NativeOnFocusLost(const FFocusEvent&)override;
    virtual void NativeOnMouseEnter(const FGeometry&,const FPointerEvent&) override;
    virtual void NativeOnMouseLeave(const FPointerEvent&) override;
    virtual FReply NativeOnMouseMove(const FGeometry&,const FPointerEvent&)override;
private:
    friend class UColdSteelHUDWidget;
    UPROPERTY() TObjectPtr<UColdSteelHUDWidget> HUD;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY() TObjectPtr<class UBorder> Surface;
    UPROPERTY() TObjectPtr<class UImage> Icon;
    UPROPERTY() TObjectPtr<class UTexture2D> Texture;
    UPROPERTY() TObjectPtr<UTextBlock> Caption;
    UPROPERTY() TObjectPtr<UTextBlock> Quantity;
    UPROPERTY() TObjectPtr<UTextBlock> Badges;
    UPROPERTY() TArray<TObjectPtr<class UBorder>> BadgeSurfaces;
    UPROPERTY() TArray<TObjectPtr<UTextBlock>> BadgeLabels;
    FString ItemId,LoadedDefinition;
    int32 Cell=0;
    bool bPointerFocus=false;
};
UCLASS()
class FPSGAME_API UColdSteelWarehouseWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelHUDWidget* Owner);
    void ResetPage();
    void Refresh();
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
private:
    friend class UColdSteelHUDWidget;
    UPROPERTY() TObjectPtr<UColdSteelHUDWidget> HUD;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY() TObjectPtr<UTextBlock> Capacity;
    UPROPERTY() TObjectPtr<UTextBlock> Page;
    UPROPERTY() TObjectPtr<UTextBlock> Message;
    UPROPERTY() TObjectPtr<UButton> Previous;
    UPROPERTY() TObjectPtr<UButton> Next;
    UPROPERTY() TObjectPtr<UComboBoxString> SortMenu;
    UPROPERTY() TObjectPtr<UScrollBox> Scroll;
    UPROPERTY() TArray<TObjectPtr<UColdSteelWarehouseCell>> Cells;
    FDelegateHandle ChangedHandle;
    UFUNCTION() void Close();
    UFUNCTION() void StoreAll();
    UFUNCTION() void Matching();
    UFUNCTION() void PreviousPage();
    UFUNCTION() void NextPage();
    UFUNCTION() void SortChanged(FString Selection,ESelectInfo::Type Type);
    UFUNCTION() UWidget* SortOption(FString Item);
};
