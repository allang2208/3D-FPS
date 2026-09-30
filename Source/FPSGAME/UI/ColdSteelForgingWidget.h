#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/ComboBoxString.h"
#include "ColdSteelForgingWidget.generated.h"
class UColdSteelHUDWidget;
class UColdSteelStatusModel;
class UColdSteelForgingSystem;
class UColdSteelForgeBoard;
class UBackgroundBlur;
class UBorder;
class UButton;
class UTextBlock;
class USizeBox;
class UProgressBar;
class UTexture2D;
class AVoxelBuildWorld;
class UVerticalBox;
class UVerticalBoxSlot;
class UHorizontalBoxSlot;
class UHorizontalBox;
class UGridPanel;
class UGridSlot;
class UScrollBox;

UCLASS()
class FPSGAME_API UColdSteelForgingWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelHUDWidget* Owner);
    void SetStation(AVoxelBuildWorld* InWorld,FIntVector InCell);
    void SetInputReady(bool bReady);
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
    UFUNCTION() void HandleSmelting();
    UFUNCTION() void HandleRecipeSelected(FString Option,ESelectInfo::Type SelectionType);
    UFUNCTION() UWidget* GenerateRecipeOption(FString Option);
    UTextBlock* Text(const FString& Caption,float Pixels,bool bNumeric=false,bool bMedium=false);
    UButton* Button(const FString& Caption,UTextBlock*& Label);
    UVerticalBox* Card(UVerticalBox* Parent);
    void Space(UVerticalBoxSlot* Slot,FMargin Padding);
    void Refresh();
    void UpdateScale();
    void LoadMold();
    void RefreshProductPreview();
    void AddMaterialCell(UWidget* Widget,int32 Row,int32 Column);
    void EnsureMaterialRows(int32 Count);
    FName SelectedRecipe;
    TWeakObjectPtr<AVoxelBuildWorld> World;
    FIntVector Cell=FIntVector::ZeroValue;
    FDelegateHandle ChangedHandle;
    float Scale=0,RefreshClock=0,BoardHeight=0;
    bool bInputReady=false,bMaterialsDirty=true,bCanStart=false,bCanDiscard=false;
    FString Notice,LoadedMold,StartReason;
    struct FLabel {TWeakObjectPtr<UTextBlock> Widget;float Pixels;bool Numeric,Medium;};
    TArray<FLabel> Labels;
    TArray<TWeakObjectPtr<UButton>> Buttons;
    TArray<TWeakObjectPtr<USizeBox>> ButtonSizes;
    TArray<TWeakObjectPtr<UBorder>> Cards;
    struct FRowSpacing {TWeakObjectPtr<UVerticalBoxSlot> Slot;FMargin Padding;};
    TArray<FRowSpacing> RowSpacings;
    UPROPERTY(Transient) TObjectPtr<UColdSteelHUDWidget> HUD;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<UColdSteelForgingSystem> System;
    UPROPERTY(Transient) TObjectPtr<UColdSteelForgeBoard> Board;
    UPROPERTY(Transient) TObjectPtr<UTexture2D> MoldTexture;
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
    UPROPERTY(Transient) TObjectPtr<UHorizontalBoxSlot> SecondaryActionSlot;
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
    UPROPERTY(Transient) TObjectPtr<UButton> SmeltingButton;
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
