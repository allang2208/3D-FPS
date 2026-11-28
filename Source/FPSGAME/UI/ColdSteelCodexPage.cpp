#include "ColdSteelCodexPage.h"
#include "ColdSteelWeaponText.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelEnhancementSystem.h"
#include "../FPSGAMEPlayerController.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelInventoryTypes.h"
#include "ColdSteelScrollBar.h"
#include "ColdSteelUIStyle.h"
#include "ColdSteelWeaponIcons.h"
#include "ColdSteelMonsterPortraits.h"
#include "StatusEffectsComponent.h"
#include "../Monsters/MonsterCoreStats.h"
#include "../Development/DevelopmentSpawnComponent.h"
#include "../Weapons/GunsmithSystem.h"
#include "../Weapons/WeaponStatEvaluation.h"
#include "../Production/ProductionToolStats.h"
#include "../Production/ProductionToolEnhance.h"
#include "../Production/ProductionResource.h"
#include "../Production/ProductionTreeHealth.h"
#include "Engine/GameInstance.h"
// GetDefaultObject<AActor>() 需要 AActor 完整定义；角色头文件在怪物类之外也提供它。
#include "GameFramework/Character.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Widgets/Layout/SBox.h"
#include "Widgets/Layout/SBorder.h"
#include "Widgets/Layout/SScrollBox.h"
#include "Widgets/SBoxPanel.h"
#include "Widgets/Input/SButton.h"
#include "Widgets/Input/SEditableTextBox.h"
#include "Widgets/Images/SImage.h"
#include "Widgets/Text/STextBlock.h"

#include "ColdSteelCodexPrivate.h"
using namespace ColdSteelCodexPrivate;

namespace ColdSteelCodexPrivate
{
    /** 武器分类索引：与原项目 codex-manager 的 equipCategories 同序（去掉本工程没有的防具／饰品）。 */
    const TCHAR* WeaponCategoryKeys[] = {TEXT("all"), TEXT("weapon_ranged"), TEXT("weapon_melee"), TEXT("weapon_magic"), TEXT("tool"), TEXT("equipment")};
    const TCHAR* WeaponCategoryLabels[] = {TEXT("全部"), TEXT("枪械"), TEXT("近战武器"), TEXT("魔法武器"), TEXT("生产工具"), TEXT("装备")};
    const int32 WeaponCategoryCount = UE_ARRAY_COUNT(WeaponCategoryKeys);

    /** 怪物分类按品阶。页签刻意不列 Minor（本工程九只身份没有一只用它），
     *  因此**页签下标与 EMonsterRank 的枚举值不是同一套编号**，两者必须显式映射：
     *  页签 1(普通)=Normal、2(精英)=Elite、3(领主)=Lord、4(首领)=Boss。
     *  先前用 SortKey+1 直接比页签下标，等于假设两套编号重合，导致每一阶都错位一格
     *  （毒蛆显示在「领主」、手脑显示在「首领」），此表即为修正。 */
    const EMonsterRank MonsterCategoryRanks[] = {
        EMonsterRank::Normal, EMonsterRank::Normal, EMonsterRank::Elite,
        EMonsterRank::Lord, EMonsterRank::Boss };
    const TCHAR* MonsterCategoryLabels[] = {TEXT("全部"), TEXT("普通"), TEXT("精英"), TEXT("领主"), TEXT("首领")};
    const int32 MonsterCategoryCount = UE_ARRAY_COUNT(MonsterCategoryLabels);
    static_assert(UE_ARRAY_COUNT(MonsterCategoryRanks) == UE_ARRAY_COUNT(MonsterCategoryLabels),
        "怪物页签与品阶映射表长度必须一致");

    /** 状态分区分类：页签 0=全部不过滤，1=增益(buff)，2=减益(debuff)。
     *  与怪物侧同一纪律：页签下标与目录 kind 字符串必须显式映射，不做下标算术。 */
    const TCHAR* StatusCategoryKinds[] = {TEXT("all"), TEXT("buff"), TEXT("debuff")};
    const TCHAR* StatusCategoryLabels[] = {TEXT("全部"), TEXT("增益"), TEXT("减益")};
    const int32 StatusCategoryCount = UE_ARRAY_COUNT(StatusCategoryLabels);
    static_assert(UE_ARRAY_COUNT(StatusCategoryKinds) == UE_ARRAY_COUNT(StatusCategoryLabels),
        "状态页签与 kind 映射表长度必须一致");

    /** 状态来源分组（2026-09-30 用户需求）：显示顺序即表序。分组语义写在注释与组头副标题，
     *  条目归属由目录 group 字段驱动（status_effects.json 单一事实源）。 */
    const FStatusGroupDef StatusGroups[] = {
        { TEXT("combat"),       TEXT("战斗状态"), TEXT("战斗中由攻击、法术与环境直接施加的状态") },
        { TEXT("triggered"),    TEXT("触发效果"), TEXT("满足特定条件时触发：击杀、命中、弹反、施法") },
        { TEXT("persistent"),   TEXT("常态效果"), TEXT("生效期间持续起效，无触发条件") },
        { TEXT("tribute"),      TEXT("祭品与赐福"), TEXT("地牢祭坛祭品与神殿赐福，本次地牢有效") },
        { TEXT("dungeon_event"), TEXT("地牢事件"), TEXT("地牢路线事件获得，按战斗场次消耗") },
    };
    const int32 StatusGroupCount = UE_ARRAY_COUNT(StatusGroups);

    /** 祭品稀有度分组（2026-09-30）：组序高→低，与祭品分类页签同序同长。
     *  标签走 ColdSteelUI::RarityLabel（稀有度文案单一来源），此处只定序。 */
    const TCHAR* TributeRarityKeys[] = {
        TEXT("legendary"), TEXT("mythic"), TEXT("epic"), TEXT("rare"), TEXT("uncommon"), TEXT("common") };
    const TCHAR* TributeRarityLabels[] = {
        TEXT("传说"), TEXT("神话"), TEXT("史诗"), TEXT("稀有"), TEXT("罕见"), TEXT("普通") };
    static_assert(UE_ARRAY_COUNT(TributeRarityKeys) == UE_ARRAY_COUNT(TributeRarityLabels),
        "祭品稀有度键与标签表长度必须一致");

    /** 附魔分区分类：页签 0=全部，1=前缀(prefix)，2=后缀(suffix)。
     *  与状态/怪物侧同一纪律：页签下标与目录 slot 字符串显式映射，不做下标算术。 */
    const TCHAR* EnchantCategorySlots[] = {TEXT("all"), TEXT("prefix"), TEXT("suffix")};
    const TCHAR* EnchantCategoryLabels[] = {TEXT("全部"), TEXT("前缀"), TEXT("后缀")};
    const int32 EnchantCategoryCount = UE_ARRAY_COUNT(EnchantCategoryLabels);
    static_assert(UE_ARRAY_COUNT(EnchantCategorySlots) == UE_ARRAY_COUNT(EnchantCategoryLabels),
        "附魔页签与 slot 映射表长度必须一致");

    /** 兼容 restriction 键 → 玩家文案。与强化台 UColdSteelEnhancementSystem::CanEnchant
     *  的八类键一一对应；未知键如实显示原文，不伪造兼容范围。 */
    struct FEnchantRestrictionLabel { const TCHAR* Key; const TCHAR* Label; };
    const FEnchantRestrictionLabel EnchantRestrictionLabels[] = {
        { TEXT("weapon"),     TEXT("任意武器") },
        { TEXT("firearm"),    TEXT("枪械") },
        { TEXT("melee"),      TEXT("近战武器") },
        { TEXT("meleeOrBow"), TEXT("近战武器或弓") },
        { TEXT("sword"),      TEXT("剑类武器") },
        { TEXT("oneHandedBlade"), TEXT("单手刀／剑") },
        { TEXT("pistol"),     TEXT("手枪") },
        { TEXT("machineGun"), TEXT("轻机枪") },
        { TEXT("sniper"),     TEXT("狙击步枪") },
    };
    FString EnchantRestrictionText(const FString& Key)
    {
        for (const FEnchantRestrictionLabel& R : EnchantRestrictionLabels)
            if (Key == R.Key) return R.Label;
        return Key;
    }

    /** rarity 是否落在祭品/附魔共用的稀有度组序表内；表外（含缺失）由调用方归入「其他」组。 */
    bool MatchesTributeRarity(const FString& Rarity)
    {
        for (int32 Index = 0; Index < TributeRarityCount; ++Index)
            if (Rarity == TributeRarityKeys[Index]) return true;
        return false;
    }

    FString Dash() { return TEXT("—"); }

/** 网格与详情并排／纵排的切换阈值（抽屉内容宽，px）。
 *  抽屉宽度下限 720px、SetLayoutWidth 收到 Width−2，故正常显示器实际为 718–1038px；
 *  阈值取 720 会让两列版式永不出现，取 560 可让常规 1080p 走两列、仓库同开（约 626px）时仍走两列、
 *  更窄（如窄视口叠加左抽屉）才纵排。BuildPage 与 BuildDetail 共用本常量，避免两处阈值漂移。 */
constexpr float StackedBelowWidth = 560.f;

/** 并排时左右两列的宽度占比：左名称列表 1/3、右详情 2/3。
 *  详情占大头才能容下整栏立绘与「说明 + 数值」两列；两处比例集中在此，避免漂移。 */
constexpr float CodexGridShare = 1.f / 3.f;
constexpr float CodexDetailShare = 2.f / 3.f;

    FString FormatNumber(double Value, int32 Decimals)
    {
        if (Decimals <= 0) return FString::Printf(TEXT("%lld"), (int64)FMath::RoundToDouble(Value));
        FString Text = FString::Printf(TEXT("%.*f"), Decimals, Value);
        // 去掉无意义的尾零，保持数值列紧凑。
        if (Text.Contains(TEXT(".")))
        {
            while (Text.EndsWith(TEXT("0"))) Text.LeftChopInline(1);
            if (Text.EndsWith(TEXT("."))) Text.LeftChopInline(1);
        }
        return Text;
    }

    FString RankLabel(EMonsterRank Rank)
    {
        switch (Rank)
        {
        case EMonsterRank::Minor: return TEXT("次级");
        case EMonsterRank::Elite: return TEXT("精英");
        case EMonsterRank::Lord: return TEXT("领主");
        case EMonsterRank::Boss: return TEXT("首领");
        default: return TEXT("普通");
        }
    }
}

void UColdSteelCodexPage::SetHUD(UColdSteelHUDWidget* Owner) { HUD = Owner; }

void UColdSteelCodexPage::SetLayoutWidth(float Pixels)
{
    if (FMath::IsNearlyEqual(PageWidth, Pixels, .5f)) return;
    PageWidth = Pixels;
    RefreshLayout();
}

TSharedRef<SWidget> UColdSteelCodexPage::RebuildWidget()
{
    Model = GetGameInstance() ? GetGameInstance()->GetSubsystem<UColdSteelStatusModel>() : nullptr;
    // 立绘就绪回调只绑定一次：武器与怪物两个工作室分别用同一处理入口。
    if (UGameInstance* GI = GetGameInstance())
    {
        if (auto* Icons = GI->GetSubsystem<UColdSteelWeaponIcons>())
        {
            Icons->OnReady.RemoveAll(this);
            Icons->OnReady.AddUObject(this, &UColdSteelCodexPage::HandlePortraitReady);
        }
        if (auto* Portraits = GI->GetSubsystem<UColdSteelMonsterPortraits>())
        {
            Portraits->OnReady.RemoveAll(this);
            Portraits->OnReady.AddUObject(this, &UColdSteelCodexPage::HandlePortraitReady);
        }
    }
    SAssignNew(Root, SBox);
    RefreshLayout();
    return Root.ToSharedRef();
}

void UColdSteelCodexPage::ReleaseSlateResources(bool bReleaseChildren)
{
    Super::ReleaseSlateResources(bReleaseChildren);
    // 解绑工作室回调，避免页面销毁后仍被 OnReady 引用。
    if (UGameInstance* GI = GetGameInstance())
    {
        if (auto* Icons = GI->GetSubsystem<UColdSteelWeaponIcons>()) Icons->OnReady.RemoveAll(this);
        if (auto* Portraits = GI->GetSubsystem<UColdSteelMonsterPortraits>()) Portraits->OnReady.RemoveAll(this);
    }
    // 搜索框与状态卡片区是跨重建缓存的 Slate 控件，页面销毁时一并放掉。
    SearchEdit.Reset();
    StatusCardsHost.Reset();
    TributeCardsHost.Reset();
    EnchantCardsHost.Reset();
    Root.Reset();
    GridScroll.Reset();
    DetailScroll.Reset();
    GridHost.Reset();
    DetailHost.Reset();
    CardButtons.Reset();
    SectionButtons.Reset();
    CategoryButtons.Reset();
}

void UColdSteelCodexPage::NativeTick(const FGeometry& Geometry, float Delta)
{
    Super::NativeTick(Geometry, Delta);

    // 立绘只在图鉴打开时加载：可见性一变就切换加载状态。
    // 关闭时释放预览工作室与渲染目标（约 6MB 常驻）并丢弃未拍的排队项，
    // 避免「没打开图鉴也在后台拍图」把内存和帧时间吃满。
    const bool bVisibleNow = GetVisibility() != ESlateVisibility::Collapsed
        && GetVisibility() != ESlateVisibility::Hidden;
    if (bVisibleNow != bCodexVisible)
    {
        bCodexVisible = bVisibleNow;
        if (!bCodexVisible) ReleasePortraitResources();
        else EnsureSelectedPortraitQueued();
    }

    if (!FMath::IsNearlyEqual(Scale, ColdSteelUI::PixelScale(this))) RefreshLayout();
}

void UColdSteelCodexPage::ReleasePortraitResources()
{
    // 两个工作室都放掉：图鉴关闭后没有在拍的立绘，也没必要占着预览场景。
    if (UGameInstance* GI = GetGameInstance())
    {
        if (auto* Portraits = GI->GetSubsystem<UColdSteelMonsterPortraits>()) Portraits->ReleaseIdleResources();
    }
}

void UColdSteelCodexPage::EnsureSelectedPortraitQueued()
{
    // 打开图鉴时只请求「当前选中项」一张；没有选中项就什么都不加载，
    // 等玩家点选时再按需请求。绝不在这里预取整份列表。
    if (!SelectedId.IsEmpty()) RequestPortrait(Section == 0, SelectedId);
}

void UColdSteelCodexPage::RefreshLayout()
{
    Scale = ColdSteelUI::PixelScale(this);
    // 分区卡画刷随 DPI 重建；SBorder 取指针，故缓存为成员而不是就地构造临时值。
    // 圆角与描边除以 Scale，与其他面板（DevelopmentPanelWidget／WeatherControlWidget）一致。
    SectionBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::StatusCard,
        ColdSteelUI::CardRadius / FMath::Max(Scale, .01f), ColdSteelUI::Border, 1.f / FMath::Max(Scale, .01f));
    if (Root.IsValid()) Root->SetContent(BuildPage());
}

TSharedRef<SWidget> UColdSteelCodexPage::Label(const FString& Value, float Pixels, const FLinearColor& Color,
    bool bNumeric, bool bMedium) const
{
    const float Units = Pixels * .75f / FMath::Max(Scale, .01f);
    return SNew(STextBlock)
        .Font(bNumeric ? ColdSteelUI::NumberFont(Units, bMedium) : ColdSteelUI::TextFont(Units, bMedium))
        .ColorAndOpacity(FSlateColor(Color))
        .Text(FText::FromString(Value))
        .AutoWrapText(true);
}

TSharedRef<SWidget> UColdSteelCodexPage::TabLabel(const FString& Value, bool bIsActive) const
{
    // 页签文字必须单行横向显示：AutoWrapText(true) 会在等宽窄列里把中文逐字换行成竖排。
    const float Units = 14.f * .75f / FMath::Max(Scale, .01f);
    return SNew(STextBlock)
        .Font(ColdSteelUI::TextFont(Units, bIsActive))
        .ColorAndOpacity(FSlateColor(bIsActive ? ColdSteelUI::TextPrimary : ColdSteelUI::TextSecondary))
        .Text(FText::FromString(Value))
        .AutoWrapText(false)
        .WrapTextAt(0.f);
}

TSharedRef<SWidget> UColdSteelCodexPage::LeftLabel(const FString& Value, float Pixels,
    const FLinearColor& Color, bool bMedium) const
{
    // 列表／卡片内的左对齐单行文字：名称与类别不换行，保证每张卡片行高一致。
    const float Units = Pixels * .75f / FMath::Max(Scale, .01f);
    return SNew(STextBlock)
        .Font(ColdSteelUI::TextFont(Units, bMedium))
        .ColorAndOpacity(FSlateColor(Color))
        .Text(FText::FromString(Value))
        .AutoWrapText(false);
}

TSharedRef<SWidget> UColdSteelCodexPage::ValueLabel(const FString& Value, float Pixels,
    const FLinearColor& Color, bool bMedium) const
{
    // 数值一律单行：JetBrains Mono 数值与单位不需要换行，换行只会在窄列里把数字拆散。
    const float Units = Pixels * .75f / FMath::Max(Scale, .01f);
    return SNew(STextBlock)
        .Font(ColdSteelUI::NumberFont(Units, bMedium))
        .ColorAndOpacity(FSlateColor(Color))
        .Text(FText::FromString(Value))
        .AutoWrapText(false);
}

TSharedRef<SWidget> UColdSteelCodexPage::DetailRow(const FString& Caption, const FString& Value,
    const FLinearColor& ValueColor) const
{
    const float Row = 22.f / FMath::Max(Scale, .01f);
    // 明细行横向排布：左侧说明按内容占宽（单行不换行，避免窄列里逐字竖排），
    // 右侧数值右对齐且单行，行高一致便于纵向扫读。
    return SNew(SHorizontalBox)
        + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
        [ SNew(SBox).MinDesiredWidth(84.f / FMath::Max(Scale, .01f))
          [ LeftLabel(Caption, 14, ColdSteelUI::TextSecondary) ] ]
        + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center).Padding(Row * .5f, 0.f, 0.f, 0.f)
        [ SNew(SBox).HAlign(HAlign_Right)
          [ ValueLabel(Value.IsEmpty() ? Dash() : Value, 14, ValueColor) ] ];
}

TSharedRef<SWidget> UColdSteelCodexPage::SectionCard(const FString& Title,
    const TArray<TSharedRef<SWidget>>& Rows) const
{
    const float Pad = 12.f / FMath::Max(Scale, .01f);
    TSharedRef<SVerticalBox> Body = SNew(SVerticalBox);
    Body->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, Pad * .5f)
        [ Label(Title, 16, ColdSteelUI::TextPrimary, false, true) ];
    for (const TSharedRef<SWidget>& Row : Rows) Body->AddSlot().AutoHeight().Padding(0.f, Pad * .2f)[ Row ];
    return SNew(SBorder)
        .BorderImage(&SectionBrush)
        .Padding(FMargin(Pad, Pad))
        [ Body ];
}

TSharedRef<SWidget> UColdSteelCodexPage::PortraitFrame(bool bWeapon, const FString& Id) const
{
    // 立绘独占一整条横栏：宽度取「详情列可用宽 − 左右内边距」，高度按图片等比推出。
    // 起因链：① 图片曾被塞进固定 132×198 竖框 → SImage 拉满 → 横幅枪械被压扁；
    //          ② 改等比后仍放在与文字并排的 AutoWidth 槽 → 槽宽=图宽，图被限制在窄条内。
    // 现在宽由详情列实际宽度决定，不再有硬编码小上限，图能铺满整条横栏。
    const float ScaleSafe = FMath::Max(Scale, .01f);
    const float Pad = 12.f / ScaleSafe;
    // 并排时详情列 = 内容宽 × 2/3；纵排时详情占满内容宽。两种情形都减去本行的左右内边距。
    const bool bStacked = PageWidth < StackedBelowWidth;
    const float ColumnWidth = bStacked ? PageWidth : PageWidth * CodexDetailShare;
    const float RowWidth = FMath::Max(80.f / ScaleSafe, ColumnWidth - Pad * 2.f);
    const float MaxH = (bWeapon ? 200.f : 240.f) / ScaleSafe;   // 横栏高度上限，防止竖幅近战把详情顶下去

    const FSlateBrush* Brush = PortraitBrush(bWeapon, Id);
    // 横栏容器：整宽、定高、内容居中等比；空态时也占同高，避免行高跳动。
    TSharedRef<SBox> Frame = SNew(SBox)
        .WidthOverride(RowWidth)
        .HeightOverride(MaxH)
        .HAlign(HAlign_Center)
        .VAlign(VAlign_Center);

    if (Brush && Brush->GetResourceObject())
    {
        const FVector2D Source = Brush->ImageSize;
        FVector2D Draw = Source;
        if (Source.X > 0.f && Source.Y > 0.f)
        {
            // 等比 Fit：横幅枪械贴满栏宽、竖幅近战受高度限制而居中，均不变形。
            const float Fit = FMath::Min(RowWidth / float(Source.X), MaxH / float(Source.Y));
            Draw = Source * Fit;
        }
        // 只用 DesiredSizeOverride 给出等比目标尺寸，笔刷仍用工作室缓存里的原始画刷本身——
        // SImage 只持有 const FSlateBrush*，传局部副本的地址会悬空。
        Frame->SetContent(
            SNew(SImage)
            .Image(Brush)
            .DesiredSizeOverride(Draw)
            .ColorAndOpacity(FLinearColor::White));
    }
    else
    {
        // 占位：整条横栏空框 + 居中标状态，不留塌陷、不画灰色假图。
        Frame->SetContent(
            SNew(SBorder)
            .BorderImage(&SectionBrush)
            .Padding(FMargin(0.f))
            [
                SNew(SBox).HAlign(HAlign_Center).VAlign(VAlign_Center)
                [ LeftLabel(TEXT("生成中"), 12, ColdSteelUI::TextTertiary) ]
            ]);
    }
    return Frame;
}

TSharedRef<SWidget> UColdSteelCodexPage::BuildPage()
{
    const float Pad = 16.f / FMath::Max(Scale, .01f);
    const float Gap = 12.f / FMath::Max(Scale, .01f);

    TSharedRef<SVerticalBox> Content = SNew(SVerticalBox);
    Content->AddSlot().AutoHeight().Padding(Pad, Pad * .5f, Pad, Pad * .5f)[ BuildTabs() ];

    // 状态分区独占整页：一张「状态栏卡片」平铺全部条目与说明，不与列表/详情分栏共用布局
    // （2026-09-29 用户要求：进入状态栏后整个页面都留给状态栏显示）。
    if (Section == 2)
    {
        Content->AddSlot().FillHeight(1.f).Padding(Pad, 0.f, Pad, Pad * .5f)[ BuildStatusPage() ];
    }
    // 祭品分区同样整页独占（与状态分区同规则）：搜索栏 + 按稀有度分组的「祭品卡片」。
    else if (Section == 3)
    {
        Content->AddSlot().FillHeight(1.f).Padding(Pad, 0.f, Pad, Pad * .5f)[ BuildTributePage() ];
    }
    // 附魔分区整页独占（与祭品分区同规则，2026-10-03）：搜索栏 + 按稀有度分组的「附魔卡片」。
    else if (Section == 4)
    {
        Content->AddSlot().FillHeight(1.f).Padding(Pad, 0.f, Pad, Pad * .5f)[ BuildEnchantPage() ];
    }
    // 内容宽低于 StackedBelowWidth 时网格与详情纵排；否则左列表右详情。
    // 抽屉宽度本身下限就是 720px（视口 48%、夹在 720–1040px），SetLayoutWidth 收到的是 Width−2，
    // 所以正常显示器上实际宽度约 718–1038px。阈值若取 720 将几乎永远走纵排——两列版式永远不出现。
    else if (PageWidth < StackedBelowWidth)
    {
        Content->AddSlot().FillHeight(1.f).Padding(Pad, 0.f, Pad, Gap)[ BuildGrid() ];
        Content->AddSlot().AutoHeight().Padding(Pad, 0.f, Pad, Pad * .5f)[ BuildDetail() ];
    }
    else
    {
        Content->AddSlot().FillHeight(1.f).Padding(Pad, 0.f, Pad, Pad * .5f)
        [
            SNew(SHorizontalBox)
            // 左列表 1/3、右详情 2/3：详情要放宽才能容下整栏立绘与两列数值。
            // 用 GridShare/DetailShare 两个常量集中表达，避免两处比例漂移。
            + SHorizontalBox::Slot().FillWidth(CodexGridShare).Padding(0.f, 0.f, Gap * .5f, 0.f)[ BuildGrid() ]
            + SHorizontalBox::Slot().FillWidth(CodexDetailShare).Padding(Gap * .5f, 0.f, 0.f, 0.f)[ BuildDetail() ]
        ];
    }
    Content->AddSlot().AutoHeight().Padding(Pad, 0.f, Pad, Pad)
        [ SNew(SBox).HAlign(HAlign_Center)
          [ LeftLabel(TEXT("N 收起  ·  Caps 状态  ·  Tab 背包  ·  P 技能"), 12, ColdSteelUI::TextTertiary) ] ];
    return Content;
}

TSharedRef<SWidget> UColdSteelCodexPage::BuildTabs()
{
    const float Height = ColdSteelUI::ActionHeight / FMath::Max(Scale, .01f);
    const float Gap = ColdSteelUI::ActionGap / FMath::Max(Scale, .01f);
    const float Pad = 14.f / FMath::Max(Scale, .01f);
    ActionStyle = ColdSteelUI::ButtonStyle(Scale);
    // 选中态是同源副本，只换普通态画刷；Slate 的 .ButtonStyle() 取指针，故使用成员样式。
    // 圆角与描边同样除以 Scale，与 ButtonStyle 内部一致（否则高 DPI 下选中页签会变方角粗边）。
    ActionActiveStyle = ActionStyle;
    ActionActiveStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover,
        ColdSteelUI::ButtonRadius / FMath::Max(Scale, .01f), ColdSteelUI::Accent, 1.f / FMath::Max(Scale, .01f)));

    // 页签一律横向排布、文字不换行：等宽列会把「近战武器」「生产工具」压成竖排单字，
    // 因此主分区按比例分宽（1:1），分类页签按文字宽度自适应（AutoWidth + ContentPadding）并整体居中。
    // 文本走 TabLabel（AutoWrapText(false)），与技能页 FilterButtons 的单行标签同规格。
    SectionButtons.Reset();
    TSharedRef<SHorizontalBox> Sections = SNew(SHorizontalBox);
    const TCHAR* SectionLabels[] = {TEXT("武器"), TEXT("怪物"), TEXT("状态"), TEXT("祭品"), TEXT("附魔")};
    for (int32 Index = 0; Index < UE_ARRAY_COUNT(SectionLabels); ++Index)
    {
        const bool bActive = Index == Section;
        TSharedPtr<SButton> Button;
        Sections->AddSlot().FillWidth(1.f)
            .Padding(Index == 0 ? 0.f : Gap * .5f, 0.f, Index == 0 ? Gap * .5f : 0.f, Gap * .6f)
        [
            SAssignNew(Button, SButton)
            .ButtonStyle(bActive ? &ActionActiveStyle : &ActionStyle)
            .HAlign(HAlign_Center).VAlign(VAlign_Center)
            .OnClicked(FOnClicked::CreateLambda([this, Index]() { return SelectSection(Index); }))
            [ SNew(SBox).HeightOverride(Height).VAlign(VAlign_Center).HAlign(HAlign_Center)
              [ TabLabel(SectionLabels[Index], bActive) ] ]
        ];
        SectionButtons.Add(Button);
    }

    CategoryButtons.Reset();
    TSharedRef<SHorizontalBox> Categories = SNew(SHorizontalBox);
    const TArray<FString> CategoryNames = this->Categories();
    for (int32 Index = 0; Index < CategoryNames.Num(); ++Index)
    {
        const bool bActive = Index == Category;
        TSharedPtr<SButton> Button;
        // 左右各留 Pad 的内容内边距，配合 AutoWidth 让按钮宽度贴合文字，不再等分挤压。
        Categories->AddSlot().AutoWidth().VAlign(VAlign_Center)
            .Padding(Index == 0 ? 0.f : Gap * .5f, 0.f, 0.f, 0.f)
        [
            SAssignNew(Button, SButton)
            .ButtonStyle(bActive ? &ActionActiveStyle : &ActionStyle)
            .HAlign(HAlign_Center).VAlign(VAlign_Center)
            .ContentPadding(FMargin(Pad, 0.f))
            .OnClicked(FOnClicked::CreateLambda([this, Index]() { return SelectCategory(Index); }))
            [ SNew(SBox).HeightOverride(Height * .82f).VAlign(VAlign_Center).HAlign(HAlign_Center)
              [ TabLabel(CategoryNames[Index], bActive) ] ]
        ];
        CategoryButtons.Add(Button);
    }
    // 分类页签整体居中，避免窄抽屉里挤在左侧。
    return SNew(SVerticalBox)
        + SVerticalBox::Slot().AutoHeight()[ Sections ]
        + SVerticalBox::Slot().AutoHeight().HAlign(HAlign_Center)[ Categories ];
}

TSharedRef<SWidget> UColdSteelCodexPage::BuildGrid()
{
    CardButtons.Reset();
    // 圆角与描边必须除以 Scale：RoundedBrush 接收的是 Slate 单位，ButtonStyle(Scale) 内部同样除法。
    // 传原始像素值会在高 DPI 下让圆角偏小、描边偏粗，卡片看起来是方角加粗边。
    const float Radius = ColdSteelUI::CardRadius / FMath::Max(Scale, .01f);
    const float Hairline = 1.f / FMath::Max(Scale, .01f);
    CardStyle = ColdSteelUI::ButtonStyle(Scale);
    CardStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::AttributeRow, Radius, ColdSteelUI::Border, Hairline));
    CardStyle.SetHovered(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonHover, Radius, ColdSteelUI::Border, Hairline));
    CardStyle.SetPressed(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonPressed, Radius, ColdSteelUI::Accent, Hairline));
    CardActiveStyle = CardStyle;
    CardActiveStyle.SetNormal(ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonNormal, Radius, ColdSteelUI::Accent, Hairline * 2.f));

    const TArray<FCodexEntry> List = Entries();
    const float Pad = 10.f / FMath::Max(Scale, .01f);
    const float RowGap = 8.f / FMath::Max(Scale, .01f);

    TSharedRef<SVerticalBox> Rows = SNew(SVerticalBox);
    if (List.IsEmpty())
    {
        Rows->AddSlot().AutoHeight().Padding(Pad, Pad * 1.5f)
            [ Label(Section == 0 ? TEXT("此分类暂无武器档案") : Section == 2 ? TEXT("此分类暂无状态档案")
                : Section == 3 ? TEXT("此分类暂无祭品档案") : TEXT("此分类暂无怪物档案"), 14, ColdSteelUI::TextTertiary) ];
    }
    else
    {
        for (int32 Index = 0; Index < List.Num(); ++Index)
        {
            const FCodexEntry Entry = List[Index];
            TSharedPtr<SButton> Button;
            // 卡片内两行结构：首行「名称 …… 战力」（横向两端对齐，怪物栏才显示战力），
            // 次行类别。名称单行不换行，避免长名把卡片撑成多行错位。
            TSharedRef<SHorizontalBox> Head = SNew(SHorizontalBox)
                + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
                [ LeftLabel(Entry.Name, 14, ColdSteelUI::TextPrimary, Entry.Id == SelectedId) ];
            if (Section == 1)
            {
                Head->AddSlot().AutoWidth().VAlign(VAlign_Center).Padding(Pad * .5f, 0.f, 0.f, 0.f)
                    [ SNew(SBox).HAlign(HAlign_Right)
                      [ ValueLabel(FString::Printf(TEXT("战力 %d"), Entry.CombatLevel), 12, ColdSteelUI::TextSecondary) ] ];
            }
            TSharedRef<SVerticalBox> Card = SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()[ Head ]
                + SVerticalBox::Slot().AutoHeight().Padding(0.f, Pad * .25f, 0.f, 0.f)
                [ LeftLabel(Entry.Subtitle, 12, ColdSteelUI::TextTertiary, false) ];
            Rows->AddSlot().AutoHeight().Padding(0.f, Index == 0 ? 0.f : RowGap, 0.f, 0.f)
            [
                SAssignNew(Button, SButton)
                .ButtonStyle(Entry.Id == SelectedId ? &CardActiveStyle : &CardStyle)
                .HAlign(HAlign_Fill).VAlign(VAlign_Center)
                .OnClicked(FOnClicked::CreateLambda([this, Id = Entry.Id]() { return SelectEntry(Id); }))
                [ SNew(SBox).Padding(FMargin(Pad, Pad * .8f))[ Card ] ]
            ];
            CardButtons.Add(Button);
        }
    }
    SAssignNew(GridScroll, SScrollBox);
    GridScroll->SetAllowOverscroll(EAllowOverscroll::No);
    ColdSteelUI::ApplyGoldScroll(GridScroll.ToSharedRef(), FVector2D(6.f / FMath::Max(Scale, .01f)), FMargin(4.f / FMath::Max(Scale, .01f), 0.f, 0.f, 0.f), true);
    GridScroll->AddSlot()[ Rows ];
    SAssignNew(GridHost, SBox);
    GridHost->SetContent(GridScroll.ToSharedRef());
    return GridHost.ToSharedRef();
}

TSharedRef<SWidget> UColdSteelCodexPage::BuildDetail()
{
    const float Pad = 12.f / FMath::Max(Scale, .01f);
    const float CardGap = 10.f / FMath::Max(Scale, .01f);
    TSharedRef<SVerticalBox> Detail = SNew(SVerticalBox);

    if (SelectedId.IsEmpty())
    {
        Detail->AddSlot().AutoHeight().Padding(Pad)
            [ Label(TEXT("从左侧选择条目查看档案详情"), 14, ColdSteelUI::TextTertiary) ];
    }
    else
    {
        const TArray<FCodexEntry> List = Entries();
        const FCodexEntry* Found = List.FindByPredicate([this](const FCodexEntry& E) { return E.Id == SelectedId; });
        // 选中条目可能已被分类切换过滤掉；此时直接按 Id 读取，详情与列表不共用过滤结果。
        FString Name = Found ? Found->Name : (Section == 0 ? CatalogName(SelectedId) : SelectedId);
        if (Name.IsEmpty()) Name = SelectedId;
        const FString Subtitle = Found ? Found->Subtitle : SectionLabel();

        // 详情头：立绘**独占一整条横栏**（整宽、居中等比），名称与类别在下一行。
        // 先前把立绘放在 AutoWidth 槽里与文字并排，槽宽只等于图片自身宽度，
        // 于是图片始终被限制在窄条内——这就是「还是压缩在小范围」的原因。
        // 现在立绘是整宽横栏，缩放上限由详情列实际宽度决定（见 PortraitFrame）。
        // 状态分区无立绘（图标为字体字形，直接进入卡片行），不画占位横栏。
        if (Section != 2)
        {
            Detail->AddSlot().AutoHeight().Padding(Pad, Pad, Pad, CardGap * .6f)
                [ PortraitFrame(Section == 0, SelectedId) ];
        }

        Detail->AddSlot().AutoHeight().Padding(Pad, 0.f, Pad, CardGap)
        [
            SNew(SVerticalBox)
            + SVerticalBox::Slot().AutoHeight()[ Label(Name, 20, ColdSteelUI::TextPrimary, false, true) ]
            + SVerticalBox::Slot().AutoHeight().Padding(0.f, Pad * .3f, 0.f, 0.f)
              [ Label(Subtitle, 12, ColdSteelUI::TextSecondary) ]
        ];

        const TArray<TSharedRef<SWidget>> Rows = Section == 0
            ? WeaponDetailRows(SelectedId)
            : MonsterDetailRows(SelectedId);

        TSharedRef<SVerticalBox> Cards = SNew(SVerticalBox);
        for (int32 Index = 0; Index < Rows.Num(); ++Index)
            Cards->AddSlot().AutoHeight().Padding(0.f, Index == 0 ? 0.f : CardGap, 0.f, 0.f)[ Rows[Index] ];

        TSharedPtr<SScrollBox> Scroll;
        SAssignNew(Scroll, SScrollBox);
        Scroll->SetAllowOverscroll(EAllowOverscroll::No);
        ColdSteelUI::ApplyGoldScroll(Scroll.ToSharedRef(), FVector2D(6.f / FMath::Max(Scale, .01f)), FMargin(4.f / FMath::Max(Scale, .01f), 0.f, 0.f, 0.f), true);
        Scroll->AddSlot().Padding(Pad, 0.f, Pad, Pad)[ Cards ];
        DetailScroll = Scroll;
        Detail->AddSlot().FillHeight(1.f)[ Scroll.ToSharedRef() ];

        Detail->AddSlot().AutoHeight().Padding(Pad, CardGap, Pad, Pad)
        [
            SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight / FMath::Max(Scale, .01f))
            [
                SNew(SButton).ButtonStyle(&ActionStyle)
                .HAlign(HAlign_Center).VAlign(VAlign_Center)
                .OnClicked(FOnClicked::CreateLambda([this]() { return CloseDetail(); }))
                // 与页签同一原因：按钮标签必须单行，否则在窄列里会逐字竖排成「返／回」。
                [ SNew(SBox).HAlign(HAlign_Center).VAlign(VAlign_Center)
                  [ LeftLabel(TEXT("返回列表"), 14, ColdSteelUI::TextPrimary) ] ]
            ]
        ];
    }

    SAssignNew(DetailHost, SBox);
    // 纵排时详情保留至少 420px 高以容纳完整分组；并排时随抽屉高度填满。
    // 阈值必须与 BuildPage 的纵排阈值一致，否则会出现「按并排排版却要求 420px 最小高」的矛盾约束。
    if (PageWidth < StackedBelowWidth) DetailHost->SetMinDesiredHeight(420.f);
    DetailHost->SetContent(Detail);
    return DetailHost.ToSharedRef();
}

FReply UColdSteelCodexPage::SelectSection(int32 Index)
{
    if (Section != Index) { Section = Index; Category = 0; SelectedId.Reset(); }
    RefreshLayout();
    return FReply::Handled();
}

FReply UColdSteelCodexPage::SelectCategory(int32 Index)
{
    if (Category != Index) { Category = Index; SelectedId.Reset(); }
    RefreshLayout();
    return FReply::Handled();
}

FReply UColdSteelCodexPage::SelectEntry(const FString& Id)
{
    SelectedId = Id;
    // 选中即请求立绘：未出图时先渲染，完成后经 OnReady 回来重建详情。
    RequestPortrait(Section == 0, Id);
    RefreshLayout();
    if (DetailScroll.IsValid()) DetailScroll->SetScrollOffset(0.f);
    return FReply::Handled();
}

FReply UColdSteelCodexPage::CloseDetail()
{
    SelectedId.Reset();
    RefreshLayout();
    return FReply::Handled();
}

