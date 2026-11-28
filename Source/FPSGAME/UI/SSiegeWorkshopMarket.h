#pragma once

#include "Widgets/SCompoundWidget.h"
#include "Styling/SlateBrush.h"
#include "UObject/StrongObjectPtr.h"

class SHorseMarketPlate;
class SHorizontalBox;
class STextBlock;
class SButton;
class SBox;
class SBorder;
class SImage;
class SScrollBox;
class UChapelDialogueComponent;
class UTexture2D;

class SSiegeWorkshopMarket final : public SCompoundWidget
{
public:
SLATE_BEGIN_ARGS(SSiegeWorkshopMarket) : _Conversation(nullptr) {}
        SLATE_ARGUMENT(UChapelDialogueComponent*, Conversation)
        SLATE_EVENT(FSimpleDelegate, OnBack)
    SLATE_END_ARGS()
    void Construct(const FArguments& Args);
    void Refresh();
    void RequestClose();
    TSharedPtr<SWidget> FocusTarget() const;
private:
    friend struct FSiegeDrawerReview;
    struct FFacilityEntry
    {
        FString Id, Name, ShortName, Subtitle, ShortSub, PortraitFile;
        int32 UpgradeOffset=INDEX_NONE;
        bool bUnlocked=false;
        TStrongObjectPtr<UTexture2D> Portrait;
        FSlateBrush Brush;
        TSharedPtr<SHorseMarketPlate> Plate;
        TSharedPtr<SBorder> StateBadge, CompactFrame, CompactCornerTL, CompactCornerTR;
        TSharedPtr<STextBlock> StateLabel, TotalRankLabel, CompactMeta;
        TSharedPtr<SImage> PipImages[6];
        float Reveal=0.f;
    };
    struct FOffer
    {
        int32 Rank=0;
        int32 MaxRank=3;
        int32 BuiltTrackMax=0;
        TSharedPtr<SBox> RowBox;
        TSharedPtr<SBorder> CardFrame, FullBadge;
        TSharedPtr<STextBlock> Title, Tier, Current, Next, Arrow, Delta, DetailText, RequirementText, Cost, Full, BuyLabel;
        TSharedPtr<SHorizontalBox> LevelTrack;
        TArray<TSharedPtr<SBorder>> TrackSegments;
        TSharedPtr<SButton> Buy;
    };
    TWeakObjectPtr<UChapelDialogueComponent> Conversation;
    TArray<FFacilityEntry> Facilities;
    TArray<TSharedPtr<SButton>> Tabs;
    TSharedPtr<STextBlock> Balance, Feedback, ShareTag;
    TSharedPtr<SBorder> FeedbackFrame;
    TSharedPtr<SBox> SummaryHost, Drawer;
    TSharedPtr<STextBlock> SummaryKeys[4], SummaryValues[4];
    TSharedPtr<SScrollBox> FacilityScroll, OffersScroll;
    FSimpleDelegate OnBack;
    FOffer Offers[6];
    float DrawerWidth=490.f;
    float PlateHeight=116.f;
    bool bCompactHeader=false;
    float OpenFraction=0.f;
    bool bClosing=false;
    bool bReturnQueued=false;
    int32 Selected=0;
    TSharedRef<SWidget> MakeFacilityCard(int32 Index);
    TSharedRef<SWidget> MakeCompactTab(int32 Index);
    TSharedRef<SWidget> MakeOffer(int32 Stat);
    void SetTabReveal(int32 Index, float Fraction);
    float FacilityCardWidth(bool bCompact) const;
    virtual void Tick(const FGeometry& Geometry, double Time, float Delta) override;
};
