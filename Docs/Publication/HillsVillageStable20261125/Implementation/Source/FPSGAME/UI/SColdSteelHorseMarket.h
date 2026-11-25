#pragma once

#include "../Movement/StableHorseMarket.h"
#include "Styling/SlateBrush.h"
#include "UObject/StrongObjectPtr.h"
#include "Widgets/SCompoundWidget.h"

class SButton;
class SBox;
class SScrollBox;
class STextBlock;
class SHorseMarketPlate;
class SVerticalBox;
class UTexture2D;

class SColdSteelHorseMarket : public SCompoundWidget
{
public:
    DECLARE_DELEGATE_OneParam(FOpenHorse, FGuid);
    SLATE_BEGIN_ARGS(SColdSteelHorseMarket) : _Owned(false) {}
        SLATE_ARGUMENT(bool, Owned)
        SLATE_EVENT(FOpenHorse, OnDetails)
        SLATE_EVENT(FSimpleDelegate, OnSelect)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args);
    void SetStock(const TArray<FStableHorseOffer>& Stock, const FStableMountRoster& Roster,
                  int32 Day, int64 Balance, bool Pending);
    void SetRoster(const FStableMountRoster& Roster);
    void ResetSelection();

private:
    struct FCard
    {
        FStableHorseOffer Lot;
        bool Sold=false;
        FString Name;
        FSlateBrush Portrait, SoftPortrait;
        TSharedPtr<SHorseMarketPlate> Plate;
        TSharedPtr<SBox> DetailClip;
        TSharedPtr<SVerticalBox> Detail;
        float Reveal=0.f;
        TSharedPtr<SButton> Button, BuyButton;
        TSharedPtr<STextBlock> Status;
    };
    void Reflow();
    void BuildCard(FCard& Card);
    void RefreshSelection();
    FReply Select(FGuid Id);
    FReply Details(FGuid Id);
    virtual void Tick(const FGeometry& Geometry, double Time, float Delta) override;

    TSharedPtr<SVerticalBox> Grid;
    TSharedPtr<SScrollBox> Scroll;
    TSharedPtr<STextBlock> Date;
    TArray<TUniquePtr<FCard>> Cards;
    TStrongObjectPtr<UTexture2D> Atlas, SoftAtlas;
    FGuid Selected, Deployed;
    bool bOwned=false;
    int32 MarketDay=INDEX_NONE, Columns=0;
    int64 Souls=0;
    bool bPending=false;
    FOpenHorse OnDetails;
    FSimpleDelegate OnSelect;

    friend class UHorseMarketCardsReviewCommandlet;
};
