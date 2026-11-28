#include "SSiegeWorkshopMarket.h"
#include "ColdSteelTextToolTip.h"
#include "ColdSteelMarketCardStyle.h"
#include "ColdSteelScrollBar.h"
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
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/Layout/SSpacer.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/SOverlay.h"
#include "Widgets/Text/STextBlock.h"

namespace
{
FText Text(const FString& S) { return FText::FromString(S); }

// Cold Steel text hierarchy uses Slate points (px * 0.75) across NotoSansSC 400 / 600 / 700.
FSlateFontInfo Font(float Px, ColdSteelUI::ETextWeight Weight = ColdSteelUI::ETextWeight::Regular)
{
    return ColdSteelUI::TextFont(Px * .75f, Weight);
}

const TCHAR* StatTitle(VillageSiegeUpgrades::EFacility F, int32 Stat)
{
    using namespace VillageSiegeUpgrades;
    if(F==SmartTurret)
    {
        switch(Stat)
        {
        case TurretDamage:    return TEXT("火控增幅");
        case TurretFeed:      return TEXT("伺服供弹");
        case TurretOptics:    return TEXT("光学锁敌");
        case TurretWeakpoint: return TEXT("弱点校准");
        case TurretMagExpand: return TEXT("弹链扩容");
        default:              return TEXT("穿甲贯通");
        }
    }
    if(F==HotOil)
    {
        switch(Stat)
        {
        case OilDamage:     return TEXT("热油伤害");
        case OilRadius:     return TEXT("蔓延范围");
        case OilDuration:   return TEXT("持续时间");
        default:            return TEXT("灼烧层数");
        }
    }
    if(F==LightningSpire)
    {
        switch(Stat)
        {
        case SpireDamage:   return TEXT("雷击伤害");
        case SpireCooldown: return TEXT("聚能冷却");
        case SpireElectrify:return TEXT("感电层数");
        default:            return TEXT("引雷射程");
        }
    }
    const bool Stone=(F==Trebuchet);
    switch(Stat)
    {
    case Damage:  return Stone ? TEXT("中心伤害") : TEXT("伤害");
    case Reload:  return TEXT("装填冷却");
    case Special: return Stone ? TEXT("爆炸半径") : TEXT("护甲穿透");
    case 4:       return Stone ? TEXT("热油") : TEXT("射程");
    default:      return TEXT("射程");
    }
}

const TCHAR* SummaryKey(VillageSiegeUpgrades::EFacility F, int32 Stat)
{
    using namespace VillageSiegeUpgrades;
    if(F==SmartTurret)
    {
        switch(Stat)
        {
        case TurretDamage:    return TEXT("火力");
        case TurretFeed:      return TEXT("换弹/射速");
        case TurretOptics:    return TEXT("射程");
        default:              return TEXT("锁头");
        }
    }
    if(F==HotOil)
    {
        switch(Stat)
        {
        case OilDamage:     return TEXT("伤害");
        case OilRadius:     return TEXT("范围");
        case OilDuration:   return TEXT("时长");
        default:            return TEXT("灼烧");
        }
    }
    if(F==LightningSpire)
    {
        switch(Stat)
        {
        case SpireDamage:   return TEXT("伤害");
        case SpireCooldown: return TEXT("冷却");
        case SpireElectrify:return TEXT("感电");
        default:            return TEXT("射程");
        }
    }
    const bool Stone=(F==Trebuchet);
    switch(Stat)
    {
    case Damage:  return TEXT("伤害");
    case Reload:  return TEXT("装填");
    case Special: return Stone ? TEXT("爆炸") : TEXT("穿甲");
    default:      return TEXT("射程");
    }
}

FString StatValue(VillageSiegeUpgrades::EFacility F, int32 Stat, int32 Level, bool CompactSpace=false)
{
    using namespace VillageSiegeUpgrades;
    const double V=Value(F, Stat, Level);
    if(F==SmartTurret)
    {
        switch(Stat)
        {
        case TurretDamage:
            return FString::Printf(TEXT("%d%%"), FMath::RoundToInt(V*100.));
        case TurretFeed:
        {
            const int32 ReloadPct=FMath::RoundToInt(V*100.);
            const int32 RatePct=FMath::RoundToInt(TurretFireRateScale(Level)*100.);
            return CompactSpace
                ? FString::Printf(TEXT("-%d%%/+%d%%"), Level*3, Level*2)
                : FString::Printf(TEXT("换弹%d%%/射速%d%%"), ReloadPct, RatePct);
        }
        case TurretOptics:
        {
            const int32 SpreadReduction=Level*3;
            return CompactSpace
                ? FString::SanitizeFloat(V/100., 0)+TEXT("米")
                : FString::Printf(TEXT("%s 米 · 散布-%d%%"), *FString::SanitizeFloat(V/100., 0), SpreadReduction);
        }
        case TurretWeakpoint:
            return FString::Printf(TEXT("%d%%"), FMath::RoundToInt(V*100.));
        case TurretMagExpand:
            return FString::Printf(TEXT("+%d%%"), FMath::RoundToInt(V*100.));
        default:
            return CompactSpace
                ? FString::Printf(TEXT("+%d目标"), TurretBonusPierce(Level))
                : FString::Printf(TEXT("+%d 目标"), TurretBonusPierce(Level));
        }
    }
    if(F==HotOil)
    {
        switch(Stat)
        {
        case OilDamage:     return FString::FromInt(FMath::RoundToInt(V));
        case OilRadius:     return FString::SanitizeFloat(V/100., 0)+(CompactSpace ? TEXT("米") : TEXT(" 米"));
        case OilDuration:   return CompactSpace ? FString::Printf(TEXT("%d秒"), FMath::RoundToInt(V)) : FString::Printf(TEXT("%d 秒"), FMath::RoundToInt(V));
        default:            return CompactSpace ? FString::Printf(TEXT("%d层"), FMath::RoundToInt(V)) : FString::Printf(TEXT("%d 层"), FMath::RoundToInt(V));
        }
    }
    if(F==LightningSpire)
    {
        switch(Stat)
        {
        case SpireCooldown:  return CompactSpace ? FString::Printf(TEXT("%.2f秒"), V) : FString::Printf(TEXT("%.2f 秒"), V);
        case SpireElectrify: return CompactSpace ? FString::Printf(TEXT("%d层"), FMath::RoundToInt(V)) : FString::Printf(TEXT("%d 层"), FMath::RoundToInt(V));
        case SpireReach:     return FString::SanitizeFloat(V/100., 0)+(CompactSpace ? TEXT("米") : TEXT(" 米"));
        default:             return FString::FromInt(FMath::RoundToInt(V));
        }
    }
    const bool Stone=(F==Trebuchet);
    if(Stone && Stat==4) return Level>0 ? TEXT("已激活 · 每第 4 发形成热油") : TEXT("未激活");
    if(Stat==Reload) return CompactSpace ? FString::Printf(TEXT("%.2f秒"), V) : FString::Printf(TEXT("%.2f 秒"), V);
    if(Stat==Reach || (Stone && Stat==Special))
        return FString::SanitizeFloat(V/100., 0)+(CompactSpace ? TEXT("米") : TEXT(" 米"));
    if(Stat==Special) return FString::Printf(TEXT("%d%%"), FMath::RoundToInt(V*100.));
    return FString::FromInt(FMath::RoundToInt(V));
}

FString StatDeltaText(VillageSiegeUpgrades::EFacility F, int32 Stat, int32 Rank)
{
    using namespace VillageSiegeUpgrades;
    const int32 Max=MaxRank(FacilityStatIndex(F, Stat));
    const bool Done=Rank>=Max;
    const int32 Mult=Done ? Max : 1;
    if(F==SmartTurret)
    {
        switch(Stat)
        {
        case TurretDamage:    return Done ? FString::Printf(TEXT("+%d%% 累计"), 5*Mult) : TEXT("+5%");
        case TurretFeed:      return Done ? FString::Printf(TEXT("-%d%%/+%d%% 累计"), 3*Mult, 2*Mult) : TEXT("-3% / +2%");
        case TurretOptics:    return Done ? FString::Printf(TEXT("+%s米/-%d%% 累计"), *FString::SanitizeFloat(1.5*Mult, 0), 3*Mult) : TEXT("+1.5米 / 散布-3%");
        case TurretWeakpoint: return Done ? FString::Printf(TEXT("%d%% 满级"), 10*Mult) : TEXT("+10%");
        case TurretMagExpand: return Done ? FString::Printf(TEXT("+%d%% 满级"), 25*Mult) : TEXT("+25%");
        default:              return Done ? FString::Printf(TEXT("+%d 穿透满级"), Mult) : TEXT("+1 穿透");
        }
    }
    if(F==HotOil)
    {
        switch(Stat)
        {
        case OilDamage:     return Done ? FString::Printf(TEXT("+%d%% 累计"), 10*Mult) : TEXT("+10%");
        case OilRadius:     return Done ? FString::Printf(TEXT("+%s 米 累计"), *FString::SanitizeFloat(.15*Mult, 0)) : TEXT("+0.15 米");
        case OilDuration:   return Done ? FString::Printf(TEXT("+%d 秒 累计"), 2*Mult) : TEXT("+2 秒");
        default:            return Done ? FString::Printf(TEXT("+%d 层 累计"), Mult) : TEXT("+1 层");
        }
    }
    if(F==LightningSpire)
    {
        switch(Stat)
        {
        case SpireDamage:    return Done ? FString::Printf(TEXT("+%d%% 累计"), 10*Mult) : TEXT("+10%");
        case SpireCooldown:  return Done ? FString::Printf(TEXT("-%d%% 累计"), 3*Mult) : TEXT("-3%");
        case SpireElectrify: return Done ? FString::Printf(TEXT("+%d 层 累计"), Mult) : TEXT("+1 层");
        default:             return Done ? FString::Printf(TEXT("+%d%% 累计"), 3*Mult) : TEXT("+3%");
        }
    }
    const bool Stone=(F==Trebuchet);
    switch(Stat)
    {
    case Damage:  return Done ? FString::Printf(TEXT("+%d%% 累计"), 10*Mult) : TEXT("+10%");
    case Reload:  return Done ? FString::Printf(TEXT("-%d%% 累计"), 3*Mult) : TEXT("-3%");
    case Special: return Done ? FString::Printf(TEXT("+%d%% 累计"), 15*Mult) : TEXT("+15%");
    case 4:       return Done ? TEXT("已解锁 · 友方免伤") : TEXT("友方免伤 · 联动热油锅");
    default:      return Done ? FString::Printf(TEXT("+%d%% 累计"), 3*Mult) : TEXT("+3%");
    }
}

const TCHAR* StatDetailDescription(VillageSiegeUpgrades::EFacility F, int32 Stat)
{
    using namespace VillageSiegeUpgrades;
    if(F==Trebuchet && Stat==4)
        return TEXT("攻击 3 次后，第 4 次攻击在命中位置地面形成热油，效果实时匹配热油锅当前等级与数值；投石机形成的热油地面不会对友方单位造成伤害。");
    if(F==SmartTurret)
    {
        switch(Stat)
        {
        case TurretDamage:    return TEXT("按比例发挥所挂载主战长枪的完整面板、强化等级、枪匠配件与武器附魔威力。");
        case TurretFeed:      return TEXT("缩短机枪塔自动换弹耗时（管式霰弹亦同步加速逐发补弹），并提高射速。");
        case TurretOptics:    return TEXT("同步扩大 3D 蓝宝石光学索敌半径与建造指示圈，并收束连射与霰弹散布。");
        case TurretWeakpoint: return TEXT("触发时自动锁头瞄准目标弱点，享受枪械完整暴击倍率加成。");
        case TurretMagExpand: return TEXT("扩展挂载枪械的弹匣与弹鼓装填上限（无限备弹，仅消耗弹匣容量）。");
        default:              return TEXT("高速穿甲弹道在命中怪物后可额外贯通后续目标，强化尸潮防线清场能力。");
        }
    }
    return nullptr;
}

const FSlateBrush& PillDarkBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(15, 212), 4, FLinearColor(222.f/255.f, 222.f/255.f, 222.f/255.f, .24f), 1); return B; }
const FSlateBrush& PillGoldBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(FLinearColor::FromSRGBColor(FColor(26, 21, 14, 228)), 4, ColdSteelUI::HUDGold, 1); return B; }
const FSlateBrush& PillMutedBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(22, 220), 4, ColdSteelUI::Gray(222, 30), 1); return B; }
const FSlateBrush& StatNormalBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(255, 9), 6, ColdSteelUI::Gray(222, 24), 1); return B; }
const FSlateBrush& StatHighBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(FLinearColor(ColdSteelUI::HUDGold.R, ColdSteelUI::HUDGold.G, ColdSteelUI::HUDGold.B, .11f), 6, FLinearColor(ColdSteelUI::HUDGold.R, ColdSteelUI::HUDGold.G, ColdSteelUI::HUDGold.B, .42f), 1); return B; }
const FSlateBrush& StripNormalBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(13, 185), 4, ColdSteelUI::Gray(222, 20), 1); return B; }
const FSlateBrush& StripGoldBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(16, 205), 4, FLinearColor(ColdSteelUI::HUDGold.R, ColdSteelUI::HUDGold.G, ColdSteelUI::HUDGold.B, .42f), 1); return B; }
const FSlateBrush& ReservedCardBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(20, 228), 6, ColdSteelUI::Gray(222, 26), 1); return B; }
const FSlateBrush& CompactTabBrush(bool Active, bool Unlocked)
{
    using namespace ColdSteelUI;
    static const FSlateBrush On=RoundedBrush(FLinearColor::FromSRGBColor(FColor(38, 35, 29, 242)), 6, FLinearColor(HUDGold.R, HUDGold.G, HUDGold.B, .82f), 1.5f);
    static const FSlateBrush Off=RoundedBrush(FLinearColor::FromSRGBColor(FColor(28, 28, 31, 238)), 6, Border, 1.f);
    static const FSlateBrush Locked=RoundedBrush(Gray(20, 218), 6, Gray(222, 24), 1.f);
    return !Unlocked ? Locked : (Active ? On : Off);
}
const FSlateBrush& PipEmptyBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(255, 26), 1.5f, ColdSteelUI::Gray(255, 58), .7f); return B; }
const FSlateBrush& PipMidBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::MountStamina, 1.5f, ColdSteelUI::MountStamina, 0); return B; }
const FSlateBrush& PipGoldBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::HUDGoldLight, 1.5f, ColdSteelUI::HUDGoldLight, 0); return B; }
const FSlateBrush& TrackDoneBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::Enhanced, 1.5f, FLinearColor::Transparent, 0); return B; }
const FSlateBrush& TrackFullBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::HUDGoldLight, 1.5f, FLinearColor::Transparent, 0); return B; }
const FSlateBrush& TrackNextBrush()
{
    static const FSlateBrush B=ColdSteelUI::RoundedBrush(FLinearColor(ColdSteelUI::HUDGoldLight.R, ColdSteelUI::HUDGoldLight.G, ColdSteelUI::HUDGoldLight.B, .34f), 1.5f, FLinearColor(ColdSteelUI::HUDGold.R, ColdSteelUI::HUDGold.G, ColdSteelUI::HUDGold.B, .88f), .8f);
    return B;
}
const FSlateBrush& TrackIdleBrush() { static const FSlateBrush B=ColdSteelUI::RoundedBrush(ColdSteelUI::Gray(255, 22), 1.5f, FLinearColor::Transparent, 0); return B; }
}

void SSiegeWorkshopMarket::Construct(const FArguments& Args)
{
    using namespace ColdSteelUI;
    Conversation=Args._Conversation;
    OnBack=Args._OnBack;

    Facilities.Reset();
    {
        FFacilityEntry& F=Facilities.AddDefaulted_GetRef();
        F.Id=TEXT("trebuchet"); F.Name=TEXT("配重投石机"); F.ShortName=TEXT("投石机");
        F.Subtitle=TEXT("范围轰击 · 独特热油"); F.ShortSub=TEXT("范围轰击");
        F.PortraitFile=TEXT("Trebuchet.jpg"); F.UpgradeOffset=VillageSiegeUpgrades::Index(VillageSiegeUpgrades::Trebuchet, 0); F.bUnlocked=true;
    }
    {
        FFacilityEntry& F=Facilities.AddDefaulted_GetRef();
        F.Id=TEXT("ballista"); F.Name=TEXT("固定式弩炮"); F.ShortName=TEXT("弩炮");
        F.Subtitle=TEXT("城防快射 · 穿甲点杀"); F.ShortSub=TEXT("穿甲点杀");
        F.PortraitFile=TEXT("Ballista.jpg"); F.UpgradeOffset=VillageSiegeUpgrades::Index(VillageSiegeUpgrades::Ballista, 0); F.bUnlocked=true;
    }
    {
        FFacilityEntry& F=Facilities.AddDefaulted_GetRef();
        F.Id=TEXT("hot_oil"); F.Name=TEXT("城防热油锅"); F.ShortName=TEXT("热油锅");
        F.Subtitle=TEXT("墙头倾泻 · 灼烧火海"); F.ShortSub=TEXT("灼烧火海");
        F.PortraitFile=TEXT("HotOil.jpg"); F.UpgradeOffset=VillageSiegeUpgrades::Index(VillageSiegeUpgrades::HotOil, 0); F.bUnlocked=true;
    }
    {
        FFacilityEntry& F=Facilities.AddDefaulted_GetRef();
        F.Id=TEXT("lightning_spire"); F.Name=TEXT("符文引雷塔"); F.ShortName=TEXT("引雷塔");
        F.Subtitle=TEXT("高塔城门 · 链雷感电"); F.ShortSub=TEXT("链雷感电");
        F.PortraitFile=TEXT("LightningSpire.jpg"); F.UpgradeOffset=VillageSiegeUpgrades::Index(VillageSiegeUpgrades::LightningSpire, 0); F.bUnlocked=true;
    }
    {
        FFacilityEntry& F=Facilities.AddDefaulted_GetRef();
        F.Id=TEXT("smart_turret"); F.Name=TEXT("智能机枪塔"); F.ShortName=TEXT("机枪塔");
        F.Subtitle=TEXT("长枪挂架 · 智控索敌"); F.ShortSub=TEXT("智控索敌");
        F.PortraitFile=TEXT("SmartTurret.jpg"); F.UpgradeOffset=VillageSiegeUpgrades::SmartTurretBaseIdx; F.bUnlocked=true;
    }

    for(FFacilityEntry& F : Facilities)
    {
        if(!F.PortraitFile.IsEmpty())
        {
            F.Portrait.Reset(FImageUtils::ImportFileAsTexture2D(FPaths::ProjectContentDir()/TEXT("ColdSteelUI/SiegeWorkshop")/F.PortraitFile));
            F.Brush.SetResourceObject(F.Portrait.Get());
            F.Brush.DrawAs=ESlateBrushDrawType::Image;
            F.Brush.SetImageSize(FVector2D(672, 322));
            F.Brush.SetUVRegion(FBox2f(FVector2f::ZeroVector, FVector2f(1, 1)));
        }
    }

    static const FSlateBrush Panel=RoundedBrush(GlassFallback, PanelRadius, Border, 1);
    static const FSlateBrush HeaderBg=RoundedBrushCorners(HeaderTint, FVector4(PanelRadius, PanelRadius, 0, 0));
    static const FSlateBrush Rule=RoundedBrush(Gray(222, 22), 0, FLinearColor::Transparent, 0);
    static const FSlateBrush GoldBar=RoundedBrush(HUDGold, 1, FLinearColor::Transparent, 0);
    static const FScrollBoxStyle ScrollStyle=FScrollBoxStyle()
        .SetTopShadowBrush(FSlateNoResource()).SetBottomShadowBrush(FSlateNoResource())
        .SetLeftShadowBrush(FSlateNoResource()).SetRightShadowBrush(FSlateNoResource());

    auto DesktopRow=SNew(SHorizontalBox);
    auto CompactRow=SNew(SHorizontalBox);
    Tabs.SetNum(Facilities.Num());
    for(int32 I=0; I<Facilities.Num(); ++I)
    {
        DesktopRow->AddSlot().AutoWidth().Padding(I==0 ? 0.f : 4.f, 0, (I+1==Facilities.Num()) ? 0.f : 4.f, 0)[MakeFacilityCard(I)];
        CompactRow->AddSlot().AutoWidth().Padding(I==0 ? 0.f : 3.f, 0, (I+1==Facilities.Num()) ? 0.f : 3.f, 0)[MakeCompactTab(I)];
    }

    auto SummaryRow=SNew(SHorizontalBox);
    for(int32 I=0; I<4; ++I)
    {
        if(I>0) SummaryRow->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(2, 0)[SNew(SBox).WidthOverride(1.f).HeightOverride(11.f)[SNew(SImage).Image(&Rule)]];
        SummaryRow->AddSlot().FillWidth(1).HAlign(HAlign_Center).VAlign(VAlign_Center)
        [
            SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 5, 0)
            [SAssignNew(SummaryKeys[I], STextBlock).Font(Font(12.f)).ColorAndOpacity(TextTertiary)]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [SAssignNew(SummaryValues[I], STextBlock).Font(Font(12.5f)).ColorAndOpacity(TextPrimary)]
        ];
    }

    auto OffersBox=SNew(SVerticalBox);
    for(int32 I=0; I<VillageSiegeUpgrades::MaxStatsPerFacility; ++I) OffersBox->AddSlot().AutoHeight()[MakeOffer(I)];

    SetClipping(EWidgetClipping::ClipToBounds);
    ChildSlot
    [
        SNew(SOverlay)
        +SOverlay::Slot().HAlign(HAlign_Right).VAlign(VAlign_Fill).Padding(0, 8, 0, 8)
        [
            SAssignNew(Drawer, SBox).WidthOverride_Lambda([this]{ return FOptionalSize(DrawerWidth); })
            [
                SNew(SBorder).BorderImage(&Panel).Padding(0)
                [
                    SNew(SVerticalBox)
                    +SVerticalBox::Slot().AutoHeight()
                    [
                        SNew(SBorder).BorderImage(&HeaderBg).Padding(FMargin(16, 11, 16, 10))
                        [
                            SNew(SHorizontalBox)
                            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
                            [
                                SNew(SHorizontalBox)
                                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 8, 0)
                                [SNew(SBox).WidthOverride(2.5f).HeightOverride(16.f)[SNew(SImage).Image(&GoldBar)]]
                                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                                [SNew(STextBlock).Text(Text(TEXT("守备设施升级"))).Font(Font(20.f, ETextWeight::Bold)).ColorAndOpacity(TextPrimary)]
                                +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(10, 1, 0, 0)
                                [SAssignNew(ShareTag, STextBlock).Text(Text(TEXT("全村共享 · 即时生效"))).Font(Font(12.f)).ColorAndOpacity(TextTertiary)]
                            ]
                            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 8, 0)
                            [
                                SNew(SBox).HeightOverride(28.f)
                                [
                                    SNew(SBorder).BorderImage(&PillGoldBrush()).VAlign(VAlign_Center).Padding(FMargin(10, 0))
                                    [SAssignNew(Balance, STextBlock).Font(Font(13.f, ETextWeight::SemiBold)).ColorAndOpacity(HUDGoldLight)]
                                ]
                            ]
                            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                            [
                                SNew(SBox).HeightOverride(28.f)
                                [
                                    // Keep tooltip strictly on the close button for FSiegeDrawerReview::FindClose.
                                    SNew(SButton).ButtonStyle(&ColdSteelMarketCard::SecondaryActionStyle()).VAlign(VAlign_Center).ContentPadding(FMargin(10, 0))
                                    .ToolTip(ColdSteelToolTip::Make(Text(TEXT("收回边栏，返回工匠对话"))))
                                    .OnClicked_Lambda([this]{ RequestClose(); return FReply::Handled(); })
                                    [
                                        SNew(SHorizontalBox)
                                        +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                                        [SNew(STextBlock).Text(Text(TEXT("收起"))).Font(Font(13.f)).ColorAndOpacity(TextPrimary)]
                                        +SHorizontalBox::Slot().AutoWidth().Padding(6, 0, 0, 0).VAlign(VAlign_Center)
                                        [SNew(STextBlock).Text(Text(TEXT("Esc"))).Font(Font(11.f)).ColorAndOpacity(HUDGoldLight)]
                                    ]
                                ]
                            ]
                        ]
                    ]
                    +SVerticalBox::Slot().AutoHeight()[SNew(SBox).HeightOverride(1)[SNew(SImage).Image(&Rule)]]
                    +SVerticalBox::Slot().FillHeight(1).Padding(16, 10, 16, 11)
                    [
                        SNew(SVerticalBox)
                        +SVerticalBox::Slot().AutoHeight()
                        [
                            SNew(SOverlay)
                            +SOverlay::Slot()
                            [
                                SNew(SBox)
                                .Visibility_Lambda([this]{ return bCompactHeader ? EVisibility::Collapsed : EVisibility::SelfHitTestInvisible; })
                                [
                                    ColdSteelUI::ApplyGoldScroll(
                                        SAssignNew(FacilityScroll, SScrollBox).Style(&ScrollStyle)
                                        .Orientation(Orient_Horizontal)
                                        .AllowOverscroll(EAllowOverscroll::No).ConsumeMouseWheel(EConsumeMouseWheel::WhenScrollingPossible)
                                        +SScrollBox::Slot()[DesktopRow],
                                        FVector2D(5, 5), FMargin(0, 4, 0, 0), true)
                                ]
                            ]
                            +SOverlay::Slot()
                            [
                                SNew(SBox)
                                .Visibility_Lambda([this]{ return bCompactHeader ? EVisibility::SelfHitTestInvisible : EVisibility::Collapsed; })
                                [
                                    ColdSteelUI::ApplyGoldScroll(
                                        SNew(SScrollBox).Style(&ScrollStyle)
                                        .Orientation(Orient_Horizontal)
                                        .AllowOverscroll(EAllowOverscroll::No)
                                        +SScrollBox::Slot()[CompactRow],
                                        FVector2D(4, 4), FMargin(0, 3, 0, 0), true)
                                ]
                            ]
                        ]
                        +SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)
                        [
                            SAssignNew(SummaryHost, SBox)
                            .Visibility_Lambda([this]{ return bCompactHeader ? EVisibility::Collapsed : EVisibility::HitTestInvisible; })
                            [SNew(SBorder).BorderImage(&StripNormalBrush()).Padding(FMargin(8, 6))[SummaryRow]]
                        ]
                        +SVerticalBox::Slot().AutoHeight().Padding(0, 10, 0, 7)
                        [
                            SNew(SHorizontalBox)
                            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 7, 0)
                            [SNew(SBox).WidthOverride(2.5f).HeightOverride(12.f)[SNew(SImage).Image(&GoldBar)]]
                            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                            [SNew(STextBlock).Text(Text(TEXT("强化项目"))).Font(Font(14.f, ETextWeight::SemiBold)).ColorAndOpacity(HUDGoldLight)]
                            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(10, 0, 10, 0)
                            [SNew(SBox).HeightOverride(1)[SNew(SImage).Image(&Rule)]]
                            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                            [SNew(STextBlock).Text(Text(TEXT("当前 → 下一级 · 分段进度"))).Font(Font(11.5f)).ColorAndOpacity(TextTertiary)]
                        ]
                        +SVerticalBox::Slot().FillHeight(1)
                        [
                            ColdSteelUI::ApplyGoldScroll(
                                SAssignNew(OffersScroll, SScrollBox).Style(&ScrollStyle)
                                .AllowOverscroll(EAllowOverscroll::No)
                                .ConsumeMouseWheel(EConsumeMouseWheel::Always).AnimateWheelScrolling(true)
                                +SScrollBox::Slot()[OffersBox],
                                FVector2D(5.5f, 5.5f), FMargin(6, 0, 0, 0), true)
                        ]
                        +SVerticalBox::Slot().AutoHeight().Padding(0, 8, 0, 0)
                        [
                            SAssignNew(FeedbackFrame, SBorder).BorderImage(&StripNormalBrush()).Padding(FMargin(10, 6))
                            [SAssignNew(Feedback, STextBlock).Font(Font(12.5f)).AutoWrapText(true)]
                        ]
                    ]
                ]
            ]
        ]
    ];

    Drawer->SetRenderOpacity(0.f);
    Drawer->SetVisibility(EVisibility::HitTestInvisible);
    Refresh();
}

float SSiegeWorkshopMarket::FacilityCardWidth(bool bCompact) const
{
    const float Inner=FMath::Max(320.f, DrawerWidth-34.f);
    const int32 VisibleCount=FMath::Clamp(Facilities.Num(), 1, 3);
    const float Gap=(VisibleCount-1)*(bCompact ? 6.f : 8.f);
    const float MinW=bCompact ? 110.f : 146.f;
    return FMath::Max(MinW, (Inner-Gap)/VisibleCount);
}

TSharedRef<SWidget> SSiegeWorkshopMarket::MakeFacilityCard(int32 I)
{
    using namespace ColdSteelUI;
    FFacilityEntry& E=Facilities[I];

    if(!E.bUnlocked)
    {
        return SNew(SBox).WidthOverride_Lambda([this]{ return FOptionalSize(FacilityCardWidth(false)); })
            [SNew(SBorder).BorderImage(&ReservedCardBrush()).Padding(1)
                [SNew(SBox).HeightOverride_Lambda([this]{ return FOptionalSize(PlateHeight); }).Clipping(EWidgetClipping::ClipToBounds)
                    [SNew(SOverlay)
                        +SOverlay::Slot().VAlign(VAlign_Top).Padding(7, 6)[SNew(SBorder).BorderImage(&PillMutedBrush()).Padding(FMargin(6, 2))[SNew(STextBlock).Text(Text(TEXT("预留 · 待开放"))).Font(Font(11.f)).ColorAndOpacity(TextSecondary)]]
                        +SOverlay::Slot().VAlign(VAlign_Bottom).Padding(8, 0, 8, 7)[SNew(STextBlock).Text(Text(E.Name)).Font(Font(14.f, ETextWeight::SemiBold)).ColorAndOpacity(TextSecondary).OverflowPolicy(ETextOverflowPolicy::Ellipsis)]]]];
    }

    auto PipsRow=SNew(SHorizontalBox);
    const int32 PipCount=VillageSiegeUpgrades::FacilityStatCount(VillageSiegeUpgrades::FacilityOf(E.UpgradeOffset));
    for(int32 P=0; P<VillageSiegeUpgrades::MaxStatsPerFacility; ++P)
    {
        PipsRow->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(P==0 ? 0.f : 2.f, 0, 0, 0)
        [SNew(SBox).WidthOverride(4.5f).HeightOverride(4.5f).Visibility(P<PipCount ? EVisibility::Visible : EVisibility::Collapsed)[SAssignNew(E.PipImages[P], SImage).Image(&PipEmptyBrush())]];
    }

    const bool IsSel=(I==Selected);
    SAssignNew(Tabs[I], SButton).ButtonStyle(&ColdSteelMarketCard::CardFrame(IsSel))
        .ContentPadding(1).HAlign(HAlign_Fill).VAlign(VAlign_Fill)
        .OnClicked_Lambda([this, I]{
            if(!bClosing && Selected!=I){ Selected=I; OffersScroll->ScrollToStart(); if(FacilityScroll && Tabs.IsValidIndex(I) && Tabs[I]) FacilityScroll->ScrollDescendantIntoView(Tabs[I].ToSharedRef(), true); Refresh(); }
            return FReply::Handled();
        })
        [
            SNew(SBox).WidthOverride_Lambda([this]{ return FOptionalSize(FacilityCardWidth(false)); })
            .HeightOverride_Lambda([this]{ return FOptionalSize(PlateHeight); }).Clipping(EWidgetClipping::ClipToBounds)
            .Visibility(EVisibility::HitTestInvisible)
            [
                SNew(SOverlay)
                +SOverlay::Slot()
                [
                    SAssignNew(E.Plate, SHorseMarketPlate)
                    .Sharp(&E.Brush).PreferredHeight(124.f).CornerRadius(5.f)
                    .ShowScrim(true).CornerBrackets(false).PortraitFocus(FVector2f(.50f, .54f))
                ]
                +SOverlay::Slot().VAlign(VAlign_Top).Padding(7, 6)
                [
                    SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                    [
                        SAssignNew(E.StateBadge, SBorder).BorderImage(IsSel ? &PillGoldBrush() : &PillMutedBrush()).Padding(FMargin(6, 2))
                        [SAssignNew(E.StateLabel, STextBlock).Font(Font(11.f)).ColorAndOpacity(IsSel ? HUDGoldLight : TextSecondary)]
                    ]
                    +SHorizontalBox::Slot().FillWidth(1)[SNew(SSpacer)]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                    [
                        SNew(SBorder).BorderImage(&PillDarkBrush()).Padding(FMargin(6, 2))
                        [
                            SNew(SHorizontalBox)
                            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 4, 0)
                            [SAssignNew(E.TotalRankLabel, STextBlock).Font(Font(11.f)).ColorAndOpacity(TextPrimary)]
                            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)[PipsRow]
                        ]
                    ]
                ]
                +SOverlay::Slot().VAlign(VAlign_Bottom).Padding(8, 0, 8, 6)
                [
                    SNew(SVerticalBox)
                    +SVerticalBox::Slot().AutoHeight()
                    [
                        SNew(STextBlock).Text(Text(E.Name)).Font(Font(15.f, ETextWeight::SemiBold))
                        .ColorAndOpacity(FLinearColor(.95f, .95f, .96f, 1.f))
                        .ShadowOffset(FVector2D(0, 1.5f)).ShadowColorAndOpacity(FLinearColor(0, 0, 0, .88f))
                        .OverflowPolicy(ETextOverflowPolicy::Ellipsis)
                    ]
                    +SVerticalBox::Slot().AutoHeight().Padding(0, 1, 0, 0)
                    [
                        SNew(STextBlock).Text(Text(E.Subtitle)).Font(Font(11.f))
                        .ColorAndOpacity(FLinearColor(.78f, .78f, .80f, 1.f))
                        .ShadowOffset(FVector2D(0, 1.f)).ShadowColorAndOpacity(FLinearColor(0, 0, 0, .90f))
                        .OverflowPolicy(ETextOverflowPolicy::Ellipsis)
                    ]
                ]
            ]
        ];

    SetTabReveal(I, IsSel ? 1.f : 0.f);
    return Tabs[I].ToSharedRef();
}

TSharedRef<SWidget> SSiegeWorkshopMarket::MakeCompactTab(int32 I)
{
    using namespace ColdSteelUI;
    FFacilityEntry& E=Facilities[I];

    TSharedRef<SWidget> Thumb=E.bUnlocked
        ? StaticCastSharedRef<SWidget>(
            SNew(SHorseMarketPlate).Sharp(&E.Brush).PreferredHeight(40.f).CornerRadius(4.f)
            .ShowScrim(false).CornerBrackets(false).PortraitFocus(FVector2f(.50f, .54f)))
        : StaticCastSharedRef<SWidget>(
            SNew(SBorder).BorderImage(&PillMutedBrush()).HAlign(HAlign_Center).VAlign(VAlign_Center)
            [SNew(STextBlock).Text(Text(TEXT("✦"))).Font(Font(14.f)).ColorAndOpacity(FLinearColor(HUDGold.R, HUDGold.G, HUDGold.B, .35f))]);

    const bool IsSel=E.bUnlocked && I==Selected;
    auto TabBox=SNew(SBox).WidthOverride_Lambda([this]{ return FOptionalSize(FacilityCardWidth(true)); }).HeightOverride(50.f)
    [
        SAssignNew(E.CompactFrame, SBorder).BorderImage(&CompactTabBrush(IsSel, E.bUnlocked)).Padding(FMargin(6, 5))
        [
            SNew(SHorizontalBox)
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(0, 0, 6, 0)
            [SNew(SBox).WidthOverride(36.f).HeightOverride(36.f).Clipping(EWidgetClipping::ClipToBounds)[Thumb]]
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center)
            [
                SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()
                [
                    SNew(STextBlock).Text(Text(E.ShortName)).Font(Font(13.f, ETextWeight::SemiBold))
                    .ColorAndOpacity(E.bUnlocked ? TextPrimary : TextTertiary)
                    .OverflowPolicy(ETextOverflowPolicy::Ellipsis)
                ]
                +SVerticalBox::Slot().AutoHeight().Padding(0, 1, 0, 0)
                [
                    SAssignNew(E.CompactMeta, STextBlock).Text(Text(E.bUnlocked ? FString::Printf(TEXT("0/%d 阶"), VillageSiegeUpgrades::FacilityMaxTotal(VillageSiegeUpgrades::FacilityOf(E.UpgradeOffset))) : FString(TEXT("预留槽"))))
                    .Font(Font(11.f)).ColorAndOpacity(E.bUnlocked ? (IsSel ? HUDGoldLight : TextSecondary) : TextTertiary)
                    .OverflowPolicy(ETextOverflowPolicy::Ellipsis)
                ]
            ]
        ]
    ];

    if(!E.bUnlocked) return TabBox;

    // Share the button action without replacing Tabs[I] so FSiegeDrawerReview still drives Tabs[0..2].
    static const FButtonStyle TransparentBtn=[]
    {
        FButtonStyle S=ColdSteelUI::ButtonStyle();
        const FSlateBrush Empty=FSlateNoResource();
        S.SetNormal(Empty).SetHovered(Empty).SetPressed(Empty).SetDisabled(Empty)
         .SetNormalPadding(0).SetPressedPadding(0);
        return S;
    }();
    return SNew(SButton).ButtonStyle(&TransparentBtn).ContentPadding(0)
        .OnClicked_Lambda([this, I]{
            if(!bClosing && Selected!=I){ Selected=I; OffersScroll->ScrollToStart(); if(FacilityScroll && Tabs.IsValidIndex(I) && Tabs[I]) FacilityScroll->ScrollDescendantIntoView(Tabs[I].ToSharedRef(), true); Refresh(); }
            return FReply::Handled();
        })
        [TabBox];
}

void SSiegeWorkshopMarket::SetTabReveal(int32 I, float Fraction)
{
    if(!Facilities.IsValidIndex(I))return;
    FFacilityEntry& E=Facilities[I];
    E.Reveal=Fraction;
    if(E.Plate) E.Plate->SetReveal(ColdSteelUI::EaseSmooth(Fraction));
}

TSharedRef<SWidget> SSiegeWorkshopMarket::MakeOffer(int32 Stat)
{
    using namespace ColdSteelUI;
    FOffer& O=Offers[Stat];
    return SAssignNew(O.RowBox, SBox).Padding(FMargin(0, Stat==0 ? 0.f : 8.f, 0, 0))
    [
        SAssignNew(O.CardFrame, SBorder).BorderImage(&StatNormalBrush()).Padding(FMargin(12, 9))
        [
            SNew(SHorizontalBox)
            +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(0, 0, 12, 0)
            [
                SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight()
                [
                    SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                    [SAssignNew(O.Title, STextBlock).Font(Font(14.5f, ETextWeight::SemiBold)).ColorAndOpacity(TextPrimary)]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center).Padding(8, 1, 0, 0)
                    [SAssignNew(O.Tier, STextBlock).Font(Font(12.f)).ColorAndOpacity(TextTertiary)]
                ]
                +SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
                [
                    SNew(SHorizontalBox)
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                    [SAssignNew(O.Current, STextBlock).Font(Font(15.f)).ColorAndOpacity(TextPrimary)]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                    [SAssignNew(O.Arrow, STextBlock).Text(Text(TEXT("  →  "))).Font(Font(13.f)).ColorAndOpacity(TextTertiary)]
                    +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                    [SAssignNew(O.Next, STextBlock).Font(Font(15.5f, ETextWeight::SemiBold)).ColorAndOpacity(HUDGoldLight)]
                    +SHorizontalBox::Slot().FillWidth(1).VAlign(VAlign_Center).Padding(8, 1, 0, 0)
                    [SAssignNew(O.Delta, STextBlock).Font(Font(12.f)).ColorAndOpacity(Success)]
                ]
                +SVerticalBox::Slot().AutoHeight().Padding(0, 5, 0, 0)
                [
                    SAssignNew(O.DetailText, STextBlock).Font(Font(11.5f)).ColorAndOpacity(TextSecondary)
                    .AutoWrapText(true).Visibility(EVisibility::Collapsed)
                ]
                +SVerticalBox::Slot().AutoHeight().Padding(0, 4, 0, 0)
                [
                    SAssignNew(O.RequirementText, STextBlock).Font(Font(11.5f)).ColorAndOpacity(HUDGoldLight)
                    .AutoWrapText(true).Visibility(EVisibility::Collapsed)
                ]
                +SVerticalBox::Slot().AutoHeight().Padding(0, 7, 0, 0)
                [SAssignNew(O.LevelTrack, SHorizontalBox)]
            ]
            +SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
            [
                SNew(SVerticalBox)
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)
                [
                    SAssignNew(O.FullBadge, SBorder).BorderImage(&PillGoldBrush()).Padding(FMargin(10, 4))
                    [SAssignNew(O.Full, STextBlock).Text(Text(TEXT("✓ 已满级"))).Font(Font(13.f, ETextWeight::SemiBold)).ColorAndOpacity(HUDGoldLight)]
                ]
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right)
                [
                    SNew(SBox).MinDesiredWidth(84).HeightOverride_Lambda([this]{ return FOptionalSize(bCompactHeader ? 25.f : 28.f); })
                    .Visibility_Lambda([this, Stat]{ return Offers[Stat].Rank>=Offers[Stat].MaxRank ? EVisibility::Collapsed : EVisibility::Visible; })
                    [
                        SAssignNew(O.Buy, SButton).ButtonStyle(&ColdSteelMarketCard::PurchaseStyle()).HAlign(HAlign_Center).VAlign(VAlign_Center)
                        .ContentPadding(FMargin(10, 0)).OnClicked_Lambda([this, Stat]{
                            if(!bClosing && OpenFraction>=1.f && Facilities.IsValidIndex(Selected) && Facilities[Selected].UpgradeOffset!=INDEX_NONE)
                            {
                                const VillageSiegeUpgrades::EFacility Fac=VillageSiegeUpgrades::FacilityOf(Facilities[Selected].UpgradeOffset);
                                const int32 Idx=VillageSiegeUpgrades::FacilityStatIndex(Fac, Stat);
                                if(auto* C=Conversation.Get()) C->BuySiegeUpgrade(Idx, Offers[Stat].Rank);
                            }
                            return FReply::Handled();
                        })
                        [SAssignNew(O.BuyLabel, STextBlock).Text(Text(TEXT("升级"))).Font(Font(13.f)).ColorAndOpacity(HUDGoldLight)]
                    ]
                ]
                +SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Right).Padding(0, 4, 0, 0)
                [SAssignNew(O.Cost, STextBlock).Font(Font(12.f)).ColorAndOpacity(TextSecondary)]
            ]
        ]
    ];
}

void SSiegeWorkshopMarket::Refresh()
{
    using namespace VillageSiegeUpgrades;
    using namespace ColdSteelUI;
    const auto* C=Conversation.Get();
    if(!C || bClosing || !Facilities.IsValidIndex(Selected))return;
    const FFacilityEntry& Active=Facilities[Selected];
    const int32 BaseIdx=FMath::Max(0, Active.UpgradeOffset);
    const EFacility ActiveFacility=FacilityOf(BaseIdx);
    const int64 Souls=C->WorkshopBalance();
    const FRanks Ranks=C->WorkshopAllRanks();
    const int64 BlueprintCount=C->WorkshopItemCount(TrebuchetHotOilBlueprintId);

    Balance->SetText(Text(FString::Printf(TEXT("✦ %s 灵魂"), *FText::AsNumber(Souls).ToString())));
    const bool HasResult=C->IsPending() || !C->Message.IsEmpty();
    Feedback->SetText(Text(C->IsPending() ? FString(TEXT("正在向服务器确认改造订单，请稍候…")) :
        HasResult ? C->Message : FString(TEXT("升级对全村已建和新建的同类防御设施即时生效。"))));
    Feedback->SetColorAndOpacity(HasResult ? HUDGoldLight : TextSecondary);
    if(FeedbackFrame) FeedbackFrame->SetBorderImage(HasResult ? &StripGoldBrush() : &StripNormalBrush());

    for(int32 I=0; I<Facilities.Num(); ++I)
    {
        FFacilityEntry& F=Facilities[I];
        if(!F.bUnlocked)continue;
        const bool IsSel=(I==Selected);
        if(Tabs.IsValidIndex(I) && Tabs[I]) Tabs[I]->SetButtonStyle(&ColdSteelMarketCard::CardFrame(IsSel));
        if(F.Plate) F.Plate->SetSelected(IsSel);
        if(F.StateBadge) F.StateBadge->SetBorderImage(IsSel ? &PillGoldBrush() : &PillMutedBrush());
        if(F.StateLabel)
        {
            F.StateLabel->SetText(Text(IsSel ? TEXT("★ 检视") : TEXT("待选")));
            F.StateLabel->SetColorAndOpacity(IsSel ? HUDGoldLight : TextSecondary);
        }
        int32 SumRank=0;
        const EFacility Fac=FacilityOf(F.UpgradeOffset);
        const int32 StatCount=FacilityStatCount(Fac);
        const int32 TotalMax=FacilityMaxTotal(Fac);
        for(int32 S=0; S<MaxStatsPerFacility; ++S)
        {
            if(S>=StatCount)
            {
                if(F.PipImages[S]) F.PipImages[S]->SetVisibility(EVisibility::Collapsed);
                continue;
            }
            const int32 Idx=FacilityStatIndex(Fac, S);
            const int32 R=Rank(Ranks, Idx);
            SumRank+=R;
            if(F.PipImages[S])
            {
                F.PipImages[S]->SetVisibility(EVisibility::Visible);
                F.PipImages[S]->SetImage(R>=MaxRank(Idx) ? &PipGoldBrush() : (R>0 ? &PipMidBrush() : &PipEmptyBrush()));
            }
        }
        if(F.TotalRankLabel) F.TotalRankLabel->SetText(Text(FString::Printf(TEXT("%d/%d"), SumRank, TotalMax)));
        if(F.CompactFrame) F.CompactFrame->SetBorderImage(&CompactTabBrush(IsSel, true));
        if(F.CompactMeta)
        {
            F.CompactMeta->SetText(Text(FString::Printf(TEXT("%d/%d 阶"), SumRank, TotalMax)));
            F.CompactMeta->SetColorAndOpacity(IsSel ? HUDGoldLight : TextSecondary);
        }
    }

    const int32 ActiveStatCount=FacilityStatCount(ActiveFacility);
    for(int32 I=0; I<MaxStatsPerFacility; ++I)
    {
        FOffer& O=Offers[I];
        const bool bVisible=I<ActiveStatCount;
        if(O.RowBox) O.RowBox->SetVisibility(bVisible ? EVisibility::SelfHitTestInvisible : EVisibility::Collapsed);
        if(!bVisible) continue;

        const int32 Idx=FacilityStatIndex(ActiveFacility, I);
        O.Rank=Rank(Ranks, Idx);
        O.MaxRank=MaxRank(Idx);
        const bool bUnique=IsUniqueUpgrade(Idx);
        const bool bNeedsBlueprint=RequiredBlueprint(Idx)!=nullptr;
        const bool bHasBlueprint=!bNeedsBlueprint || BlueprintCount>=1;
        const bool Done=O.Rank>=O.MaxRank;
        const int32 Cost=Price(Idx, O.Rank);
        const bool Affordable=Souls>=Cost;

        if(I<4)
        {
            if(SummaryKeys[I]) SummaryKeys[I]->SetText(Text(SummaryKey(ActiveFacility, I)));
            if(SummaryValues[I])
            {
                SummaryValues[I]->SetText(Text(StatValue(ActiveFacility, I, O.Rank, true)));
                SummaryValues[I]->SetColorAndOpacity(O.Rank>0 ? HUDGoldLight : TextPrimary);
            }
        }

        O.CardFrame->SetBorderImage(Done ? &StatHighBrush() : &StatNormalBrush());
        O.Title->SetText(Text(StatTitle(ActiveFacility, I)));
        O.Title->SetColorAndOpacity(Done ? FLinearColor::FromSRGBColor(FColor(239, 228, 202)) : TextPrimary);
        O.Tier->SetText(Text(bUnique
            ? (Done ? TEXT("独特强化 · 已解锁") : TEXT("独特强化 · 0/1 级"))
            : FString::Printf(TEXT("%d/%d 级"), O.Rank, O.MaxRank)));
        O.Tier->SetColorAndOpacity(Done ? HUDGoldLight : (O.Rank>0 ? HUDGold : TextTertiary));

        O.Current->SetText(Text(StatValue(ActiveFacility, I, O.Rank)));
        O.Current->SetColorAndOpacity(Done ? HUDGoldLight : TextPrimary);
        O.Arrow->SetVisibility(Done ? EVisibility::Collapsed : EVisibility::HitTestInvisible);
        O.Next->SetText(Done ? FText::GetEmpty() : Text(bUnique ? FString(TEXT("每第 4 发形成热油")) : StatValue(ActiveFacility, I, O.Rank+1)));
        if(bUnique && Done)
        {
            O.Delta->SetText(Text(TEXT("友方免伤 · 联动热油锅")));
        }
        else O.Delta->SetText(Text(StatDeltaText(ActiveFacility, I, O.Rank)));

        if(O.DetailText)
        {
            const TCHAR* Detail=StatDetailDescription(ActiveFacility, I);
            O.DetailText->SetVisibility(Detail ? EVisibility::HitTestInvisible : EVisibility::Collapsed);
            if(Detail) O.DetailText->SetText(Text(Detail));
        }
        if(O.RequirementText)
        {
            const bool bShowUnlockedHotOil=bUnique && Done;
            const bool bShowReq=(bNeedsBlueprint && !Done) || bShowUnlockedHotOil;
            O.RequirementText->SetVisibility(bShowReq ? EVisibility::HitTestInvisible : EVisibility::Collapsed);
            if(bShowUnlockedHotOil)
            {
                const int32 OilDmg=FMath::RoundToInt(Installed(Ranks, HotOil, OilDamage));
                const double OilRad=Installed(Ranks, HotOil, OilRadius)/100.;
                const int32 OilSec=FMath::RoundToInt(Installed(Ranks, HotOil, OilDuration));
                const int32 OilStacks=FMath::RoundToInt(Installed(Ranks, HotOil, OilBurnStacks));
                O.RequirementText->SetText(Text(FString::Printf(TEXT("当前同步热油锅：伤 %d · %s 米 · %d 秒 · %d 层灼烧"),
                    OilDmg, *FString::SanitizeFloat(OilRad, 0), OilSec, OilStacks)));
                O.RequirementText->SetColorAndOpacity(Success);
            }
            else if(bShowReq)
            {
                O.RequirementText->SetText(Text(bHasBlueprint
                    ? FString::Printf(TEXT("解锁条件：已持有「隔热包装方案设计图」（传说 ×%lld，解锁消耗 1 份）"), static_cast<long long>(BlueprintCount))
                    : FString(TEXT("解锁条件：需「隔热包装方案设计图」（传说）· 当前未持有 (0/1)"))));
                O.RequirementText->SetColorAndOpacity(bHasBlueprint ? Success : Danger);
            }
        }

        if(O.LevelTrack)
        {
            O.LevelTrack->SetVisibility(bUnique ? EVisibility::Collapsed : EVisibility::HitTestInvisible);
            if(!bUnique)
            {
                if(O.BuiltTrackMax!=O.MaxRank)
                {
                    O.LevelTrack->ClearChildren();
                    O.TrackSegments.Reset();
                    O.BuiltTrackMax=O.MaxRank;
                    const float Gap=O.MaxRank>6 ? 2.f : 4.f;
                    for(int32 N=0; N<O.MaxRank; ++N)
                    {
                        TSharedPtr<SBorder> Seg;
                        O.LevelTrack->AddSlot().FillWidth(1).Padding(0, 0, N+1==O.MaxRank ? 0.f : Gap, 0)
                            [SNew(SBox).HeightOverride(4.f)[SAssignNew(Seg, SBorder).BorderImage(&TrackIdleBrush())]];
                        O.TrackSegments.Add(Seg);
                    }
                }
                for(int32 N=0; N<O.TrackSegments.Num(); ++N)
                {
                    if(O.TrackSegments[N])
                        O.TrackSegments[N]->SetBorderImage(
                            N<O.Rank ? (Done ? &TrackFullBrush() : &TrackDoneBrush())
                            : (!Done && N==O.Rank) ? &TrackNextBrush()
                            : &TrackIdleBrush());
                }
            }
        }

        O.FullBadge->SetVisibility(Done ? EVisibility::HitTestInvisible : EVisibility::Collapsed);
        O.Full->SetText(Text(bUnique ? TEXT("✓ 已解锁") : TEXT("✓ 已满级")));
        O.Full->SetVisibility(Done ? EVisibility::HitTestInvisible : EVisibility::Collapsed);

        if(O.BuyLabel) O.BuyLabel->SetText(Text(C->IsPending() ? TEXT("结算中…") : !bHasBlueprint ? TEXT("缺设计图") : bUnique ? TEXT("解锁") : TEXT("升级")));
        O.Buy->SetEnabled(!Done && Affordable && bHasBlueprint && !C->IsPending());

        O.Cost->SetText(Text(Done ? FString() : bNeedsBlueprint
            ? (Affordable ? FString::Printf(TEXT("✦ %d + 设计图×1"), Cost) : FString::Printf(TEXT("✦ %d · 缺 %lld + 设计图×1"), Cost, static_cast<long long>(Cost-Souls)))
            : (Affordable ? FString::Printf(TEXT("✦ %d 灵魂"), Cost) : FString::Printf(TEXT("✦ %d · 缺 %lld"), Cost, static_cast<long long>(Cost-Souls)))));
        O.Cost->SetColorAndOpacity(Done ? TextTertiary : C->IsPending() ? HUDGoldLight : (Affordable && bHasBlueprint ? TextSecondary : Danger));
        O.Cost->SetVisibility(Done ? EVisibility::Collapsed : EVisibility::HitTestInvisible);
    }
}

TSharedPtr<SWidget> SSiegeWorkshopMarket::FocusTarget() const
{
    return Tabs.IsValidIndex(Selected) ? Tabs[Selected] : nullptr;
}

void SSiegeWorkshopMarket::RequestClose()
{
    if(bClosing)return;
    bClosing=true;
    Drawer->SetVisibility(EVisibility::HitTestInvisible);
}

void SSiegeWorkshopMarket::Tick(const FGeometry& G, double Time, float Delta)
{
    SCompoundWidget::Tick(G, Time, Delta);
    const FVector2D Size=G.GetLocalSize();
    const float PreviousWidth=DrawerWidth, PreviousFraction=OpenFraction;
    DrawerWidth=FMath::Max(1.f, FMath::Min(float(Size.X), FMath::Clamp(float(Size.X)*.39f, 376.f, 588.f)));
    bCompactHeader=Size.Y<620.f;
    PlateHeight=FMath::Clamp((DrawerWidth-46.f)*.225f, 96.f, 124.f);
    if(ShareTag) ShareTag->SetVisibility(bCompactHeader ? EVisibility::Collapsed : EVisibility::HitTestInvisible);

    const float Step=Delta*(bClosing ? 5.6f : 4.5f);
    OpenFraction=FMath::Clamp(OpenFraction+(bClosing ? -Step : Step), 0.f, 1.f);
    if(PreviousFraction!=OpenFraction || PreviousWidth!=DrawerWidth)
    {
        const float Ease=ColdSteelUI::EaseSmooth(OpenFraction);
        Drawer->SetRenderTransform(FSlateRenderTransform(FVector2D((1.f-Ease)*DrawerWidth, 0)));
        Drawer->SetRenderOpacity(Ease);
        Drawer->SetVisibility(!bClosing && OpenFraction>=1.f ? EVisibility::SelfHitTestInvisible : EVisibility::HitTestInvisible);
    }
    if(bClosing && OpenFraction<=0.f && !bReturnQueued)
    {
        bReturnQueued=true;
        // Restore the dialogue after Slate has finished iterating this frame's widget tree.
        const TWeakPtr<SSiegeWorkshopMarket> Weak=SharedThis(this);
        AsyncTask(ENamedThreads::GameThread, [Weak]{ if(auto Self=Weak.Pin()) Self->OnBack.ExecuteIfBound(); });
    }
    for(int32 I=0; I<Facilities.Num(); ++I)
    {
        if(!Facilities[I].bUnlocked || !Tabs.IsValidIndex(I) || !Tabs[I])continue;
        const bool Open=Selected==I || Tabs[I]->IsHovered() ||
            Tabs[I]->HasAnyUserFocus().Get(EFocusCause::Cleared)==EFocusCause::Navigation;
        const float Next=FMath::Clamp(Facilities[I].Reveal+Delta*(Open ? 5.f : -5.f), 0.f, 1.f);
        if(Next!=Facilities[I].Reveal) SetTabReveal(I, Next);
    }
}
