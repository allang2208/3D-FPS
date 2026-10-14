#pragma once
#include "CoreMinimal.h"
#include "Blueprint/UserWidget.h"
#include "Styling/SlateBrush.h"
#include "ColdSteelShopModel.h"
#include "ColdSteelShopWidget.generated.h"
class UColdSteelHUDWidget;
class UColdSteelShopWidget;
class UTextBlock;
class UEditableTextBox;
class UButton;
class UBorder;
class USizeBox;

/** A view of shop stock / the sale selection using the backpack's spatial grid. */
UCLASS()
class UColdSteelShopGrid : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelShopWidget* Owner, bool Sale);
    void SetItems(const TArray<FColdSteelShopSaleLine>& Items);
    void ResetPage();
    void TurnPage(int32 Direction, bool Wrap = false);
    void SelectKey(const FString& Key, bool Reveal);
    const FColdSteelShopSaleLine* SelectedLine() const;
    int32 PageNumber() const { return Page + 1; }
    int32 PageCount() const { return PageRows.Num(); }
    int32 ItemCount() const { return Entries.Num(); }
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeTick(const FGeometry&, float) override;
    virtual int32 NativePaint(const FPaintArgs&, const FGeometry&, const FSlateRect&, FSlateWindowElementList&, int32, const FWidgetStyle&, bool) const override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry&, const FPointerEvent&) override;
    virtual FReply NativeOnMouseButtonDoubleClick(const FGeometry&, const FPointerEvent&) override;
    virtual FReply NativeOnMouseMove(const FGeometry&, const FPointerEvent&) override;
    virtual void NativeOnMouseLeave(const FPointerEvent&) override;
    virtual FReply NativeOnMouseWheel(const FGeometry&, const FPointerEvent&) override;
private:
    struct FEntry { FColdSteelShopSaleLine Line; FString Key, Name; FSlateBrush Icon; int32 Page = 0, Cell = 0; };
    void Pack();
    void InvalidateGridPaint();
    int32 Hit(const FGeometry&, FVector2D Screen) const;
    void GridGeometry(FVector2D& Origin, float& Cell) const;
    UPROPERTY(Transient) TObjectPtr<UColdSteelShopWidget> Shop;
    TArray<FEntry> Entries;
    TArray<int32> PageRows {1};
    FVector2D Size = FVector2D::ZeroVector;
    FString Selected;
    int32 Page = 0, Rows = 1, Hovered = INDEX_NONE;
    bool bSale = false;
};

UCLASS()
class FPSGAME_API UColdSteelShopWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    void Configure(UColdSteelHUDWidget* Owner);
    void Refresh();
    void ResetSession();
    bool AddToSale(const FString& Id);
    bool HandleItemDrop(class UColdSteelItemDrag* Drag, FVector2D Position);
    bool IsConfirming() const;
    bool ConfirmationContains(FVector2D Position) const;
    void CancelConfirmation();
    UColdSteelShopModel* ShopModel() const { return Model; }
    class UTexture2D* IconFor(const FColdSteelItem& Item);
    void GridChanged(bool Sale, bool ResetQuantity = false);
    void ActivateGridItem(bool Sale);
protected:
    virtual void NativeOnInitialized() override;
    virtual void NativeConstruct() override;
    virtual void NativeDestruct() override;
    virtual TSharedRef<SWidget> RebuildWidget() override;
    virtual FReply NativeOnMouseWheel(const FGeometry&, const FPointerEvent&) override;
    virtual bool NativeOnDragOver(const FGeometry&, const FDragDropEvent&, UDragDropOperation*) override;
    virtual bool NativeOnDrop(const FGeometry&, const FDragDropEvent&, UDragDropOperation*) override;
private:
    UFUNCTION() void Close();
    UFUNCTION() void Clear();
    UFUNCTION() void RequestSell();
    UFUNCTION() void ConfirmSell();
    UFUNCTION() void CancelSell();
    UFUNCTION() void BuySelected();
    UFUNCTION() void RemoveSelected();
    UFUNCTION() void SaleQuantityCommitted(const FText& Text, ETextCommit::Type CommitMethod);
    UFUNCTION() void PreviousBuyPage();
    UFUNCTION() void NextBuyPage();
    UFUNCTION() void PreviousSalePage();
    UFUNCTION() void NextSalePage();
    UPROPERTY(Transient) TObjectPtr<UColdSteelHUDWidget> HUD;
    UPROPERTY(Transient) TObjectPtr<UColdSteelShopModel> Model;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Balance;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Total;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> Message;
    UPROPERTY(Transient) TObjectPtr<UButton> SellButton;
    UPROPERTY(Transient) TObjectPtr<UColdSteelShopGrid> BuyGrid;
    UPROPERTY(Transient) TObjectPtr<UColdSteelShopGrid> SaleGrid;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> BuyInfo;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> SaleInfo;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> BuyPage;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> SalePage;
    UPROPERTY(Transient) TObjectPtr<UEditableTextBox> BuyQuantity;
    UPROPERTY(Transient) TObjectPtr<UEditableTextBox> SaleQuantity;
    UPROPERTY(Transient) TObjectPtr<UButton> BuyAction;
    UPROPERTY(Transient) TObjectPtr<UButton> SaleAction;
    UPROPERTY(Transient) TObjectPtr<UButton> BuyPrevious;
    UPROPERTY(Transient) TObjectPtr<UButton> BuyNext;
    UPROPERTY(Transient) TObjectPtr<UButton> SalePrevious;
    UPROPERTY(Transient) TObjectPtr<UButton> SaleNext;
    UPROPERTY(Transient) TObjectPtr<UBorder> BuyArea;
    UPROPERTY(Transient) TObjectPtr<UBorder> SaleArea;
    UPROPERTY(Transient) TObjectPtr<UBorder> Confirmation;
    UPROPERTY(Transient) TObjectPtr<USizeBox> ConfirmationCard;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> ConfirmationSummary;
    UPROPERTY(Transient) TObjectPtr<UTextBlock> ConfirmationTotal;
    UPROPERTY(Transient) TObjectPtr<UButton> CancelButton;
    UPROPERTY(Transient) TMap<FString,TObjectPtr<class UTexture2D>> Icons;
    FDelegateHandle Changed;
    FColdSteelShopQuote PendingQuote;
};
