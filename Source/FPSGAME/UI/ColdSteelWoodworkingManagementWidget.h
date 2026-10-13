#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/ComboBoxString.h"
#include "ColdSteelWoodworkingManagementWidget.generated.h"
class UColdSteelWoodworkingWidget;
class UColdSteelStatusModel;
class UWoodworkingSystem;
class UColdSteelForgeBoard;
class UColdSteelGunRecipeOptionWidget;
class UBackgroundBlur;
class UBorder;
class UButton;
class UTextBlock;
class USizeBox;
class UProgressBar;
class UTexture2D;
struct FColdSteelCraftingRecipe;
class UVerticalBox;
class UVerticalBoxSlot;
class UHorizontalBoxSlot;
class UHorizontalBox;
class UGridPanel;
class UGridSlot;
class UScrollBox;

UCLASS()
class FPSGAME_API UColdSteelWoodworkingManagementWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelWoodworkingWidget* Owner);
    bool IsRecipeMenuOpen() const;
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry& Geometry,float DeltaTime) override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&) override;
private:
    UFUNCTION() void HandleAction();
    UFUNCTION() void HandleDiscard();
    UFUNCTION() void HandleClose();
    UFUNCTION() void HandleRecipeSelected(FString Option,ESelectInfo::Type SelectionType);
    UFUNCTION() UWidget* GenerateRecipeOption(FString Option);
    UTextBlock* Text(const FString& Caption,float Pixels,bool bNumeric=false,bool bMedium=false);
    UButton* Button(const FString& Caption,UTextBlock*& Label);
    UVerticalBox* Card(UVerticalBox* Parent);
    void Space(UVerticalBoxSlot* Slot,FMargin Padding);
    void Refresh();
    void UpdateScale();
    const FColdSteelCraftingRecipe* Recipe() const;
    void CacheProductImages();
    void RefreshProductPreview();
    void AddMaterialCell(UWidget* Widget,int32 Row,int32 Column);
    void EnsureMaterialRows(int32 Count);
    FName ObservedPattern;
    FString ObservedJobId;
    bool bObservedFinished=false,bObservedBusy=false;
    uint8 ObservedPhase=255;
    FDelegateHandle ChangedHandle;
    float Scale=0,RefreshClock=0,BoardHeight=0;
    bool bMaterialsDirty=true,bCanStart=false,bCanDiscard=false;
    FString StartReason;
    struct FLabel {TWeakObjectPtr<UTextBlock> Widget;float Pixels;bool Numeric,Medium;};
    TArray<FLabel> Labels;
    // Slate owns the option's SObjectWidget; this cache only updates visible rows for DPI changes.
    TArray<TWeakObjectPtr<UColdSteelGunRecipeOptionWidget>> RecipeOptionWidgets;
    TArray<TWeakObjectPtr<UButton>> Buttons;
    TArray<TWeakObjectPtr<USizeBox>> ButtonSizes;
    TArray<TWeakObjectPtr<UBorder>> Cards;
    struct FRowSpacing {TWeakObjectPtr<UVerticalBoxSlot> Slot;FMargin Padding;};
    TArray<FRowSpacing> RowSpacings;
    TWeakObjectPtr<UColdSteelWoodworkingWidget> OwnerWidget;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<UWoodworkingSystem> System;
    UPROPERTY(Transient) TObjectPtr<UColdSteelForgeBoard> Board;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<UTexture2D>> ProductImages;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> RulesText;
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> Blur;
    UPROPERTY(Transient) TObjectPtr<UBorder> Shell;
    UPROPERTY(Transient) TObjectPtr<UBorder> Header;
    UPROPERTY(Transient) TObjectPtr<UBorder> Body;
    UPROPERTY(Transient) TObjectPtr<UBorder> Footer;
    UPROPERTY(Transient) TObjectPtr<USizeBox> BoardSize;
    UPROPERTY(Transient) TObjectPtr<UHorizontalBoxSlot> PreviewParameterSlot;
    UPROPERTY(Transient) TObjectPtr<UGridPanel> PreviewParameterGrid;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PreviewName;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PreviewScope;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PreviewStage;
    struct FPreviewRow { TWeakObjectPtr<UTextBlock> Name,Value; };
    TArray<FPreviewRow> PreviewRows;
    TArray<TWeakObjectPtr<UGridSlot>> PreviewCellSlots;
    UPROPERTY(Transient) TObjectPtr<USizeBox> CloseSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> TimerSize;
    UPROPERTY(Transient) TObjectPtr<UScrollBox> Scroll;
    UPROPERTY(Transient) TObjectPtr<UHorizontalBoxSlot> DiscardActionSlot;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> RecipeTitle;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Materials;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Stage;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Stats;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StatLegend;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> RefundPreview;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Status;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> ActionLabel;
    UPROPERTY(Transient) TObjectPtr<UButton> ActionButton;
    UPROPERTY(Transient) TObjectPtr<UButton> DiscardButton;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> Timer;
    UPROPERTY(Transient) TObjectPtr<UComboBoxString> RecipeChoice;
    // Reused on data changes; the widget tree owns these children.
    struct FMaterialRow
    {
        TWeakObjectPtr<UTextBlock> Name,Owned,Separator,Required,State;
        TWeakObjectPtr<UHorizontalBox> Amount;
    };
    TArray<FMaterialRow> MaterialRows;
    TWeakObjectPtr<UGridPanel> MaterialGrid;
    TArray<TWeakObjectPtr<UGridSlot>> MaterialCellSlots;
    TWeakObjectPtr<UTextBlock> MaterialQuantityHeader,MaterialSource;
};
