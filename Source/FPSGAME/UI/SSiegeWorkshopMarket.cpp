#include "SSiegeWorkshopMarket.h"
#include "ColdSteelTextToolTip.h"
#include "ColdSteelMarketCardStyle.h"
#include "SHorseMarketPlate.h"
#include "../NPC/ChapelDialogueComponent.h"
#include "../WorldGeneration/VillageSiegeUpgrades.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Async/Async.h"
#include "Brushes/SlateNoResource.h"
#include "Misc/Paths.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScaleBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
constexpr float TabCaptionHeight=28.f;

FText Text(const FString& S) { return FText::FromString(S); }
const TCHAR* StatTitle(bool Stone,int32 Stat)
{
    using namespace VillageSiegeUpgrades;
    switch(Stat)
    {
    case Damage: return TEXT("伤害");
    case Reload: return TEXT("装填冷却");
    case Special: return Stone?TEXT("爆炸半径"):TEXT("护甲穿透");
    default: return TEXT("射程");
    }
}
FString StatValue(bool Stone,int32 Stat,int32 Level)
{
    using namespace VillageSiegeUpgrades;
    const double V=Value(Stone,EStat(Stat),Level);
    if(Stat==Reload)return FString::Printf(TEXT("%.2f 秒"),V);
    if(Stat==Reach || (Stone && Stat==Special))return FString::SanitizeFloat(V/100.,0)+TEXT(" 米");
    if(Stat==Special)return FString::Printf(TEXT("%d%%"),FMath::RoundToInt(V*100.));
    return FString::FromInt(FMath::RoundToInt(V));
}
}

void SSiegeWorkshopMarket::Construct(const FArguments& Args)
{
    using namespace ColdSteelUI;
    Conversation=Args._Conversation;
    for(int32 I=0;I<2;++I)
    {
        const TCHAR* Asset=I?TEXT("Ballista.jpg"):TEXT("Trebuchet.jpg");
        Portraits[I].Reset(FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelUI/SiegeWorkshop")/Asset));
        Images[I].SetResourceObject(Portraits[I].Get());
        Images[I].DrawAs=ESlateBrushDrawType::Image;
        Images[I].SetImageSize(FVector2D(672,322));
        Images[I].SetUVRegion(FBox2f(FVector2f::ZeroVector,FVector2f(1,1)));
    }
    OnBack=Args._OnBack;
    static const auto Panel=RoundedBrush(GlassFallback,PanelRadius,Border,1);
    static const auto ScrollStyle=FScrollBoxStyle()
        .SetTopShadowBrush(FSlateNoResource()).SetBottomShadowBrush(FSlateNoResource());
    auto OffersBox=SNew(SVerticalBox);
    for(int32 I=0;I<4;++I)
        OffersBox->AddSlot().AutoHeight().Padding(0,0,0,7)[MakeOffer(I)];

    SetClipping(EWidgetClipping::ClipToBounds);
    ChildSlot
    [
        SNew(SOverlay)
        +SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Fill).Padding(0,8,0,8)
        [SAssignNew(Drawer,SBox).WidthOverride_Lambda([this]{return FOptionalSize(DrawerWidth);})
         [SNew(SBorder).BorderImage(&Panel).Padding(FMargin(16,14))
          [SNew(SVerticalBox)
           +SVerticalBox::Slot().AutoHeight()
           [SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
            [SNew(STextBlock).Text(Text(TEXT("守备机械升级"))).Font(TextFont(20,true)).ColorAndOpacity(TextPrimary)]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [SNew(SButton).ButtonStyle(&ColdSteelMarketCard::PurchaseStyle()).ContentPadding(FMargin(10,5))
                .ToolTip(ColdSteelToolTip::Make(Text(TEXT("收回边栏，返回工匠对话"))))
                .OnClicked_Lambda([this]{RequestClose();return FReply::Handled();})
                [SNew(SHorizontalBox)
                 +SHorizontalBox::Slot().AutoWidth()[SNew(STextBlock).Text(Text(TEXT("收起"))).Font(TextFont(12,true)).ColorAndOpacity(TextPrimary)]
                 +SHorizontalBox::Slot().AutoWidth().Padding(7,0,0,0).VAlign(VAlign_Center)
                 [SNew(STextBlock).Text(Text(TEXT("Esc"))).Font(NumberFont(10)).ColorAndOpacity(HUDGoldLight)]]]]
           +SVerticalBox::Slot().AutoHeight().Padding(1,6,0,12)
           [SAssignNew(Balance,STextBlock).Font(TextFont(13,true)).ColorAndOpacity(HUDGoldLight)]
           +SVerticalBox::Slot().AutoHeight()
           [SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,4,0)[MakeTab(0)]
            +SHorizontalBox::Slot().FillWidth(1).Padding(4,0,0,0)[MakeTab(1)]]
           +SVerticalBox::Slot().AutoHeight().Padding(1,13,0,6)
           [SNew(STextBlock).Text(Text(TEXT("当前数值  →  下一级"))).Font(TextFont(11)).ColorAndOpacity(TextSecondary)]
           +SVerticalBox::Slot().FillHeight(1)
           [SAssignNew(OffersScroll,SScrollBox).Style(&ScrollStyle)
            .AllowOverscroll(EAllowOverscroll::No).ScrollBarThickness(FVector2D(4,4)).ScrollBarPadding(0)
            .ConsumeMouseWheel(EConsumeMouseWheel::Always).AnimateWheelScrolling(true)
            +SScrollBox::Slot()[OffersBox]]
           +SVerticalBox::Slot().AutoHeight().Padding(1,8,1,0)
           [SAssignNew(Feedback,STextBlock).Font(TextFont(12)).AutoWrapText(true)]
          ]]]
    ];
    Drawer->SetRenderOpacity(0.f);
    Drawer->SetVisibility(EVisibility::HitTestInvisible);
    Refresh();
}

TSharedRef<SWidget> SSiegeWorkshopMarket::MakeTab(int32 I)
{
    using namespace ColdSteelUI;
    static const auto Ring=RoundedBrush(Gray(38),7,HUDGoldDim,1);
    static const auto Dot=RoundedBrush(HUDGoldLight,4,HUDGoldLight,0);
    static const auto CaptionSurface=RoundedBrush(Gray(24,235),9);
    SAssignNew(Tabs[I],SButton).ButtonStyle(&ColdSteelMarketCard::CardFrame(I==Selected))
        .ContentPadding(2).HAlign(HAlign_Fill).VAlign(VAlign_Fill)
        .OnClicked_Lambda([this,I]{
            if(!bClosing && Selected!=I){Selected=I;OffersScroll->ScrollToStart();Refresh();}
            return FReply::Handled();
        })
        [SNew(SBox).Clipping(EWidgetClipping::ClipToBounds).Visibility(EVisibility::HitTestInvisible)
         .HeightOverride_Lambda([this]{return FOptionalSize(bCompactHeader?52.f:PhotoHeight);})
         [SNew(SOverlay)
          +SOverlay::Slot()
          [SNew(SBox).Visibility_Lambda([this]{return bCompactHeader?EVisibility::Collapsed:EVisibility::HitTestInvisible;})
           [SAssignNew(Plates[I],SHorseMarketPlate).Sharp(&Images[I])]]
          +SOverlay::Slot()
          [SNew(SScaleBox).Stretch(EStretch::ScaleToFit)
           .Visibility_Lambda([this]{return bCompactHeader?EVisibility::HitTestInvisible:EVisibility::Collapsed;})
           [SNew(SImage).Image(&Images[I])]]
          +SOverlay::Slot().VAlign(VAlign_Bottom).Padding(4,0)
          [SAssignNew(Captions[I],SBox).HeightOverride(TabCaptionHeight)
           [SNew(SBorder).BorderImage(&CaptionSurface).Padding(FMargin(9,0))
            [SNew(SHorizontalBox)
             +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
             [SNew(STextBlock).Text(Text(I?TEXT("弩炮"):TEXT("投石机"))).Font(TextFont(15,true)).ColorAndOpacity(TextPrimary)]
             +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
             [SNew(SBox).WidthOverride(14).HeightOverride(14)[SNew(SBorder).BorderImage(&Ring).Padding(4)
                 [SNew(SBorder).BorderImage(&Dot).Visibility_Lambda([this,I]{return I==Selected?EVisibility::HitTestInvisible:EVisibility::Hidden;})]]]]]]]];
    SetTabReveal(I,I==Selected?1.f:0.f);
    return Tabs[I].ToSharedRef();
}

void SSiegeWorkshopMarket::SetTabReveal(int32 I,float Fraction)
{
    Reveal[I]=Fraction;
    const float Ease=ColdSteelUI::EaseSmooth(Fraction);
    Plates[I]->SetReveal(Ease);
    Captions[I]->SetRenderTransform(FSlateRenderTransform(FVector2D(0,(1.f-Ease)*TabCaptionHeight)));
    Captions[I]->SetRenderOpacity(Ease);
}

TSharedRef<SWidget> SSiegeWorkshopMarket::MakeOffer(int32 Stat)
{
    using namespace ColdSteelUI;
    static const auto Surface=RoundedBrush(Gray(35),CardRadius,Border,1);
    FOffer& O=Offers[Stat];
    return SNew(SBorder).BorderImage(&Surface).Padding(FMargin(13,9))
        [SNew(SHorizontalBox)
         +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
         [SNew(SVerticalBox)
          +SVerticalBox::Slot().AutoHeight()[SNew(SHorizontalBox)
           +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[SAssignNew(O.Title,STextBlock).Font(TextFont(15,true)).ColorAndOpacity(TextPrimary)]
           +SHorizontalBox::Slot().AutoWidth().Padding(8,0,0,0).VAlign(VAlign_Center)
           [SAssignNew(O.Tier,STextBlock).Font(TextFont(11)).ColorAndOpacity(TextSecondary)]]
          +SVerticalBox::Slot().AutoHeight().Padding(0,4,0,0)[SNew(SHorizontalBox)
           +SHorizontalBox::Slot().AutoWidth()[SAssignNew(O.Current,STextBlock).Font(TextFont(13)).ColorAndOpacity(TextPrimary)]
           +SHorizontalBox::Slot().AutoWidth()[SAssignNew(O.Arrow,STextBlock).Text(Text(TEXT("  →  "))).Font(TextFont(13)).ColorAndOpacity(TextSecondary)]
           +SHorizontalBox::Slot().AutoWidth()[SAssignNew(O.Next,STextBlock).Font(TextFont(14,true)).ColorAndOpacity(HUDGoldLight)]]]
         +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(4,0,0,0)
         [SNew(SVerticalBox)
          +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)
          [SAssignNew(O.Full,STextBlock).Text(Text(TEXT("已满级"))).Font(TextFont(13,true)).ColorAndOpacity(TextSecondary)]
          +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)
          [SNew(SBox).MinDesiredWidth(76).HeightOverride(32)
            .Visibility_Lambda([this,Stat]{return Offers[Stat].Rank==VillageSiegeUpgrades::MaxRank?EVisibility::Collapsed:EVisibility::Visible;})
           [SAssignNew(O.Buy,SButton).ButtonStyle(&ColdSteelMarketCard::PurchaseStyle()).HAlign(HAlign_Center).VAlign(VAlign_Center)
            .ContentPadding(FMargin(10,0)).OnClicked_Lambda([this,Stat]{
               if(!bClosing && OpenFraction>=1.f)
                   if(auto* C=Conversation.Get())C->BuySiegeUpgrade(Selected*4+Stat,Offers[Stat].Rank);
               return FReply::Handled();
            })
            [SNew(STextBlock).Text(Text(TEXT("升级"))).Font(TextFont(12,true)).ColorAndOpacity(HUDGoldLight)]]]
          +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right).Padding(0,3,0,0)
          [SAssignNew(O.Cost,STextBlock).Font(TextFont(11)).ColorAndOpacity(TextSecondary)]]];
}

void SSiegeWorkshopMarket::Refresh()
{
    using namespace VillageSiegeUpgrades;
    using namespace ColdSteelUI;
    const auto* C=Conversation.Get();
    if(!C || bClosing)return;
    const bool Stone=Selected==0;
    const int64 Souls=C->WorkshopBalance();
    const uint16 Ranks=C->WorkshopRanks();
    Balance->SetText(Text(FString::Printf(TEXT("余额  %s 灵魂"),*FText::AsNumber(Souls).ToString())));
    const bool HasResult=C->IsPending() || !C->Message.IsEmpty();
    Feedback->SetText(Text(C->IsPending()?FString(TEXT("正在结算…")):HasResult?C->Message:FString(TEXT("升级对全村已建和新建的同类机械生效。"))));
    Feedback->SetColorAndOpacity(HasResult?HUDGoldLight:TextSecondary);
    for(int32 I=0;I<2;++I)Tabs[I]->SetButtonStyle(&ColdSteelMarketCard::CardFrame(Selected==I));
    for(int32 I=0;I<4;++I)
    {
        FOffer& O=Offers[I];
        O.Rank=Rank(Ranks,Selected*4+I);
        const bool Done=O.Rank==MaxRank;
        const int32 Cost=Price(O.Rank);
        O.Title->SetText(Text(StatTitle(Stone,I)));
        O.Tier->SetText(Text(FString::Printf(TEXT("%d/%d 级"),O.Rank,MaxRank)));
        O.Current->SetText(Text(StatValue(Stone,I,O.Rank)));
        O.Arrow->SetVisibility(Done?EVisibility::Collapsed:EVisibility::HitTestInvisible);
        O.Next->SetText(Done?FText::GetEmpty():Text(StatValue(Stone,I,O.Rank+1)));
        O.Cost->SetText(Text(Done?FString():Souls>=Cost?FString::Printf(TEXT("%d 灵魂"),Cost):
            FString::Printf(TEXT("%d 灵魂 · 缺 %lld"),Cost,static_cast<long long>(Cost-Souls))));
        O.Cost->SetVisibility(Done?EVisibility::Collapsed:EVisibility::HitTestInvisible);
        O.Full->SetVisibility(Done?EVisibility::HitTestInvisible:EVisibility::Collapsed);
        O.Buy->SetEnabled(!Done && Souls>=Cost && !C->IsPending());
    }
}

TSharedPtr<SWidget> SSiegeWorkshopMarket::FocusTarget() const
{
    return Tabs[Selected];
}

void SSiegeWorkshopMarket::RequestClose()
{
    if(bClosing)return;
    bClosing=true;
    Drawer->SetVisibility(EVisibility::HitTestInvisible);
}

void SSiegeWorkshopMarket::Tick(const FGeometry& G,double Time,float Delta)
{
    SCompoundWidget::Tick(G,Time,Delta);
    const FVector2D Size=G.GetLocalSize();
    const float PreviousWidth=DrawerWidth,PreviousFraction=OpenFraction;
    DrawerWidth=FMath::Max(1.f,FMath::Min(float(Size.X),FMath::Clamp(float(Size.X)*.38f,368.f,568.f)));
    bCompactHeader=Size.Y<620.f;
    PhotoHeight=FMath::Clamp((DrawerWidth-46.f)*.235f,52.f,116.f);
    const float Step=Delta*(bClosing?5.6f:4.5f);
    OpenFraction=FMath::Clamp(OpenFraction+(bClosing?-Step:Step),0.f,1.f);
    if(PreviousFraction!=OpenFraction || PreviousWidth!=DrawerWidth)
    {
        const float Ease=ColdSteelUI::EaseSmooth(OpenFraction);
        Drawer->SetRenderTransform(FSlateRenderTransform(FVector2D((1.f-Ease)*DrawerWidth,0)));
        Drawer->SetRenderOpacity(Ease);
        Drawer->SetVisibility(!bClosing && OpenFraction>=1.f?EVisibility::SelfHitTestInvisible:EVisibility::HitTestInvisible);
    }
    if(bClosing && OpenFraction<=0.f && !bReturnQueued)
    {
        bReturnQueued=true;
        // Restore the dialogue after Slate has finished iterating this frame's widget tree.
        const TWeakPtr<SSiegeWorkshopMarket> Weak=SharedThis(this);
        AsyncTask(ENamedThreads::GameThread,[Weak]{if(auto Self=Weak.Pin())Self->OnBack.ExecuteIfBound();});
    }
    for(int32 I=0;I<2;++I)
    {
        const bool Open=Selected==I || Tabs[I]->IsHovered() ||
            Tabs[I]->HasAnyUserFocus().Get(EFocusCause::Cleared)==EFocusCause::Navigation;
        const float Next=FMath::Clamp(Reveal[I]+Delta*(Open?5.f:-5.f),0.f,1.f);
        if(Next!=Reveal[I])SetTabReveal(I,Next);
    }
}
