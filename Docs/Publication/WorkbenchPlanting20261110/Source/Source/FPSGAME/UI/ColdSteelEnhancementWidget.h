#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Blueprint/DragDropOperation.h"
#include "Styling/SlateTypes.h"
#include "ColdSteelEnhancementSystem.h"
#include "ColdSteelEnhancementWidget.generated.h"

/** A retrieval intent, never an inventory item or a world pickup. */
UCLASS()
class UColdSteelEnhancementDrag : public UDragDropOperation
{
    GENERATED_BODY()
public:
    TWeakObjectPtr<class UColdSteelEnhancementWidget> Source;
    FColdSteelItem Item;
    bool PreviewReturn(const class UColdSteelStatusModel* Model,FColdSteelItem& Placed,FString& Reason) const;
    bool Retrieve();
    UPROPERTY(Transient) TObjectPtr<class UColdSteelDragVisual> PointerVisual;
    void ReleaseVisual();
    virtual void Dragged_Implementation(const FPointerEvent&)override;
    virtual void Drop_Implementation(const FPointerEvent&)override;
    virtual void DragCancelled_Implementation(const FPointerEvent&)override;
    void HandleApplicationActivation(bool Active);
    FDelegateHandle ActivationHandle;
};

UCLASS()
class FPSGAME_API UColdSteelEnhancementWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void ConfigureWorld(class AEnhancementWorldView* View);
    bool ContainsManagement(FVector2D Position) const;
    bool ContainsRitual(FVector2D Position) const;
    bool HandleItemDrop(class UColdSteelItemDrag* Drag,FVector2D Position);
    void SelectItem(const FString& Id);
    bool CanRetrieve(const FColdSteelItem& Snapshot) const;
    bool RetrieveItem(const FColdSteelItem& Snapshot);
    void SelectTab(bool Enchant);
    void SelectScroll(const FString& Id);
    bool Confirm();
    void Refresh();
    const FColdSteelEnhanceQuote& CurrentQuote()const{return Preview;}
    const FString& SelectedItem()const{return ItemId;}
    bool IsEnchantTab()const{return bEnchant;}
    const FString& Result()const{return Message;}
    TSharedPtr<class SButton> ConfirmControl;
    TSharedPtr<class SButton> EnchantControl;
    TSharedPtr<class SButton> EnhanceControl;
    UPROPERTY(Transient) TObjectPtr<class UM4GunsmithWidget> WorkbenchPreview;
    TSharedPtr<class SWidget> PreviewSurface;
    TSharedPtr<class SButton> ResetViewControl,AimViewControl;
protected:
    virtual TSharedRef<SWidget> RebuildWidget()override;
    virtual void NativeConstruct()override;
    virtual void NativeDestruct()override;
    virtual void NativeTick(const FGeometry&,float Delta)override;
    virtual FReply NativeOnKeyDown(const FGeometry&,const FKeyEvent&)override;
    virtual FReply NativeOnMouseMove(const FGeometry&,const FPointerEvent&)override;
    virtual void NativeOnMouseLeave(const FPointerEvent&)override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&)override;
    virtual FReply NativeOnMouseButtonUp(const FGeometry&,const FPointerEvent&)override;
    virtual void NativeOnDragDetected(const FGeometry&,const FPointerEvent&,UDragDropOperation*&)override;
    virtual bool NativeOnDragOver(const FGeometry&,const FDragDropEvent&,UDragDropOperation*)override;
    virtual bool NativeOnDrop(const FGeometry&,const FDragDropEvent&,UDragDropOperation*)override;
private:
    class UColdSteelEnhancementSystem* System()const;
    class UColdSteelStatusModel* Profile()const;
    TSharedRef<class SWidget> Label(const FString&,int32 Size=14,FLinearColor Color=FLinearColor::White,bool Numeric=false)const;
    TSharedRef<class SButton> Button(const FString&,TFunction<void()>,bool Primary=false,bool Selected=false,bool Enabled=true);
    TSharedRef<class SWidget> TableRow(const FString&,const FString&,const FString&,const FString&,int32 Benefit=0)const;
    TSharedRef<class SWidget> GlassPanel(TSharedRef<class SWidget> Content);
    void UpdateResponsiveLayout();
    void BuildStatComparison(const FColdSteelItem& Before,const FColdSteelItem& After);
    void RefreshIcons();
    void OnWeaponIconReady(const FString& Recipe);
    const FSlateBrush* MaterialIcon(const FString& Definition);
    void ImportMaterialIcon(const FString& Definition);
    TMap<FString,TSharedPtr<FSlateBrush>> MaterialBrushes;
    TMap<FString,TSharedPtr<class SImage>> ItemImages;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<class UTexture2D>> MaterialTextures;
    // 目录小图按限时泵逐帧导入：MaterialIcon 只入队并返回空画刷（调用方亮字牌回退），
    // 导入完成后按 Definition 回填登记过的图标位，首帧不再被成批 PNG 解码卡住。
    TArray<FString> PendingIcons;
    TMap<FString,TArray<TWeakPtr<class SImage>>> PendingIconImages;
    TMap<FString,TArray<TWeakPtr<class SBorder>>> PendingIconTiles;
    FString ItemId,ScrollId,Message,PlacementRequestId;
    bool bEnchant=false,bCompareBase=false,bLastApplySucceeded=false,bProcessingRequest=false;
    double LastConfirm=-1,FlashUntil=-1;
    FColdSteelEnhanceQuote Preview;
    FDelegateHandle ProfileHandle,IconHandle,NetworkHandle;
    void OnNetworkResult(bool Success,const FString& Result);
    bool HitWorldItem(FVector2D Position) const;
    FColdSteelItem PressedBenchItem;
    TWeakObjectPtr<UColdSteelEnhancementDrag> ActiveBenchDrag;
    void RefreshBenchDragVisual();
    bool bWorldMode=false;
    TWeakObjectPtr<class AEnhancementWorldView> WorldView;
    TSharedPtr<class SWidget> ManagementSurface;
    TSharedPtr<class SVerticalBox> Rail,Inspector,ProjectSummary,Costs;
    TSharedPtr<class SHorizontalBox> Options;
    TSharedPtr<class STextBlock> ItemTitle,ItemLevel,Footer,ConfirmText;
    TSharedPtr<class STextBlock> LevelBadge,LevelMax,SoulChip,StoneChip,DustChip;
    TSharedPtr<class SHorizontalBox> LevelTrack,AffixRow;
    TSharedPtr<class SBorder> FlashOverlay;
    TSharedPtr<class SBox> BodyHost;
    TSharedPtr<class SWidget> RailContent,CenterContent,InspectorContent;
    TSharedPtr<class SScrollBox> RailScroll,OptionScroll,OverviewScroll,BodyScroll;
    TSharedPtr<class SButton> CurrentCompare,BaseCompare;
    int32 LayoutMode=-1;
    FSlateBrush Background,WeaponBrush,PanelBrush,RowBrush,GlassFallback;
    FSlateBrush TrackDone,TrackNext,TrackIdle,FlashBrush;
    FButtonStyle Normal,SelectedStyle,PrimaryStyle;
    UPROPERTY(Transient) TObjectPtr<class UTexture2D> BackgroundTexture;
    void LoadArcaneBackground();
    void SetScrollFilter(int32 Filter);
    FString EquipmentSearch;
    int32 ScrollFilter=0,BackgroundRequest=0;
    bool bClosing=false;
    TSharedPtr<class SColdSteelArcaneSeal> RitualSeal;
    TSharedPtr<class SHorizontalBox> ScrollFilters;
    TSharedPtr<class SButton> ScrollFilterControls[3];
    TSharedPtr<class STextBlock> DirectoryCount,OperationBadge,OutcomeText;
    FSearchBoxStyle EquipmentSearchStyle;
};
