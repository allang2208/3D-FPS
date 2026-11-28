#include "SColdSteelHorseMarket.h"
#include "ColdSteelScrollBar.h"
#include "ColdSteelTextToolTip.h"
#include "SHorseMarketPlate.h"
#include "ColdSteelHorsePortrait.h"
#include "ColdSteelMarketCardStyle.h"
#include "ColdSteelInventoryTypes.h"
#include "../Movement/StableHorseAppearance.h"
#include "../Movement/StableHorseGear.h"
#include "../Movement/StableHorseAffixes.h"
#include "ColdSteelUIStyle.h"
#include "Engine/Texture2D.h"
#include "ImageUtils.h"
#include "Misc/Paths.h"
#include "Brushes/SlateNoResource.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/Layout/SUniformGridPanel.h"
#include "Widgets/Layout/SWrapBox.h"
#include "Widgets/Notifications/SProgressBar.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
FText Txt(const FString& Value) { return FText::FromString(Value); }

TSharedRef<STextBlock> Label(const FString& Value, float Size, FLinearColor Tint, bool Bold=false)
{
    return SNew(STextBlock).Text(Txt(Value)).Font(ColdSteelUI::TextFont(Size,Bold)).ColorAndOpacity(Tint);
}

TSharedRef<STextBlock> NumLabel(const FString& Value, float Size, FLinearColor Tint, bool Bold=false)
{
    return SNew(STextBlock).Text(Txt(Value)).Font(ColdSteelUI::NumberFont(Size,Bold)).ColorAndOpacity(Tint);
}

using ColdSteelMarketCard::CardFrame;
using ColdSteelMarketCard::PurchaseStyle;
using ColdSteelMarketCard::SecondaryActionStyle;

const FProgressBarStyle& MiniBarStyle()
{
    static const FProgressBarStyle Style=[]
    {
        FProgressBarStyle S;
        S.SetBackgroundImage(ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(255,18),1.5f,FLinearColor::Transparent,0));
        S.SetFillImage(ColdSteelUI::RoundedBrush(FLinearColor::White,1.5f,FLinearColor::Transparent,0));
        return S;
    }();
    return Style;
}

const FSlateBrush& PillDarkBrush()
{
    static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(15,212),4,FLinearColor(222.f/255.f,222.f/255.f,222.f/255.f,.24f),1);
    return B;
}
const FSlateBrush& PillGoldBrush()
{
    static const FSlateBrush B=ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor(26,21,14,228)),4,ColdSteelUI::HUDGold,1);
    return B;
}
const FSlateBrush& PillDangerBrush()
{
    static const FSlateBrush B=ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor(96,30,39,224)),4,ColdSteelUI::Danger,1);
    return B;
}
const FSlateBrush& PillMutedBrush()
{
    static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(24,218),4,ColdSteelUI::Border,1);
    return B;
}

const FSlateBrush& StatNormalBrush()
{
    static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(255,9),4,ColdSteelUI::Gray(222,22),1);
    return B;
}
const FSlateBrush& StatHighBrush()
{
    static const FSlateBrush B=ColdSteelUI::RoundedBrush(FLinearColor(ColdSteelUI::HUDGold.R,ColdSteelUI::HUDGold.G,ColdSteelUI::HUDGold.B,.11f),4,
        FLinearColor(ColdSteelUI::HUDGold.R,ColdSteelUI::HUDGold.G,ColdSteelUI::HUDGold.B,.42f),1);
    return B;
}

FString StandoutTag(const FStableHorseTraits& Traits)
{
    const TCHAR* Prefixes[]={TEXT("骁勇 · 力"),TEXT("疾风 · 敏"),TEXT("灵驹 · 智"),TEXT("坚韧 · 体"),TEXT("精沛 · 精"),TEXT("福驹 · 运")};
    const float Values[]={Traits.Strength,Traits.Agility,Traits.Intelligence,Traits.Constitution,Traits.Spirit,Traits.Luck};
    int32 Best=0;
    for(int32 I=1;I<6;++I)if(Values[I]>Values[Best])Best=I;
    return FString::Printf(TEXT("%s%.0f"),Prefixes[Best],Values[Best]);
}

TSharedRef<SWidget> BuildTackPips(const FStableMountRecord& Horse)
{
    using namespace ColdSteelUI;
    static const FSlateBrush EmptyPip=RoundedBrush(Gray(255,24),1.5f,Gray(255,55),1);
    static const FSlateBrush GoldPip=RoundedBrush(HUDGoldLight,1.5f,HUDGoldLight,0);
    static const FSlateBrush FinePip=RoundedBrush(MountStamina,1.5f,MountStamina,0);

    auto Row=SNew(SHorizontalBox)
        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,5,0)
        [Label(TEXT("马具"),9.5f,TextSecondary)];
    int32 Count=0;
    for(int32 Slot=0;Slot<StableHorseGear::Count;++Slot)
    {
        const auto* Item=StableHorseGear::At(Horse,Slot);
        if(Item)++Count;
        const FSlateBrush* PipBrush=&EmptyPip;
        if(Item)
        {
            const FString Rarity=ColdSteelInventory::Text(*Item,TEXT("rarity"));
            PipBrush=(Rarity==TEXT("rare") || Rarity==TEXT("epic") || Rarity==TEXT("legendary"))?&GoldPip:&FinePip;
        }
        Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(1.5f,0)
        [SNew(SBox).WidthOverride(6.5f).HeightOverride(6.5f)[SNew(SImage).Image(PipBrush)]];
    }
    Row->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(5,0,0,0)
    [NumLabel(FString::Printf(TEXT("%d/%d"),Count,StableHorseGear::Count),9.5f,Count>0?HUDGoldLight:TextSecondary,true)];

    return SNew(SBorder).BorderImage(&PillDarkBrush()).Padding(FMargin(7,2.5f))[Row];
}
}

void SColdSteelHorseMarket::Construct(const FArguments& Args)
{
    using namespace ColdSteelUI;
    OnDetails=Args._OnDetails;
    OnDeploy=Args._OnDeploy;
    OnCall=Args._OnCall;
    bOwned=Args._Owned;
    OnSelect=Args._OnSelect;
    Atlas.Reset(ColdSteelHorsePortrait::LoadAtlas());
    SoftAtlas.Reset(ColdSteelHorsePortrait::LoadAtlas(true));

    static const FScrollBoxStyle MarketScroll=FScrollBoxStyle()
        .SetTopShadowBrush(FSlateNoResource()).SetBottomShadowBrush(FSlateNoResource());
    static const FSlateBrush BannerBrush=RoundedBrush(FLinearColor::FromSRGBColor(FColor(34,30,24,230)),6,
        FLinearColor(HUDGold.R,HUDGold.G,HUDGold.B,.44f),1);

    ChildSlot
    [
        SNew(SVerticalBox)
        // Active deployed mount summary banner (owned roster only)
        +SVerticalBox::Slot().AutoHeight().Padding(4,0,4,8)
        [
            SAssignNew(ActiveBannerHost,SBox).Visibility(EVisibility::Collapsed)
            [
                SNew(SBorder).BorderImage(&BannerBrush).Padding(FMargin(12,8))
                [
                    SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,10,0)
                    [SNew(SBorder).BorderImage(&PillGoldBrush()).Padding(FMargin(7,2.5f))[Label(TEXT("★ 当前出战"),10,HUDGoldLight,true)]]
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                    [
                        SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()[SAssignNew(ActiveBannerName,STextBlock).Font(TextFont(13,true)).ColorAndOpacity(TextPrimary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                        +SVerticalBox::Slot().AutoHeight().Padding(0,2,0,0)[SAssignNew(ActiveBannerMeta,STextBlock).Font(TextFont(10)).ColorAndOpacity(TextSecondary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                    ]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8,0,0,0)
                    [
                        SAssignNew(ActiveBannerDetailBtn,SButton).ButtonStyle(&SecondaryActionStyle()).ContentPadding(FMargin(10,5))
                        .OnClicked_Lambda([this]{return Deployed.IsValid()?Details(Deployed):FReply::Handled();})
                        [Label(TEXT("检视与配装 ›"),10.5f,TextPrimary,true)]
                    ]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6,0,0,0)
                    [
                        SAssignNew(ActiveBannerCallBtn,SButton).ButtonStyle(&PurchaseStyle()).ContentPadding(FMargin(10,5))
                        .Visibility(OnCall.IsBound()?EVisibility::Visible:EVisibility::Collapsed)
                        .OnClicked(this,&SColdSteelHorseMarket::QuickCall)
                        [Label(TEXT("召唤 (X)"),10.5f,HUDGoldLight,true)]
                    ]
                ]
            ]
        ]
        // Top toolbar header
        +SVerticalBox::Slot().AutoHeight().Padding(4,0,4,8)
        [
            SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
            [SAssignNew(Date,STextBlock).Font(TextFont(12.5f,true)).ColorAndOpacity(TextPrimary)]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [SNew(SBox).Visibility(bOwned?EVisibility::Collapsed:EVisibility::Visible)[Label(TEXT("每日零时换马"),10,TextSecondary)]]
        ]
        +SVerticalBox::Slot().FillHeight(1)
        [
            ColdSteelUI::ApplyGoldScroll(
                SAssignNew(Scroll,SScrollBox).Style(&MarketScroll)
                .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::Always)
                .AnimateWheelScrolling(true).WheelScrollMultiplier(1.5f)
                +SScrollBox::Slot()[SAssignNew(Grid,SVerticalBox)],
                FVector2D(5.5f,5.5f),FMargin(4,0,0,0),true)
        ]
    ];
    RefreshSelection();
}

void SColdSteelHorseMarket::Tick(const FGeometry& Geometry,double Time,float Delta)
{
    SCompoundWidget::Tick(Geometry,Time,Delta);
    const float LocalW=Geometry.GetLocalSize().X;
    const int32 Wanted=(bOwned && LocalW>=1120.f)?3:(LocalW>=590.f?2:1);
    if(Columns!=Wanted)
    {
        Columns=Wanted;
        Reflow();
    }
    for(auto& Card:Cards)
    {
        const bool Hovered=Card->Button->IsHovered() ||
            (Card->BuyButton && Card->BuyButton->IsHovered()) ||
            (Card->DeployButton && Card->DeployButton->IsHovered()) ||
            Card->Button->HasAnyUserFocus().Get(EFocusCause::Cleared)==EFocusCause::Navigation ||
            (Card->BuyButton && Card->BuyButton->HasAnyUserFocus().Get(EFocusCause::Cleared)==EFocusCause::Navigation);
        const float Next=FMath::Clamp(Card->Reveal+(Hovered?3.2f:-3.2f)*Delta,0.f,1.f);
        if(FMath::IsNearlyEqual(Next,Card->Reveal,.0005f))continue;
        Card->Reveal=Next;
        const float Ease=Next*Next*(3.f-2.f*Next);
        // Zero layout shift: hover zooms portrait and brightens in-place growth readouts only.
        Card->Plate->SetReveal(Ease);
        for(int32 I=0;I<Card->GrowthLabels.Num();++I)
        {
            const bool High=Card->HighTraits.IsValidIndex(I) && Card->HighTraits[I];
            const FLinearColor Rest=High?ColdSteelUI::HUDGold:ColdSteelUI::TextTertiary;
            const FLinearColor Lit=High?ColdSteelUI::HUDGoldLight:ColdSteelUI::Success;
            Card->GrowthLabels[I]->SetColorAndOpacity(FMath::Lerp(Rest,Lit,Ease));
        }
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
                Row->AddSlot().FillWidth(1).VAlign(VAlign_Fill).Padding(5)[Cards[I+J]->Button.ToSharedRef()];
            else
                Row->AddSlot().FillWidth(1).Padding(5)[SNew(SSpacer)];
        }
        Grid->AddSlot().AutoHeight()[Row];
    }
}

const FSlateBrush* SColdSteelHorseMarket::AffixBrushFor(const FString& Key)
{
    if(const auto* Existing=AffixBrushes.Find(Key))return Existing->Get();
    UTexture2D* Tex=FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelData/Icons/HorseAffixes")/(Key+TEXT(".png")));
    if(Tex)AffixIcons.Add(Key,TStrongObjectPtr<UTexture2D>(Tex));
    TSharedPtr<FSlateBrush> Brush=MakeShared<FSlateBrush>();
    Brush->SetResourceObject(Tex);
    Brush->DrawAs=ESlateBrushDrawType::Image;
    Brush->SetImageSize(FVector2D(15,15));
    return AffixBrushes.Add(Key,Brush).Get();
}

void SColdSteelHorseMarket::BuildCard(FCard& Card)
{
    using namespace ColdSteelUI;
    const FStableMountRecord& Horse=Card.Lot.Horse;
    const FGuid Id=Horse.HorseId;
    const auto Look=FStableHorseAppearance::FromId(Id);
    const auto Traits=Horse.Traits();
    const auto Growth=FStableHorseTraits::EffectiveGrowth(Id);
    const auto Affix=StableHorseAffixes::Bonuses(Id);
    const auto AffixList=StableHorseAffixes::Roll(Id);
    const auto TB=StableHorseGear::Bonuses(Horse);
    ColdSteelHorsePortrait::SetImage(Card.Portrait,Atlas.Get(),Look);
    Card.SoftPortrait=Card.Portrait;
    Card.SoftPortrait.SetResourceObject(SoftAtlas.Get());

    const float HighThreshold=12.f+FMath::Max(0,Horse.Level-1)*.75f;
    const float ScaleCap=FMath::Max(14.f,14.f+FMath::Max(0,Horse.Level-1)*1.0f);
    const TCHAR* Names[]={TEXT("力量"),TEXT("敏捷"),TEXT("智力"),TEXT("体质"),TEXT("精神"),TEXT("幸运")};
    const float Scores[]={Traits.Strength,Traits.Agility,Traits.Intelligence,Traits.Constitution,Traits.Spirit,Traits.Luck};
    const float Gains[]={Growth.Strength,Growth.Agility,Growth.Intelligence,Growth.Constitution,Growth.Spirit,Growth.Luck};

    Card.GrowthLabels.Reset();
    Card.HighTraits.Reset();
    const auto Facts=SNew(SUniformGridPanel).SlotPadding(FMargin(2.5f,2.5f));
    for(int32 I=0;I<UE_ARRAY_COUNT(Names);++I)
    {
        const bool High=Scores[I]>=HighThreshold;
        Card.HighTraits.Add(High);
        TSharedPtr<STextBlock> GrowText;
        const float Pct=FMath::Clamp(Scores[I]/ScaleCap,0.f,1.f);
        Facts->AddSlot(I%3,I/3)
        [
            SNew(SBorder).BorderImage(High?&StatHighBrush():&StatNormalBrush()).Padding(FMargin(6,4,6,5))
            [
                SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()
                [
                    SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0,0,3,0)
                    [Label(Names[I],9.5f,High?FLinearColor::FromSRGBColor(FColor(220,202,162)):TextTertiary)]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                    [NumLabel(FString::SanitizeFloat(FMath::RoundToFloat(Scores[I]*10.f)/10.f,0),11.5f,High?HUDGoldLight:TextPrimary,true)]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(3,0,0,0)
                    [SAssignNew(GrowText,STextBlock).Text(Txt(TEXT("+")+FString::SanitizeFloat(FMath::RoundToFloat(Gains[I]*100.f)/100.f,1)))
                        .Font(NumberFont(9.f)).ColorAndOpacity(High?HUDGold:TextTertiary)]
                ]
                +SVerticalBox::Slot().AutoHeight().Padding(0,3.5f,0,0)
                [
                    SNew(SBox).HeightOverride(2.5f)
                    [
                        SNew(SProgressBar).Style(&MiniBarStyle()).Percent(Pct)
                        .BarFillStyle(EProgressBarFillStyle::Scale).BorderPadding(FVector2D::ZeroVector)
                        .FillColorAndOpacity(High?HUDGold:FLinearColor(.78f,.80f,.84f,.72f))
                    ]
                ]
            ]
        ];
        Card.GrowthLabels.Add(GrowText);
    }

    static const FSlateBrush Rule=RoundedBrush(FLinearColor(222.f/255.f,222.f/255.f,222.f/255.f,.10f),0);
    static const FSlateBrush StripBrush=RoundedBrush(Gray(13,185),4,Gray(222,18),1);
    const FString CoatSummary=Look.CoatDescription()+TEXT(" · ")+Look.HairDescription();

    const float MaxHP=FMath::Max(1.f,Horse.MaxHealth>1.f?Horse.MaxHealth:(Traits.HealthLimit()*Affix.HealthMultiplier+TB.MaxHealthAdd));
    const float MaxSt=FMath::Max(1.f,Horse.MaxStamina>1.f?Horse.MaxStamina:(Traits.StaminaLimit()*Affix.StaminaMultiplier+TB.MaxStaminaAdd));
    const float EffCanterMs=Traits.CanterSpeed()*Affix.BaseMoveMultiplier*Affix.CanterSpeedMultiplier*(1.f+TB.SpeedBonus)/100.f;
    const float EffTurnDeg=88.f*Traits.TurnScale()*Affix.TurnMultiplier*(1.f+TB.TurnBonus);
    const float CurHP=bOwned?FMath::Clamp(Horse.Health,0.f,MaxHP):MaxHP;
    const float CurSt=bOwned?FMath::Clamp(Horse.Stamina,0.f,MaxSt):MaxSt;
    const bool bInjured=bOwned && CurHP<MaxHP*.75f;

    // Top-right badge: standout trait for Market, 4-pip tack readiness for Owned.
    TSharedRef<SWidget> TopRightWidget=bOwned
        ? BuildTackPips(Horse)
        : StaticCastSharedRef<SWidget>(SNew(SBorder).BorderImage(&PillGoldBrush()).Padding(FMargin(7,2.5f))
            [Label(StandoutTag(Traits),9.5f,HUDGoldLight,true)]);

    // Card body vertical stack
    auto BodyStack=SNew(SVerticalBox);

    // Owned cards: dual HP / Stamina micro-bars
    if(bOwned)
    {
        BodyStack->AddSlot().AutoHeight().Padding(0,0,0,7)
        [
            SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).Padding(0,0,5,0)
            [
                SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()
                [
                    SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("生命"),9.5f,TextTertiary)]
                    +SHorizontalBox::Slot().AutoWidth()[NumLabel(FString::Printf(TEXT("%.0f/%.0f"),CurHP,MaxHP),9.5f,bInjured?Danger:TextSecondary,true)]
                ]
                +SVerticalBox::Slot().AutoHeight().Padding(0,2.5f,0,0)
                [
                    SNew(SBox).HeightOverride(3.5f)
                    [SNew(SProgressBar).Style(&MiniBarStyle()).Percent(CurHP/MaxHP).BarFillStyle(EProgressBarFillStyle::Scale)
                        .BorderPadding(FVector2D::ZeroVector).FillColorAndOpacity(Health)]
                ]
            ]
            +SHorizontalBox::Slot().FillWidth(1).Padding(5,0,0,0)
            [
                SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()
                [
                    SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().FillWidth(1)[Label(TEXT("体力"),9.5f,TextTertiary)]
                    +SHorizontalBox::Slot().AutoWidth()[NumLabel(FString::Printf(TEXT("%.0f/%.0f"),CurSt,MaxSt),9.5f,TextSecondary,true)]
                ]
                +SVerticalBox::Slot().AutoHeight().Padding(0,2.5f,0,0)
                [
                    SNew(SBox).HeightOverride(3.5f)
                    [SNew(SProgressBar).Style(&MiniBarStyle()).Percent(CurSt/MaxSt).BarFillStyle(EProgressBarFillStyle::Scale)
                        .BorderPadding(FVector2D::ZeroVector).FillColorAndOpacity(MountStamina)]
                ]
            ]
        ];
    }

    // 6-stat bar-backed matrix (always visible, zero reflow!)
    BodyStack->AddSlot().AutoHeight().Padding(0,0,0,6)
    [
        SAssignNew(Card.DetailClip,SBox)[SAssignNew(Card.Detail,SVerticalBox)+SVerticalBox::Slot().AutoHeight()[Facts]]
    ];

    // Compact Affix pills row (shows all 1~4 affixes with generated icon + tier tint + tooltip)
    if(!AffixList.IsEmpty())
    {
        static const FSlateBrush SpecialPill=RoundedBrush(FLinearColor::FromSRGBColor(FColor(44,34,18,236)),4,HUDGold,1.1f);
        static const FSlateBrush PosPill=RoundedBrush(FLinearColor::FromSRGBColor(FColor(18,36,30,224)),4,FLinearColor(.38f,.80f,.58f,.68f),1.f);
        static const FSlateBrush NegPill=RoundedBrush(FLinearColor::FromSRGBColor(FColor(44,20,24,228)),4,FLinearColor(.86f,.38f,.44f,.72f),1.f);
        auto PillRow=SNew(SWrapBox).UseAllottedSize(true).InnerSlotPadding(FVector2D(4.f,3.f));
        for(EStableHorseAffix A:AffixList)
        {
            const auto& Def=StableHorseAffixes::Definition(A);
            const bool bSpec=Def.Tier==EStableHorseAffixTier::Special;
            const bool bPos=Def.Tier==EStableHorseAffixTier::Positive||Def.Tier==EStableHorseAffixTier::PositiveMajor;
            const FSlateBrush* PillBg=bSpec?&SpecialPill:(bPos?&PosPill:&NegPill);
            const FLinearColor PillTextCol=bSpec?HUDGoldLight:(bPos?FLinearColor(.78f,.96f,.86f,1.f):FLinearColor(.98f,.76f,.78f,1.f));
            const FSlateBrush* IconBrush=AffixBrushFor(FString(Def.Id));
            auto Pill=SNew(SBorder).BorderImage(PillBg).Padding(FMargin(4.f,2.f,6.f,2.f))
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,4,0)
                [SNew(SBox).WidthOverride(15).HeightOverride(15)[SNew(SImage).Image(IconBrush)]]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                [Label(bSpec?(FString(TEXT("★"))+Def.Name):FString(Def.Name),9.5f,PillTextCol,bSpec)]
            ];
            ColdSteelToolTip::Set(*Pill,Txt(FString::Printf(TEXT("%s\n%s"),Def.Name,Def.Description)));
            PillRow->AddSlot()[Pill];
        }
        BodyStack->AddSlot().AutoHeight().Padding(0,0,0,6)[PillRow];
    }

    // Performance summary strip
    BodyStack->AddSlot().AutoHeight().Padding(0,0,0,7)
    [
        SNew(SBorder).BorderImage(&StripBrush).Padding(FMargin(8,4))
        [
            SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth()[Label(bOwned?TEXT("极速 "):TEXT("生命 "),9.5f,TextTertiary)]
                +SHorizontalBox::Slot().AutoWidth()[NumLabel(bOwned?FString::Printf(TEXT("%.1f米/秒"),EffCanterMs):FString::Printf(TEXT("%.0f"),MaxHP),10.f,bOwned?HUDGoldLight:TextPrimary,true)]
            ]
            +SHorizontalBox::Slot().FillWidth(1).HAlign(HAlign_Center).VAlign(VAlign_Center)
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth()[Label(bOwned?TEXT("转向 "):TEXT("体力 "),9.5f,TextTertiary)]
                +SHorizontalBox::Slot().AutoWidth()[NumLabel(bOwned?FString::Printf(TEXT("%.0f°/秒"),EffTurnDeg):FString::Printf(TEXT("%.0f"),MaxSt),10.f,TextPrimary,true)]
            ]
            +SHorizontalBox::Slot().FillWidth(1).HAlign(HAlign_Right).VAlign(VAlign_Center)
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth()[Label(bOwned?TEXT("背包 "):TEXT("极速 "),9.5f,TextTertiary)]
                +SHorizontalBox::Slot().AutoWidth()[NumLabel(bOwned?FString::Printf(TEXT("%d排"),Horse.BagRows()):FString::Printf(TEXT("%.1f米/秒"),EffCanterMs),10.f,HUDGoldLight,true)]
            ]
        ]
    ];

    // Hairline rule + footer
    BodyStack->AddSlot().AutoHeight().Padding(0,0,0,7)[SNew(SBox).HeightOverride(1)[SNew(SImage).Image(&Rule)]];

    if(bOwned)
    {
        auto FooterRow=SNew(SHorizontalBox);
        FooterRow->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(0,0,6,0)
            [SAssignNew(Card.Status,STextBlock).Font(TextFont(10,true))];
        if(OnDeploy.IsBound())
        {
            FooterRow->AddSlot().FillWidth(1).Padding(0,0,6,0)
            [
                SAssignNew(Card.DeployButton,SButton).ButtonStyle(&PurchaseStyle())
                .ContentPadding(FMargin(8,5)).HAlign(HAlign_Center).VAlign(VAlign_Center)
                .OnClicked(this,&SColdSteelHorseMarket::QuickDeploy,Id)
                [SAssignNew(Card.DeployCaption,STextBlock).Text(Txt(TEXT("设为出战"))).Font(TextFont(10.5f,true)).ColorAndOpacity(HUDGoldLight)]
            ];
        }
        FooterRow->AddSlot().FillWidth(1)
        [
            SAssignNew(Card.BuyButton,SButton).ButtonStyle(&SecondaryActionStyle())
            .ContentPadding(FMargin(8,5)).HAlign(HAlign_Center).VAlign(VAlign_Center)
            .OnClicked(this,&SColdSteelHorseMarket::Details,Id)
            [SAssignNew(Card.BuyCaption,STextBlock).Text(Txt(TEXT("详情与马具 ›"))).Font(TextFont(10.5f,true)).ColorAndOpacity(TextPrimary)]
        ];
        BodyStack->AddSlot().AutoHeight()[FooterRow];
    }
    else
    {
        BodyStack->AddSlot().AutoHeight()
        [
            SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [NumLabel(FString::Printf(TEXT("✦ %d"),Card.Lot.Price),13.5f,HUDGoldLight,true)]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(3,1,8,0)
            [Label(TEXT("灵魂"),10,TextTertiary)]
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
            [SAssignNew(Card.Status,STextBlock).Font(TextFont(10,true)).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(6,0,0,0)
            [
                SAssignNew(Card.BuyButton,SButton).ButtonStyle(&SecondaryActionStyle())
                .ContentPadding(FMargin(10,4.5f)).HAlign(HAlign_Center).VAlign(VAlign_Center)
                .OnClicked(this,&SColdSteelHorseMarket::Details,Id)
                [SAssignNew(Card.BuyCaption,STextBlock).Text(Txt(TEXT("详情与马具 ›"))).Font(TextFont(10.5f,true)).ColorAndOpacity(TextPrimary)]
            ]
        ];
    }

    // Complete framed card with overlaid portrait header
    SAssignNew(Card.Button,SButton).ButtonStyle(&CardFrame(false)).HAlign(HAlign_Fill).VAlign(VAlign_Fill)
    .ContentPadding(FMargin(1)).OnClicked(this,&SColdSteelHorseMarket::Select,Id)
    [
        SNew(SVerticalBox)
        +SVerticalBox::Slot().AutoHeight()
        [
            SNew(SOverlay)
            +SOverlay::Slot()
            [SAssignNew(Card.Plate,SHorseMarketPlate).Sharp(&Card.Portrait).Soft(&Card.SoftPortrait).PreferredHeight(148.f).CornerRadius(5.f)]
            +SOverlay::Slot().VAlign(VAlign_Top).Padding(9,8)
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                [
                    SAssignNew(Card.TopLeftBadge,SBorder).BorderImage(&PillDarkBrush()).Padding(FMargin(7,2.5f))
                    [SAssignNew(Card.TopLeftPill,STextBlock).Font(TextFont(9.5f,true)).ColorAndOpacity(TextPrimary)]
                ]
                +SHorizontalBox::Slot().FillWidth(1)[SNew(SSpacer)]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[TopRightWidget]
            ]
            +SOverlay::Slot().VAlign(VAlign_Bottom).Padding(11,0,11,8)
            [
                SNew(SHorizontalBox)
                +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Bottom)
                [
                    SNew(SVerticalBox)
                    +SVerticalBox::Slot().AutoHeight()
                    [SNew(STextBlock).Text(Txt(Card.Name)).Font(TextFont(16.f,true)).ColorAndOpacity(FLinearColor(.95f,.95f,.96f,1.f))
                        .ShadowOffset(FVector2D(0,1.5f)).ShadowColorAndOpacity(FLinearColor(0,0,0,.85f)).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                    +SVerticalBox::Slot().AutoHeight().Padding(0,1,0,0)
                    [SNew(STextBlock).Text(Txt(CoatSummary)).Font(TextFont(9.5f)).ColorAndOpacity(FLinearColor(.78f,.78f,.80f,1.f))
                        .ShadowOffset(FVector2D(0,1.f)).ShadowColorAndOpacity(FLinearColor(0,0,0,.90f)).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]
                ]
                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom).Padding(6,0,0,0)
                [
                    SNew(SBox).Visibility(bInjured?EVisibility::HitTestInvisible:EVisibility::Collapsed)
                    [SNew(SBorder).BorderImage(&PillDangerBrush()).Padding(FMargin(6,2))[Label(TEXT("轻伤 · 需补血"),9.5f,FLinearColor(1.f,.85f,.88f,1.f),true)]]
                ]
            ]
        ]
        +SVerticalBox::Slot().AutoHeight().Padding(10,9,10,9)[BodyStack]
    ];
}

void SColdSteelHorseMarket::RefreshActiveBanner(const FStableMountRoster& Roster)
{
    if(!ActiveBannerHost)return;
    const auto* Active=(bOwned && Roster.Deployed.IsValid())?Roster.Find(Roster.Deployed):nullptr;
    if(!Active)
    {
        ActiveBannerHost->SetVisibility(EVisibility::Collapsed);
        return;
    }
    ActiveBannerHost->SetVisibility(EVisibility::Visible);
    const auto Traits=Active->Traits();
    const float MaxHP=FMath::Max(1.f,Active->MaxHealth>1.f?Active->MaxHealth:Traits.HealthLimit());
    const float MaxSt=FMath::Max(1.f,Active->MaxStamina>1.f?Active->MaxStamina:Traits.StaminaLimit());
    ActiveBannerName->SetText(Txt(FString::Printf(TEXT("%s  ·  Lv.%d"),*Active->DisplayName(),Active->Level)));
    ActiveBannerMeta->SetText(Txt(FString::Printf(TEXT("生命 %.0f/%.0f  ·  体力 %.0f/%.0f  ·  马具 %d/%d"),
        FMath::Clamp(Active->Health,0.f,MaxHP),MaxHP,FMath::Clamp(Active->Stamina,0.f,MaxSt),MaxSt,
        Active->Equipment.Num(),StableHorseGear::Count)));
}

void SColdSteelHorseMarket::SetStock(const TArray<FStableHorseOffer>& Stock,const FStableMountRoster& Roster,
                                     int32 Day,int64 Balance,bool Pending)
{
    bool Changed=MarketDay!=Day || Cards.Num()!=Stock.Num();
    auto SaleRecord=[this,&Roster](FStableHorseOffer Lot)
    {
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
        const auto& Old=Cards[I]->Lot.Horse;
        const auto& New=Lot.Horse;
        Changed=Old.HorseId!=New.HorseId || Cards[I]->Lot.Price!=Lot.Price ||
            Old.BirthVersion!=New.BirthVersion || Old.Level!=New.Level ||
            (bOwned && (Old.Equipment.Num()!=New.Equipment.Num() || Old.Experience!=New.Experience ||
                        !FMath::IsNearlyEqual(Old.Health,New.Health,1.f) || !FMath::IsNearlyEqual(Old.Stamina,New.Stamina,1.f)));
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
    RefreshActiveBanner(Roster);
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
        if(bOwned && Deployed.IsValid() && Cards.ContainsByPredicate([this](const auto& C){return C->Lot.Horse.HorseId==Deployed;}))
            Selected=Deployed;
        else
        {
            const auto* First=Cards.FindByPredicate([](const auto& C){return !C->Sold;});
            Selected=First?(*First)->Lot.Horse.HorseId:Cards.IsEmpty()?FGuid():Cards[0]->Lot.Horse.HorseId;
        }
    }
    int32 Available=0;
    for(const auto& C:Cards)if(!C->Sold)++Available;
    Date->SetText(Txt(bOwned?FString::Printf(TEXT("已拥有坐骑  %d 匹"),Cards.Num()):
        Cards.IsEmpty()?TEXT("正在等候马匹名册"):FString::Printf(TEXT("第 %d 天  ·  当前在售 %d / %d 匹"),Day+1,Available,Cards.Num())));
    RefreshSelection();
}

void SColdSteelHorseMarket::SetRoster(const FStableMountRoster& Roster)
{
    TArray<FStableHorseOffer> Entries;
    Entries.Reserve(Roster.Horses.Num());
    // Preserve full owned horse record (health, stamina, equipment, XP) for live roster cards.
    for(const auto& Horse:Roster.Horses)
    {
        auto& Offer=Entries.AddDefaulted_GetRef();
        Offer.Horse=Horse;
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
    if(Selected!=Id)
    {
        Selected=Id;
        RefreshSelection();
    }
    OnSelect.ExecuteIfBound();
    return FReply::Handled();
}

void SColdSteelHorseMarket::RefreshSelection()
{
    using namespace ColdSteelUI;
    for(auto& Card:Cards)
    {
        const FGuid Id=Card->Lot.Horse.HorseId;
        const bool IsDeployed=bOwned && Deployed==Id;
        const bool IsSelected=(Id==Selected);
        const bool Affordable=Souls>=Card->Lot.Price;
        Card->Button->SetButtonStyle(&CardFrame(IsSelected));
        if(Card->Plate)
        {
            Card->Plate->SetSelected(IsSelected);
            Card->Plate->SetMuted(!bOwned && Card->Sold);
        }

        // Top-left status/level pill
        if(Card->TopLeftPill && Card->TopLeftBadge)
        {
            if(bOwned)
            {
                Card->TopLeftPill->SetText(Txt(FString::Printf(TEXT("%s · Lv.%d"),IsDeployed?TEXT("★ 出战中"):TEXT("马棚待命"),Card->Lot.Horse.Level)));
                Card->TopLeftPill->SetColorAndOpacity(IsDeployed?HUDGoldLight:TextPrimary);
                Card->TopLeftBadge->SetBorderImage(IsDeployed?&PillGoldBrush():&PillDarkBrush());
            }
            else
            {
                Card->TopLeftPill->SetText(Txt(FString::Printf(TEXT("Lv.%d · %s"),Card->Lot.Horse.Level,Card->Sold?TEXT("已售出"):TEXT("在售"))));
                Card->TopLeftPill->SetColorAndOpacity(Card->Sold?TextSecondary:TextPrimary);
                Card->TopLeftBadge->SetBorderImage(Card->Sold?&PillMutedBrush():&PillDarkBrush());
            }
        }

        FString Status=IsSelected?TEXT("已选中"):TEXT("在售");
        FLinearColor StatusColor=IsSelected?HUDGoldLight:TextSecondary;
        if(bOwned)
        {
            Status=IsDeployed?TEXT("出战中"):TEXT("待命");
            StatusColor=IsDeployed?HUDGoldLight:TextTertiary;
        }
        else if(Card->Sold)
        {
            Status=TEXT("已购入");
            StatusColor=TextTertiary;
        }
        else if(bPending)
        {
            Status=TEXT("交易处理中");
            StatusColor=HUDGold;
        }
        else if(!Affordable)
        {
            Status=FString::Printf(TEXT("还差 %lld"),int64(Card->Lot.Price)-Souls);
            StatusColor=Danger;
        }

        const FText Hint=Txt(FString::Printf(TEXT("查看%s的详情与马具"),*Card->Name));
        if(Card->BuyButton)
        {
            ColdSteelToolTip::Set(*Card->BuyButton,Hint);
#if WITH_ACCESSIBILITY
            Card->BuyButton->SetAccessibleBehavior(EAccessibleBehavior::Custom,Hint);
#endif
            if(!bOwned)
            {
                Card->BuyButton->SetButtonStyle(IsSelected && !Card->Sold?&PurchaseStyle():&SecondaryActionStyle());
                if(Card->BuyCaption)
                {
                    Card->BuyCaption->SetText(Txt(Card->Sold?TEXT("✓ 已入栏"):TEXT("详情与马具 ›")));
                    Card->BuyCaption->SetColorAndOpacity(IsSelected && !Card->Sold?HUDGoldLight:TextPrimary);
                }
            }
            else
            {
                Card->BuyButton->SetButtonStyle(IsSelected?&PurchaseStyle():&SecondaryActionStyle());
                if(Card->BuyCaption)
                    Card->BuyCaption->SetColorAndOpacity(IsSelected?HUDGoldLight:TextPrimary);
            }
        }
        if(Card->DeployButton && Card->DeployCaption)
        {
            Card->DeployButton->SetButtonStyle(IsDeployed?&SecondaryActionStyle():&PurchaseStyle());
            Card->DeployCaption->SetText(Txt(IsDeployed?TEXT("取消出战"):TEXT("设为出战")));
            Card->DeployCaption->SetColorAndOpacity(IsDeployed?TextSecondary:HUDGoldLight);
        }
        Card->Status->SetText(Txt(Status));
        Card->Status->SetColorAndOpacity(StatusColor);
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

FReply SColdSteelHorseMarket::QuickDeploy(FGuid Id)
{
    OnDeploy.ExecuteIfBound(Id);
    return FReply::Handled();
}

FReply SColdSteelHorseMarket::QuickCall()
{
    OnCall.ExecuteIfBound();
    return FReply::Handled();
}
