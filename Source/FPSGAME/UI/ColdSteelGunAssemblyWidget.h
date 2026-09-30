#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/ComboBoxString.h"
#include "ColdSteelGunAssemblyWidget.generated.h"
class UColdSteelHUDWidget;
class UColdSteelStatusModel;
class UGunAssemblySystem;
class UColdSteelForgeBoard;
class UColdSteelGunRecipeOptionWidget;
class UBackgroundBlur;
class UBorder;
class UButton;
class UTextBlock;
class USizeBox;
class UProgressBar;
class UTexture2D;
class UVerticalBox;
class UVerticalBoxSlot;
class UHorizontalBoxSlot;
class UHorizontalBox;
class UGridPanel;
class UGridSlot;
class UScrollBox;
class UWidgetSwitcher;

/** Assembly preparation uses the same dimensions and presentation as forging. */
UCLASS()
class FPSGAME_API UColdSteelGunAssemblyWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelHUDWidget* Owner){HUD=Owner;}
    void OpenStation();
    void SetInputReady(bool bReady);
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual void NativeTick(const FGeometry&,float) override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry&,const FPointerEvent&) override;
private:
    UFUNCTION() void HandleAction();
    UFUNCTION() void HandleDiscard();
    UFUNCTION() void HandleClose();
    UFUNCTION() void HandleRecipeSelected(FString Option,ESelectInfo::Type SelectionType);
    UFUNCTION() UWidget* GenerateRecipeOption(FString Option);
    UTextBlock* Text(const FString&,float,bool bNumeric=false,bool bMedium=false);
    UButton* Button(const FString&,UTextBlock*&);
    UVerticalBox* Card(UVerticalBox*);
    void Space(UVerticalBoxSlot*,FMargin);
    void AddMaterialCell(UWidget*,int32,int32);
    void EnsureMaterialRows(int32);
    void Refresh();
    void RefreshProductPreview();
    void UpdateScale();
    void LoadMold();
    void BuildManufacturingNavigation(UVerticalBox* Parent);
    void SelectManufacturingPage(bool bAmmo);
    void UpdateManufacturingNavigation();
    UFUNCTION() void HandleAmmoPage();
    UFUNCTION() void HandleGunPage();
    FName SelectedRecipe;
    FDelegateHandle ChangedHandle;
    float Scale=0,RefreshClock=0,BoardHeight=0;
    bool bInputReady=false,bMaterialsDirty=true,bCanDiscard=false;
    bool bAmmoPage=false;
    FString Notice,LoadedMold;
    struct FLabel {TWeakObjectPtr<UTextBlock> Widget;float Pixels;bool Numeric,Medium;};
    struct FRowSpacing {TWeakObjectPtr<UVerticalBoxSlot> Slot;FMargin Padding;};
    struct FPreviewRow {TWeakObjectPtr<UTextBlock> Name,Value;};
    struct FMaterialRow {TWeakObjectPtr<UTextBlock> Name,Owned,Separator,Required,State;TWeakObjectPtr<UHorizontalBox> Amount;};
    TArray<FLabel> Labels;
    TArray<TWeakObjectPtr<UColdSteelGunRecipeOptionWidget>> RecipeOptionWidgets;
    TArray<FRowSpacing> RowSpacings;
    TArray<FPreviewRow> PreviewRows;
    TArray<FMaterialRow> MaterialRows;
    TArray<TWeakObjectPtr<UButton>> Buttons;
    TArray<TWeakObjectPtr<USizeBox>> ButtonSizes;
    TArray<TWeakObjectPtr<UBorder>> Cards;
    TArray<TWeakObjectPtr<UGridSlot>> PreviewCellSlots,MaterialCellSlots;
    TWeakObjectPtr<UGridPanel> MaterialGrid;
    TWeakObjectPtr<UTextBlock> MaterialQuantityHeader,MaterialSource;
    UPROPERTY(Transient) TObjectPtr<UColdSteelHUDWidget> HUD;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<UGunAssemblySystem> System;
    UPROPERTY(Transient) TObjectPtr<UColdSteelForgeBoard> Board;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> MoldTexture;
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> Blur;
    UPROPERTY(Transient) TObjectPtr<UBorder> Shell;
    UPROPERTY(Transient) TObjectPtr<UBorder> Header;
    UPROPERTY(Transient) TObjectPtr<UBorder> Body;
    UPROPERTY(Transient) TObjectPtr<UBorder> Footer;
    UPROPERTY(Transient) TObjectPtr<USizeBox> BoardSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> CloseSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> TimerSize;
    UPROPERTY(Transient) TObjectPtr<UScrollBox> Scroll;
    UPROPERTY(Transient) TObjectPtr<UHorizontalBoxSlot> PreviewParameterSlot;
    UPROPERTY(Transient) TObjectPtr<UHorizontalBoxSlot> DiscardActionSlot;
    UPROPERTY(Transient) TObjectPtr<UGridPanel> PreviewParameterGrid;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PreviewName;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PreviewScope;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PreviewStage;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> RecipeTitle;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Materials;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Stage;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Stats;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> StatLegend;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PartsLabel;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> RefundPreview;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Status;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> ActionLabel;
    UPROPERTY(Transient) TObjectPtr<UButton> ActionButton;
    UPROPERTY(Transient) TObjectPtr<UButton> DiscardButton;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> Timer;
    UPROPERTY(Transient) TObjectPtr<UComboBoxString> RecipeChoice;
    UPROPERTY(Transient) TObjectPtr<UBorder> ManufacturingNavigation;
    UPROPERTY(Transient) TObjectPtr<UButton> AmmoPageButton;
    UPROPERTY(Transient) TObjectPtr<UButton> GunPageButton;
    UPROPERTY(Transient) TObjectPtr<USizeBox> AmmoPageSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> GunPageSize;
    UPROPERTY(Transient) TObjectPtr<UWidgetSwitcher> ManufacturingPages;
    UPROPERTY(Transient) TObjectPtr<UWidgetSwitcher> ManufacturingActions;
    void BuildAmmoCard(UVerticalBox* Parent,UVerticalBox* ActionParent);
    void RefreshAmmoCard();
    UFUNCTION() void HandleAmmoSelected(FString Option,ESelectInfo::Type SelectionType);
    UFUNCTION() void HandleAmmoCraft();
    TArray<FName> AmmoRecipeIds;
    FName SelectedAmmoRecipe;
    TArray<FMaterialRow> AmmoMaterialRows;
    bool bAmmoDirty=true;
    FString AmmoNotice;
    UPROPERTY(Transient) TObjectPtr<class UColdSteelCraftingSystem> Crafting;
    UPROPERTY(Transient) TObjectPtr<UComboBoxString> AmmoChoice;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> AmmoStock;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> AmmoStatus;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> AmmoActionLabel;
    UPROPERTY(Transient) TObjectPtr<UButton> AmmoAction;
};
