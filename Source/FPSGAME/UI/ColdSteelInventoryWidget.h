#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/DragDropOperation.h"
#include "ColdSteelInventoryTypes.h"
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
    FColdSteelItem SourceSnapshot;
    bool bHasSourceSnapshot=false;
    // Pending drop orientation, absolute; initialised from the source instance.
    bool bRotated=false;
    // Pointer position inside the item's cell rect, normalised, so a turn keeps the same corner.
    FVector2D GrabNorm=FVector2D(.5f,.5f);
    // Grab geometry captured at drag start; turns derive from these so they can never drift.
    FIntPoint BaseGrabOffset=FIntPoint::ZeroValue;
    FVector2D BaseGrabNorm=FVector2D(.5f,.5f);
    TWeakObjectPtr<class UColdSteelInventoryWidget> PreviewBoard;
    bool IsCurrent(const UColdSteelStatusModel* Model) const;
    TWeakObjectPtr<class UColdSteelInventoryWidget> SourceBoard;
    TWeakObjectPtr<class UColdSteelHUDWidget> SourceHUD;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelDragVisual> PointerVisual;
    void ReleaseVisual();
    virtual void Dragged_Implementation(const FPointerEvent&)override;
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
    bool DropAt(const FString& Id,int32 Place,int32 Cell,int32 Orientation=-1);
    void CancelInteraction();
    void FinishDrag();
    void OpenItemMenu(FVector2D Anchor,bool SplitOnly=false);
    FString Selection()const{return Selected;}
    void ConfigureWarehouse(class UColdSteelHUDWidget* Owner);
    void ResetStoragePage();
    /** Re-evaluates this board's drop highlight after the drag orientation changed. */
    void RefreshDragPreview(class UColdSteelItemDrag& Drag);
    /** Turns the in-flight drag a quarter turn; the host may call it while the pointer is outside this board. */
    bool RotateDraggedItem(const FGeometry& G);
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
    FString PendingTooltip;
    FVector2D TooltipAnchor;
    float TooltipHoverTime=0;
    bool bHoverTooltipShown=false;
    friend class UColdSteelHUDWidget;
    friend class UColdSteelInventoryPopup;
    friend class UColdSteelWarehouseWidget;
    bool bWarehouse=false;
    TWeakObjectPtr<class UColdSteelHUDWidget> StorageHUD;
    int32 StoragePlace()const{return bWarehouse?4:0;}
    int32 StorageStart()const;
    int32 StorageRows()const;
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
    TWeakObjectPtr<UColdSteelItemDrag> ActivePointerDrag;
    bool bPendingClick=false;
    int32 KeyboardHotbar=-1;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelInventoryPopup> ItemMenu;
    bool bPreviewValid=false;
    TArray<FIntRect> SwapDestinations;
    int32 PreviewPlace=-1,PreviewCell=-1;
    // Highlight footprint follows the pending orientation of the drag in progress.
    FIntPoint PreviewCells=FIntPoint(1,1);
    bool bPreviewRotatable=false;
    int32 FocusPlace=0,FocusCell=0;
    int32 PressPlace=-1,PressCell=-1;
    bool bConfirmDrop=false;
    float Scale=1;
    struct FBoardLayout {float Width,Cell,GearWidth,GearHeight,GearY,GearPitch,BagY,HotY,Height;};
    FBoardLayout Layout(const FGeometry& G)const;
    bool Hit(const FGeometry&,FVector2D Screen,int32& Place,int32& Cell)const;
    FString IdAt(int32 Place,int32 Cell)const;
    void LoadIcons();
    void OnWeaponIconReady(const FString& Recipe);
    void RefreshPresentation();
    void ClearDragPreview();
    FIntPoint PendingFootprint(const FColdSteelItem& Item,const UColdSteelItemDrag& Drag)const;
    bool PreviewItemDrag(UColdSteelItemDrag& Drag,FVector2D Screen);
    void UpdateDragGhost(UColdSteelItemDrag& Drag,const FGeometry& G,FVector2D CursorPos)const;
    struct FItemPresentation {FString Name,Rarity;int32 Enhancement=0;bool Crafted=false,Enchanted=false;};
    TMap<FString,FItemPresentation> Presentation;
    int32 HoverPlace=-1,PointerCell=-1;
    bool bSortHovered=false;
    bool bProcessingAnimated=false;
    float GlintSeconds=0;
};
