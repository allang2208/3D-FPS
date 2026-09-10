#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/DragDropOperation.h"
#include "ColdSteelInventoryWidget.generated.h"
class UColdSteelStatusModel;
UCLASS()
class UColdSteelItemDrag : public UDragDropOperation
{
    GENERATED_BODY()
public:
    FString ItemId;
    FIntPoint GrabOffset=FIntPoint::ZeroValue;
    int32 HotbarIndex=-1;
    int32 SourcePlace=-1,SourceCell=-1;
    TWeakObjectPtr<class UColdSteelInventoryWidget> SourceBoard;
    virtual void Drop_Implementation(const FPointerEvent&)override;
    virtual void DragCancelled_Implementation(const FPointerEvent&)override;
};
/** Spatial board renders shared cold-steel tokens; all writes route to the profile. */
UCLASS()
class FPSGAME_API UColdSteelInventoryWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void SelectItem(const FString& Id){Selected=Id;}
    void PerformAction(int32 Action);
    bool DropAt(const FString& Id,int32 Place,int32 Cell);
    void CancelInteraction();
    void FinishDrag();
    void OpenItemMenu(FVector2D Anchor,bool SplitOnly=false);
    FString Selection()const{return Selected;}
protected:
    virtual FReply NativeOnMouseMove(const FGeometry&,const FPointerEvent&)override;
    virtual void NativeOnMouseLeave(const FPointerEvent&)override;
    virtual void NativeOnFocusLost(const FFocusEvent&)override;
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeTick(const FGeometry&,float) override;
    virtual void NativeDestruct() override;
    virtual int32 NativePaint(const FPaintArgs&,const FGeometry&,const FSlateRect&,FSlateWindowElementList&,int32,const FWidgetStyle&,bool)const override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&) override;
    virtual FReply NativeOnMouseButtonUp(const FGeometry&,const FPointerEvent&) override;
    virtual FReply NativeOnMouseButtonDoubleClick(const FGeometry&,const FPointerEvent&) override;
    virtual FReply NativeOnKeyDown(const FGeometry&,const FKeyEvent&) override;
    virtual void NativeOnDragDetected(const FGeometry&,const FPointerEvent&,UDragDropOperation*&) override;
    virtual bool NativeOnDragOver(const FGeometry&,const FDragDropEvent&,UDragDropOperation*) override;
    virtual bool NativeOnDrop(const FGeometry&,const FDragDropEvent&,UDragDropOperation*) override;
    virtual void NativeOnDragLeave(const FDragDropEvent&,UDragDropOperation*) override;
private:
    class UColdSteelHUDWidget* TooltipHUD()const;
    bool bKeyboardTooltip=false;
    friend class UColdSteelHUDWidget;
    friend class UColdSteelInventoryPopup;
    UPROPERTY() TObjectPtr<UColdSteelStatusModel> Model;
    FDelegateHandle ModelHandle;
    FDelegateHandle IconHandle;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelWeaponIcons> WeaponIcons;
    const FSlateBrush* ItemBrush(const struct FColdSteelItem& Item) const;
    UPROPERTY() TMap<FString,TObjectPtr<class UTexture2D>> Icons;
    TMap<FString,FSlateBrush> IconBrushes;
    FString Selected;
    FString KeyboardCarry;
    FString HoverPreview;
    FString DraggedItem,InteractionMessage,PreviewReason,PressedItem;
    FVector2D PressPosition;
    bool bPendingClick=false;
    int32 KeyboardHotbar=-1;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelInventoryPopup> ItemMenu;
    bool bPreviewValid=false;
    int32 PreviewPlace=-1,PreviewCell=-1;
    int32 FocusPlace=0,FocusCell=0;
    int32 PressPlace=-1,PressCell=-1;
    bool bConfirmDrop=false;
    float Scale=1;
    struct FBoardLayout {float Width,Cell,GearWidth,GearHeight,GearY,GearPitch,BagY,HotY,Height;};
    FBoardLayout Layout(const FGeometry& G)const;
    bool Hit(const FGeometry&,FVector2D Screen,int32& Place,int32& Cell)const;
    FString IdAt(int32 Place,int32 Cell)const;
    void LoadIcons();
};
