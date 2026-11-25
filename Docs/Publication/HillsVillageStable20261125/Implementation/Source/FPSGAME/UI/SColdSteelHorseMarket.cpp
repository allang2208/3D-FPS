#include "SColdSteelHorseMarket.h"
#include "SHorseMarketPlate.h"
#include "ColdSteelHorsePortrait.h"
#include "ColdSteelMarketCardStyle.h"
#include "../Movement/StableHorseAppearance.h"
#include "ColdSteelUIStyle.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Brushes/SlateNoResource.h"
#include "Misc/Paths.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SUniformGridPanel.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
FText Txt(const FString& Value) { return FText::FromString(Value); }

TSharedRef<STextBlock> Label(const FString& Value, float Size, FLinearColor Tint, bool Bold=false)
{
    return SNew(STextBlock).Text(Txt(Value)).Font(ColdSteelUI::TextFont(Size,Bold)).ColorAndOpacity(Tint);
}

using ColdSteelMarketCard::CardFrame;
const FButtonStyle& AddHorseStyle()
{
    using namespace ColdSteelUI;
    static const FButtonStyle Style=[]
    {
        FButtonStyle Result=ButtonStyle();
        Result.SetNormal(RoundedBrush(Gray(31),5,HUDGoldDim,1)).SetNormalForeground(HUDGold);
        Result.SetHovered(RoundedBrush(Gray(48),5,HUDGold,1)).SetHoveredForeground(HUDGoldLight);
        Result.SetPressed(RoundedBrush(Gray(24),5,HUDGold,1)).SetPressedForeground(HUDGold);
        Result.SetDisabled(RoundedBrush(Gray(30),5,Border,1)).SetDisabledForeground(TextTertiary);
        return Result.SetNormalPadding(0).SetPressedPadding(0);
    }();
    return Style;
}
}

void SColdSteelHorseMarket::Construct(const FArguments& Args)
{
    using namespace ColdSteelUI;
    OnDetails=Args._OnDetails;
    bOwned=Args._Owned;
    OnSelect=Args._OnSelect;
    Atlas.Reset(ColdSteelHorsePortrait::LoadAtlas());
    SoftAtlas.Reset(ColdSteelHorsePortrait::LoadAtlas(true));

    static const FScrollBoxStyle MarketScroll=FScrollBoxStyle()
        .SetTopShadowBrush(FSlateNoResource()).SetBottomShadowBrush(FSlateNoResource());
    ChildSlot
    [
        SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight().Padding(4,0,4,8)
        [
            SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1)[SAssignNew(Date,STextBlock).Font(TextFont(12,true)).ColorAndOpacity(TextPrimary)]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SNew(SBox).Visibility(bOwned?EVisibility::Collapsed:EVisibility::Visible)[Label(TEXT("每日零时换马"),10,TextSecondary)]]
        ]
        +SVerticalBox::Slot().FillHeight(1)
        [
            SAssignNew(Scroll,SScrollBox).Style(&MarketScroll)
            .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::Always)
            .ScrollBarVisibility(EVisibility::Collapsed).ScrollBarPadding(0)
            .AnimateWheelScrolling(true).WheelScrollMultiplier(1.5f)
            +SScrollBox::Slot()[SAssignNew(Grid,SVerticalBox)]
        ]
    ];
    RefreshSelection();
}

void SColdSteelHorseMarket::Tick(const FGeometry& Geometry,double Time,float Delta)
{
    SCompoundWidget::Tick(Geometry,Time,Delta);
    // Work in the drawer's DPI-compensated coordinates.
    const int32 Wanted=Geometry.GetLocalSize().X>=590.f?2:1;
    if(Columns!=Wanted)
    {
        Columns=Wanted;
        Reflow();
    }
    for(auto& Card:Cards)
    {
        const bool Open=Card->Button->IsHovered() || Card->BuyButton->IsHovered() ||
            Card->Button->HasAnyUserFocus().Get(EFocusCause::Cleared)==EFocusCause::Navigation ||
            Card->BuyButton->HasAnyUserFocus().Get(EFocusCause::Cleared)==EFocusCause::Navigation;
        const float Next=FMath::Clamp(Card->Reveal+(Open?2.f:-2.f)*Delta,0.f,1.f);
        if(Next==Card->Reveal)continue;
        Card->Reveal=Next;
        const float Ease=Next*Next*(3.f-2.f*Next);
        Card->Plate->SetReveal(Ease);
        Card->DetailClip->SetHeightOverride(Ease*Card->Detail->GetDesiredSize().Y);
        Card->Detail->SetRenderOpacity(Ease);
    }
}

void SColdSteelHorseMarket::Reflow()
{
    Grid->ClearChildren();
    const int32 Count=FMath::Max(1,Columns);
    for(int32 I=0;I<Cards.Num();I+=Count)
    {
        const auto Row=SNew(SHorizontalBox);
        for(int32 J=0;J<Count;++J)
        {
            if(Cards.IsValidIndex(I+J))
                Row->AddSlot().FillWidth(1).VAlign(VAlign_Top).Padding(4)[Cards[I+J]->Button.ToSharedRef()];
            else
                Row->AddSlot().FillWidth(1).Padding(4)[SNew(SSpacer)];
        }
        Grid->AddSlot().AutoHeight()[Row];
    }
}

void SColdSteelHorseMarket::BuildCard(FCard& Card)
{
    using namespace ColdSteelUI;
    const FGuid Id=Card.Lot.Horse.HorseId;
    const auto Look=FStableHorseAppearance::FromId(Id);
    const auto Traits=Card.Lot.Horse.Traits();
    const auto Growth=FStableHorseTraits::Growth(Id);
    // The sheet is indexed by coat, marking family and contrasting coat. It illustrates
    // the family; the live animal keeps its individual marking position and hair geometry.
    ColdSteelHorsePortrait::SetImage(Card.Portrait,Atlas.Get(),Look);
    Card.SoftPortrait=Card.Portrait;
    Card.SoftPortrait.SetResourceObject(SoftAtlas.Get());
    const auto Facts=SNew(SUniformGridPanel).SlotPadding(FMargin(0,2,7,1));
    const TCHAR* Names[]={TEXT("力量"),TEXT("敏捷"),TEXT("智力"),TEXT("体质"),TEXT("精神"),TEXT("幸运")};
    const float Scores[]={Traits.Strength,Traits.Agility,Traits.Intelligence,Traits.Constitution,Traits.Spirit,Traits.Luck};
    const float Gains[]={Growth.Strength,Growth.Agility,Growth.Intelligence,Growth.Constitution,Growth.Spirit,Growth.Luck};
    for(int32 I=0;I<UE_ARRAY_COUNT(Names);++I)
    {
        Facts->AddSlot(I%3,I/3)
        [
            SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight()
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[Label(Names[I],10,TextSecondary)]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6,0,0,0)
                [Label(FString::SanitizeFloat(Scores[I],0),11,TextPrimary,true)]
            ]
            +SVerticalBox::Slot().AutoHeight()
            [Label(FString::Printf(TEXT("+%.1f / 级"),Gains[I]),10,TextSecondary)]
        ];
    }
    static const FSlateBrush Rule=RoundedBrush(Border,0);
    static const FSlateBrush NameRule=RoundedBrush(HUDGold,0,HUDGold,0);
    SAssignNew(Card.Button,SButton).ButtonStyle(&CardFrame(false)).HAlign(HAlign_Fill)
    .ContentPadding(FMargin(2)).OnClicked(this,&SColdSteelHorseMarket::Select,Id)
    [
        SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()
        [SAssignNew(Card.Plate,SHorseMarketPlate).Sharp(&Card.Portrait).Soft(&Card.SoftPortrait)]
        +SVerticalBox::Slot().AutoHeight().Padding(14,-16,14,9)
        [
            SNew(SVerticalBox)
            +SVerticalBox::Slot().AutoHeight()
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                [Label(Card.Name,20,TextPrimary,true)]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8,2,0,0)
                [Label(FString::Printf(TEXT("%d 级"),Card.Lot.Horse.Level),10,TextSecondary)]
            ]
            +SVerticalBox::Slot().AutoHeight().Padding(0,2,0,5)
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(.72f)[SNew(SBox).HeightOverride(1)[SNew(SImage).Image(&NameRule)]]
                +SHorizontalBox::Slot().FillWidth(.28f)[SNew(SSpacer)]
            ]
            +SVerticalBox::Slot().AutoHeight()
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Top)
                [
                    SNew(SVerticalBox)
                    +SVerticalBox::Slot().AutoHeight().Padding(0,3,0,2)[Label(Look.CoatDescription(),11,TextSecondary)]
                    +SVerticalBox::Slot().AutoHeight()
                    [
                        SAssignNew(Card.DetailClip,SBox).HeightOverride(0).VAlign(VAlign_Top)
                        .Clipping(EWidgetClipping::ClipToBounds).Visibility(EVisibility::HitTestInvisible)
                        [
                            SAssignNew(Card.Detail,SVerticalBox)
                            +SVerticalBox::Slot().AutoHeight().Padding(0,1,0,1)[Label(Look.HairDescription(),10,TextSecondary)]
                            +SVerticalBox::Slot().AutoHeight().Padding(0,1,0,2)[Facts]
                        ]
                    ]
                ]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Top).Padding(6,0,0,0)
                [
                    SNew(SBox).WidthOverride(32).HeightOverride(32)
                    [
                        SAssignNew(Card.BuyButton,SButton).ButtonStyle(&AddHorseStyle())
                        .ContentPadding(0).HAlign(HAlign_Center).VAlign(VAlign_Center)
                        .OnClicked(this,&SColdSteelHorseMarket::Details,Id)
                        [SNew(STextBlock).Text(FText::FromString(TEXT("+"))).Font(NumberFont(16,true))
                            .ColorAndOpacity(FSlateColor::UseForeground()).Justification(ETextJustify::Center)]
                    ]
                ]
            ]
            +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,5)[SNew(SBox).HeightOverride(1)[SNew(SImage).Image(&Rule)]]
            +SVerticalBox::Slot().AutoHeight()
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                [SAssignNew(Card.Status,STextBlock).Font(TextFont(10,true))]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                [SNew(STextBlock).Visibility(bOwned?EVisibility::Collapsed:EVisibility::Visible).Text(Txt(FString::FromInt(Card.Lot.Price))).Font(NumberFont(13,true)).ColorAndOpacity(HUDGoldLight)]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(4,0,0,0)
                [SNew(SBox).Visibility(bOwned?EVisibility::Collapsed:EVisibility::Visible)[Label(TEXT("灵魂"),11,HUDGoldLight)]]
            ]
        ]
    ];
    Card.Detail->SetRenderOpacity(0.f);
}

void SColdSteelHorseMarket::SetStock(const TArray<FStableHorseOffer>& Stock,const FStableMountRoster& Roster,
                                     int32 Day,int64 Balance,bool Pending)
{
    bool Changed=MarketDay!=Day || Cards.Num()!=Stock.Num();
    auto SaleRecord=[this,&Roster](FStableHorseOffer Lot)
    {
        // A horse purchased before the generation change keeps its original birth on today's sold card.
        const auto* Owned=bOwned?nullptr:Roster.Find(Lot.Horse.HorseId);
        if(Owned && Owned->BirthVersion!=Lot.Horse.BirthVersion)
        {
            Lot.Horse.BirthVersion=Owned->BirthVersion;
            Lot.Price=Lot.Horse.BirthPrice();
        }
        return Lot;
    };
    for(int32 I=0;!Changed && I<Cards.Num();++I)
    {
        const auto Lot=SaleRecord(Stock[I]);
        Changed=Cards[I]->Lot.Horse.HorseId!=Lot.Horse.HorseId || Cards[I]->Lot.Price!=Lot.Price ||
            Cards[I]->Lot.Horse.BirthVersion!=Lot.Horse.BirthVersion || Cards[I]->Lot.Horse.Level!=Lot.Horse.Level;
    }
    if(Changed)
    {
        bool SameRoster=bOwned && Cards.Num()==Stock.Num() && MarketDay==Day;
        for(int32 I=0;SameRoster && I<Cards.Num();++I)SameRoster=Cards[I]->Lot.Horse.HorseId==Stock[I].Horse.HorseId;
        const float PreviousOffset=Scroll->GetScrollOffset();
        Grid->ClearChildren();
        Cards.Reset();
        TMap<FString,int32> Names;
        for(const auto& Lot:Stock)++Names.FindOrAdd(SaleRecord(Lot).Horse.DisplayName());
        for(const auto& Lot:Stock)
        {
            auto& Card=*Cards.Add_GetRef(MakeUnique<FCard>());
            Card.Lot=SaleRecord(Lot);
            Card.Name=Card.Lot.Horse.DisplayName();
            if(Names.FindRef(Card.Name)>1)Card.Name+=TEXT(" · ")+Card.Lot.Horse.HorseId.ToString(EGuidFormats::Digits).Left(8);
            BuildCard(Card);
        }
        Reflow();
        if(SameRoster)Scroll->SetScrollOffset(PreviousOffset);else Scroll->ScrollToStart();
    }
    bool Refresh=Changed || (bOwned && Deployed!=Roster.Deployed) || Souls!=Balance || bPending!=Pending || !Selected.IsValid();
    Deployed=Roster.Deployed; MarketDay=Day; Souls=Balance; bPending=Pending;
    for(auto& Card:Cards)
    {
        const bool Sold=bOwned || Roster.Find(Card->Lot.Horse.HorseId)!=nullptr;
        Refresh|=Card->Sold!=Sold;
        Card->Sold=Sold;
    }
    if(!Refresh)return;
    if(!Cards.ContainsByPredicate([this](const auto& C){return C->Lot.Horse.HorseId==Selected;}))
    {
        const auto* First=Cards.FindByPredicate([](const auto& C){return !C->Sold;});
        Selected=First?(*First)->Lot.Horse.HorseId:Cards.IsEmpty()?FGuid():Cards[0]->Lot.Horse.HorseId;
    }
    Date->SetText(Txt(bOwned?FString::Printf(TEXT("我的马匹  ·  %d 匹"),Cards.Num()):
        Cards.IsEmpty()?TEXT("正在等候马匹名册"):FString::Printf(TEXT("第 %d 天   ·   在售名册"),Day+1)));
    RefreshSelection();
}

void SColdSteelHorseMarket::SetRoster(const FStableMountRoster& Roster)
{
    TArray<FStableHorseOffer> Entries;
    Entries.Reserve(Roster.Horses.Num());
    // Cards only display identity, birth traits and level. Full inventory records stay in the detail model.
    for(const auto& Horse:Roster.Horses)
    {
        auto& Card=Entries.AddDefaulted_GetRef().Horse;
        Card.HorseId=Horse.HorseId;Card.BirthVersion=Horse.BirthVersion;Card.Level=Horse.Level;
    }
    SetStock(Entries,Roster,0,0,false);
}

void SColdSteelHorseMarket::ResetSelection()
{
    Selected.Invalidate();
    Scroll->ScrollToStart();
}

FReply SColdSteelHorseMarket::Select(FGuid Id)
{
    if(bOwned)return Details(Id);
    Selected=Id;
    OnSelect.ExecuteIfBound();
    RefreshSelection();
    return FReply::Handled();
}

void SColdSteelHorseMarket::RefreshSelection()
{
    for(auto& Card:Cards)
    {
        const bool IsSelected=Card->Lot.Horse.HorseId==Selected;
        const bool Affordable=Souls>=Card->Lot.Price;
        Card->Button->SetButtonStyle(&CardFrame(IsSelected));
        FString Status=IsSelected?TEXT("已选中"):TEXT("在售");
        if(bOwned)Status=Deployed==Card->Lot.Horse.HorseId?TEXT("出战中"):TEXT("已拥有");
        else if(Card->Sold)Status=TEXT("已购入");
        else if(bPending)Status=TEXT("交易处理中");
        else if(!Affordable)Status=FString::Printf(TEXT("还差 %lld 灵魂"),int64(Card->Lot.Price)-Souls);
        const FText Hint=Txt(FString::Printf(TEXT("查看%s的属性与装备"),*Card->Name));
        Card->BuyButton->SetToolTipText(Hint);
#if WITH_ACCESSIBILITY
        Card->BuyButton->SetAccessibleBehavior(EAccessibleBehavior::Custom,Hint);
#endif
        Card->Status->SetText(Txt(Status));
        Card->Status->SetColorAndOpacity(IsSelected?ColdSteelUI::HUDGoldLight:ColdSteelUI::TextSecondary);
    }
}

FReply SColdSteelHorseMarket::Details(FGuid Id)
{
    const auto* Card=Cards.FindByPredicate([Id](const auto& Entry){return Entry->Lot.Horse.HorseId==Id;});
    if(Card)
    {
        Selected=Id;
        RefreshSelection();
        OnDetails.ExecuteIfBound(Id);
    }
    return FReply::Handled();
}
