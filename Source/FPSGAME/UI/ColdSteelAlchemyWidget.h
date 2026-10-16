#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Components/ComboBoxString.h"
#include "../Building/AlchemyTypes.h"
#include "../Building/AlchemyTabletop.h"
#include "ColdSteelAlchemyWidget.generated.h"
class UColdSteelAlchemySystem;
class UColdSteelStatusModel;
class AAlchemyWorldView;
class UPotionWorkbenchVisualComponent;
class UColdSteelAlchemyBookPreviewWidget;
class UCanvasPanel;
class UCanvasPanelSlot;
class UBorder;
class UButton;
class UTextBlock;
class UImage;
class UTexture2D;
class UVerticalBox;
class USizeBox;
class UColdSteelAlchemyWidget;
class UColdSteelForgeBoard;
class UColdSteelGunRecipeOptionWidget;
class UBackgroundBlur;
class UHorizontalBox;
class UHorizontalBoxSlot;
class UVerticalBoxSlot;
class UGridPanel;
class UGridSlot;
class UScrollBox;
class UProgressBar;

UCLASS()
class UColdSteelAlchemyAction : public UObject
{
    GENERATED_BODY()
public:
    TWeakObjectPtr<UColdSteelAlchemyWidget> Widget;
    int32 Action=0;
    bool Hold=false;
    UFUNCTION() void Click();
    UFUNCTION() void Press();
    UFUNCTION() void Release();
};
UCLASS()
class FPSGAME_API UColdSteelAlchemyWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    bool Configure(AActor* Station);
    void RequestClose();
    void EndSession();
    void Act(int32 Action,bool Release=false);
    bool ContainsManagement(FVector2D ScreenPosition) const;
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry& G,float Delta) override;
    virtual void NativeDestruct() override;
    virtual FReply NativeOnKeyDown(const FGeometry& G,const FKeyEvent& E) override;
    virtual FReply NativeOnKeyUp(const FGeometry& G,const FKeyEvent& E) override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry& G,const FPointerEvent& E) override;
    virtual FReply NativeOnMouseMove(const FGeometry& G,const FPointerEvent& E) override;
    virtual FReply NativeOnMouseButtonUp(const FGeometry& G,const FPointerEvent& E) override;
    virtual FReply NativeOnMouseWheel(const FGeometry& G,const FPointerEvent& E) override;
    virtual void NativeOnMouseCaptureLost(const FCaptureLostEvent& E) override;
private:
    friend class UAlchemyManualFlowAuditCommandlet;
    UFUNCTION() void Select(FString Option,ESelectInfo::Type How);
    UFUNCTION() UWidget* Option(FString Label);
    UTextBlock* Text(const FString& Value,float Pixels,bool Wrap=false,bool Numeric=false,bool Medium=false);
    UButton* Button(const FString& Value,int32 Action,bool Hold=false);
    void Build();
    void BuildEntry();
    void ScaleEntry();
    void LayoutEntry(FVector2D Size);
    void RefreshEntry(bool DataChanged);
    UVerticalBox* EntryCard(UVerticalBox* Parent);
    void EntrySpace(UVerticalBoxSlot* Slot,FMargin Padding);
    void AddEntryMaterialCell(UWidget* Widget,int32 Row,int32 Column);
    void EnsureEntryMaterialRows(int32 Count);
    void Refresh();
    void Layout(const FGeometry& Geometry);
    void World(bool On);
    void Book(bool On);
    void BookChanged(int32 Page);
    void Stop();
    void Return();
    void PrepareView();
    void SetWorkVisibility(ESlateVisibility Mode);
    bool CanTableAct(int32 Action) const;
    FAlchemyTableHit TableHit() const;
    bool BeginStirDrag();
    bool PointerStirAngle(float& Angle) const;
    bool PointerRay(FVector& Origin,FVector& Direction) const;
    void UpdateHover();
    const FAlchemyRecipe* Recipe() const;
    UPROPERTY(Transient) TObjectPtr<UColdSteelAlchemySystem> System;
    UPROPERTY(Transient) TObjectPtr<UColdSteelStatusModel> Model;
    UPROPERTY(Transient) TObjectPtr<AAlchemyWorldView> View;
    UPROPERTY(Transient) TObjectPtr<UCanvasPanel> Canvas;
    UPROPERTY(Transient) TObjectPtr<UBorder> Management;
    UPROPERTY(Transient) TObjectPtr<UBorder> Controls;
    UPROPERTY(Transient) TObjectPtr<UBorder> IngredientPanel;
    UPROPERTY(Transient) TObjectPtr<UBorder> FinishPanel;
    UPROPERTY(Transient) TObjectPtr<UBorder> Reader;
    UPROPERTY(Transient) TObjectPtr<UColdSteelAlchemyBookPreviewWidget> BookPage;
    UPROPERTY(Transient) TObjectPtr<UComboBoxString> Choice;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Materials;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Status;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> ProductInfo;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> LiveStatus;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Instruction;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Refund;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> PrepStatus;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> HoverHint;
    UPROPERTY(Transient) TObjectPtr<UBorder> HoverPopup;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> HoverTitle;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> HoverText;
    UPROPERTY(Transient) TObjectPtr<USizeBox> HoverSize;
    TWeakObjectPtr<UCanvasPanelSlot> HoverPopupSlot;
    FVector2D PointerScreen=FVector2D::ZeroVector;
    FVector2D StirCenter=FVector2D::ZeroVector,StirAxisX=FVector2D::ZeroVector,StirAxisY=FVector2D::ZeroVector;
    UPROPERTY(Transient) TArray<TObjectPtr<UTextBlock>> IngredientLabels;
    UPROPERTY(Transient) TArray<TObjectPtr<UColdSteelAlchemyAction>> Bindings;
    UPROPERTY(Transient) TMap<int32,TObjectPtr<UButton>> Actions;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<UTexture2D>> Images;
    struct FLabel {TWeakObjectPtr<UTextBlock> Widget;float Pixels;bool Numeric=false,Medium=false;};
    TArray<FLabel> Labels;
    TArray<TWeakObjectPtr<USizeBox>> ButtonSizes;
    TArray<TWeakObjectPtr<UWidget>> IngredientRows;
    FName Selection;
    FName PreparingRecipe;
    FString PreparingJob,DiscardConfirmJob;
    int64 DiscardConfirmRevision=-1;
    double EntryActionReadyAt=0;
    bool bShowEntryReadiness=true;
    FString LocalNotice;
    FString RefundSummary,CachedJob;
    TArray<FString> IngredientNames;
    FName CachedRecipe;
    int64 CachedJobRevision=-1;
    FDelegateHandle ModelChanged;
    bool bMaterialsDirty=true;
    TWeakObjectPtr<APawn> WorkingPawn;
    TWeakObjectPtr<UPotionWorkbenchVisualComponent> TableVisual;
    TWeakObjectPtr<UCanvasPanelSlot> ManagementSlot,ControlSlot,ReaderSlot,IngredientSlot,FinishSlot;
    float Clock=0,InputClock=0,Scale=1;
    int32 Held=-1,Spread=0,ObservedStep=INDEX_NONE,SelectedGrind=INDEX_NONE;
    bool bWorld=false,bBook=false,bClose=false,bReturn=false,bEnded=false,bConfirmDiscard=false,bPreparing=false,bDragging=false,bWorldHold=false;
    float DragAngle=0,DragRadians=0;
    bool bHasStirAngle=false,bStoppingInput=false;
    UPROPERTY(Transient) TObjectPtr<UBackgroundBlur> EntryBlur;
    UPROPERTY(Transient) TObjectPtr<UBorder> EntryHeader;
    UPROPERTY(Transient) TObjectPtr<UBorder> EntryBody;
    UPROPERTY(Transient) TObjectPtr<UBorder> EntryFooter;
    UPROPERTY(Transient) TObjectPtr<UScrollBox> EntryScroll;
    UPROPERTY(Transient) TObjectPtr<USizeBox> EntryCloseSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> EntryBoardSize;
    UPROPERTY(Transient) TObjectPtr<USizeBox> EntryTimerSize;
    UPROPERTY(Transient) TObjectPtr<UProgressBar> EntryTimer;
    UPROPERTY(Transient) TObjectPtr<UColdSteelForgeBoard> EntryPreview;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EntryRecipeTitle;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EntryMaterialSource;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EntryQuantityHeader;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EntryStage;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EntryStats;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EntryLegend;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EntryPreviewName;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> EntryPreviewStage;
    UPROPERTY(Transient) TObjectPtr<UGridPanel> EntryMaterialGrid;
    UPROPERTY(Transient) TObjectPtr<UGridPanel> EntryParameterGrid;
    TWeakObjectPtr<UHorizontalBoxSlot> EntryParameterSlot,EntryDiscardSlot,EntryManualSlot;
    TArray<TWeakObjectPtr<UBorder>> EntryCards;
    TArray<TWeakObjectPtr<UGridSlot>> EntryMaterialSlots,EntryParameterSlots;
    TArray<TWeakObjectPtr<UColdSteelGunRecipeOptionWidget>> EntryOptions;
    struct FEntrySpacing {TWeakObjectPtr<UVerticalBoxSlot> Slot;FMargin Padding;};
    TArray<FEntrySpacing> EntrySpacings;
    struct FEntryMaterialRow {TWeakObjectPtr<UTextBlock> Name,Owned,Separator,Required,State;TWeakObjectPtr<UHorizontalBox> Amount;};
    TArray<FEntryMaterialRow> EntryMaterialRows;
    struct FEntryParameterRow {TWeakObjectPtr<UTextBlock> Name,Value;};
    TArray<FEntryParameterRow> EntryParameterRows;
    float EntryScale=0,EntryBoardHeight=0;
    bool bEntryDirty=true;
};
