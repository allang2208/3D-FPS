#include "ColdSteelCodexPage.h"
#include "ColdSteelWeaponText.h"
#include "ColdSteelHUDWidget.h"
#include "../FPSGAMEPlayerController.h"
#include "ColdSteelStatusModel.h"
#include "ColdSteelInventoryTypes.h"
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

namespace
{
    /** 武器分类索引：与原项目 codex-manager 的 equipCategories 同序（去掉本工程没有的防具／饰品）。 */
    const TCHAR* WeaponCategoryKeys[] = {TEXT("all"), TEXT("weapon_ranged"), TEXT("weapon_melee"), TEXT("tool"), TEXT("equipment")};
    const TCHAR* WeaponCategoryLabels[] = {TEXT("全部"), TEXT("枪械"), TEXT("近战武器"), TEXT("生产工具"), TEXT("装备")};
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
    struct FStatusGroupDef { const TCHAR* Key; const TCHAR* Label; const TCHAR* Note; };
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
    const int32 TributeRarityCount = UE_ARRAY_COUNT(TributeRarityKeys);
    static_assert(UE_ARRAY_COUNT(TributeRarityKeys) == UE_ARRAY_COUNT(TributeRarityLabels),
        "祭品稀有度键与标签表长度必须一致");

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

    FString FormatNumber(double Value, int32 Decimals = 0)
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
    const TCHAR* SectionLabels[] = {TEXT("武器"), TEXT("怪物"), TEXT("状态"), TEXT("祭品")};
    for (int32 Index = 0; Index < 4; ++Index)
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
    GridScroll->SetScrollBarThickness(FVector2D(6.f / FMath::Max(Scale, .01f)));
    // 与右侧详情列保持同一滚动条行为：按需出现，不常驻。两列一常驻一按需会让中缝宽度随滚动跳动。
    GridScroll->SetAllowOverscroll(EAllowOverscroll::No);
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
        Scroll->SetScrollBarThickness(FVector2D(6.f / FMath::Max(Scale, .01f)));
        Scroll->SetAllowOverscroll(EAllowOverscroll::No);
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

TArray<FString> UColdSteelCodexPage::Categories() const
{
    TArray<FString> Names;
    if (Section == 0)
    {
        for (int32 Index = 0; Index < WeaponCategoryCount; ++Index) Names.Add(WeaponCategoryLabels[Index]);
    }
    else if (Section == 2)
    {
        for (int32 Index = 0; Index < StatusCategoryCount; ++Index) Names.Add(StatusCategoryLabels[Index]);
    }
    else if (Section == 3)
    {
        Names.Add(TEXT("全部"));
        for (int32 Index = 0; Index < TributeRarityCount; ++Index) Names.Add(TributeRarityLabels[Index]);
    }
    else
    {
        for (int32 Index = 0; Index < MonsterCategoryCount; ++Index) Names.Add(MonsterCategoryLabels[Index]);
    }
    return Names;
}

FString UColdSteelCodexPage::SectionLabel() const
{
    return Section == 0 ? TEXT("武器档案") : Section == 2 ? TEXT("状态栏")
        : Section == 3 ? TEXT("祭品") : TEXT("怪物档案");
}

FString UColdSteelCodexPage::CatalogName(const FString& Definition) const
{
    if (!Model) return FString();
    for (const FColdSteelCatalogEntry& Entry : Model->ItemCatalog())
        if (Entry.Definition == Definition) return Entry.Name;
    return FString();
}

FString UColdSteelCodexPage::WeaponCategoryOf(const FColdSteelItem& Item) const
{
    // 归类只按物品自身的 category／weaponType（与运行时同一字段），不从名称或图标猜测。
    // category 取值对齐 ClassifyItem 已承认的武器类别：weapon／weapon_ranged／weapon_magic 都是枪械，
    // weapon_melee 是近战武器，tool 是生产工具；其余（材料／消耗品／祭品等）不进图鉴。
    const FString CategoryField = ColdSteelInventory::Text(Item, TEXT("category"));
    if (CategoryField == TEXT("equipment")) return TEXT("equipment");
    if (CategoryField == TEXT("tool")) return TEXT("tool");
    if (CategoryField == TEXT("weapon_melee")) return TEXT("weapon_melee");
    if (CategoryField == TEXT("weapon") || CategoryField == TEXT("weapon_ranged") || CategoryField == TEXT("weapon_magic")) return TEXT("weapon_ranged");
    // 类别缺失时以 weaponType 兜底（近战三类归近战，其余武器归枪械）。
    const FString WeaponType = ColdSteelInventory::Text(Item, TEXT("weaponType"));
    if (WeaponType == TEXT("sword") || WeaponType == TEXT("axe") || WeaponType == TEXT("pickaxe") || WeaponType == TEXT("claymore")) return TEXT("weapon_melee");
    if (!WeaponType.IsEmpty()) return TEXT("weapon_ranged");
    return TEXT("all");
}

const UDevelopmentSpawnComponent* UColdSteelCodexPage::ResolveSpawner() const
{
    // 生成登记表挂在 PlayerController 上（FPSGAMEPlayerController 构造里
    // CreateDefaultSubobject DevelopmentSpawner），不在 Pawn 上。原先按 Pawn
    // FindComponentByClass 取，永远拿不到，导致怪物分区恒为空。
    // 与 DevelopmentPanelWidget::ResolveSpawner 取同一入口。
    const auto* Player = GetOwningPlayer<AFPSGAMEPlayerController>();
    return Player ? Player->GetDevelopmentSpawner() : nullptr;
}

const FSlateBrush* UColdSteelCodexPage::PortraitBrush(bool bWeapon, const FString& Id) const
{
    UGameInstance* GI = GetGameInstance();
    if (!GI) return nullptr;
    if (bWeapon)
    {
        // 武器复用背包同一图标工作室：固定正交相机、FRotator::ZeroRotator，朝向天然统一。
        if (!Model) return nullptr;
        const FColdSteelItem Item = Model->CreateItem(Id);
        auto* Icons = GI->GetSubsystem<UColdSteelWeaponIcons>();
        return Icons ? Icons->Find(Item) : nullptr;
    }
    auto* Portraits = GI->GetSubsystem<UColdSteelMonsterPortraits>();
    return Portraits ? Portraits->Find(Id) : nullptr;
}

void UColdSteelCodexPage::HandlePortraitReady(const FString& Id)
{
    // 只重建当前选中项的详情；其他条目的图会在被选中时自然取到。
    if (SelectedId.IsEmpty() || SelectedId != Id) return;
    // 武器与怪物两个工作室共用本入口，仅凭 Id 无法区分来源（今日两套 Id 无交集，属巧合而非约束）。
    // 因此按「当前分区里是否真有这个 Id」判定：武器查物品目录的武器归类，怪物查生成登记表。
    // 这样即使日后出现同名条目，也不会让另一个分区的工作室误触发重建。
    bool bBelongsHere = false;
    if (Section == 0)
    {
        if (Model)
        {
            for (const FColdSteelCatalogEntry& Entry : Model->ItemCatalog())
                if (Entry.Definition == Id) { bBelongsHere = WeaponCategoryOf(Model->CreateItem(Id)) != TEXT("all"); break; }
        }
    }
    else if (const UDevelopmentSpawnComponent* Spawner = ResolveSpawner())
    {
        bBelongsHere = Spawner->GetMonsters().ContainsByPredicate(
            [&Id](const FDevelopmentMonsterEntry& E) { return E.Id.ToString() == Id; });
    }
    if (bBelongsHere) RefreshLayout();
}

void UColdSteelCodexPage::RequestPortrait(bool bWeapon, const FString& Id) const
{
    UGameInstance* GI = GetGameInstance();
    if (!GI) return;
    if (bWeapon)
    {
        if (!Model) return;
        if (auto* Icons = GI->GetSubsystem<UColdSteelWeaponIcons>()) Icons->Request(Model->CreateItem(Id));
        return;
    }
    // 怪物按身份从生成登记表取类：与图鉴列表同一来源，不另建名单。
    const UDevelopmentSpawnComponent* Spawner = ResolveSpawner();
    if (!Spawner) return;
    const FDevelopmentMonsterEntry* Entry = Spawner->GetMonsters().FindByPredicate(
        [&Id](const FDevelopmentMonsterEntry& E) { return E.Id.ToString() == Id; });
    if (!Entry) return;
    // 玩家点选的那张优先：插到队首，排在已排队的预取项之前。
    if (auto* Portraits = GI->GetSubsystem<UColdSteelMonsterPortraits>()) Portraits->RequestPriority(*Entry);
}

bool UColdSteelCodexPage::MonsterStatsOf(const FDevelopmentMonsterEntry& Entry, FMonsterCoreStats& Out) const
{
    // 身份与六维在运行期不变，缓存避免每次重建都 LoadSynchronous 并重算。
    // 键是登记表条目 Id，登记表增删身份时未命中的新条目会走一次求值，已缓存的条目不受影响。
    if (const TPair<bool, FMonsterCoreStats>* Found = MonsterStatsCache.Find(Entry.Id))
    {
        Out = Found->Value;
        return Found->Key;
    }
    const UClass* Class = Entry.CharacterClass.LoadSynchronous();
    FMonsterCoreStats Stats;
    const bool bKnown = Class && MonsterCoreStats::Get(Class->GetDefaultObject<AActor>(), Stats);
    MonsterStatsCache.Add(Entry.Id, TPair<bool, FMonsterCoreStats>(bKnown, Stats));
    Out = Stats;
    return bKnown;
}

TArray<UColdSteelCodexPage::FCodexEntry> UColdSteelCodexPage::Entries() const
{
    TArray<FCodexEntry> Result;
    if (Section == 0)
    {
        if (!Model) return Result;
        const FString Key = WeaponCategoryKeys[FMath::Clamp(Category, 0, WeaponCategoryCount - 1)];
        for (const FColdSteelCatalogEntry& Entry : Model->ItemCatalog())
        {
            // 栏目归属只看物品自身的 category／weaponType；Entry.Group 是开发面板的下拉分类，
            // 生产工具在其中归入「其他」，不能用来判断武器／工具。
            const FColdSteelItem Probe = Model->CreateItem(Entry.Definition);
            const FString Own = WeaponCategoryOf(Probe);
            // 图鉴只收录可装备武器与生产工具；弹药、材料、消耗品不在本栏。
            if (Own == TEXT("all")) continue;
            if (Key != TEXT("all") && Own != Key) continue;
            FCodexEntry Row;
            Row.Id = Entry.Definition;
            Row.Name = Entry.Name;
            Row.Category = Own;
            // 副标题显示玩家能理解的类别名，而不是开发面板的内部分组。
            const FString Type = ColdSteelInventory::Text(Probe, TEXT("type"));
            Row.Subtitle = !Type.IsEmpty() ? Type : Entry.Group;
            Result.Add(MoveTemp(Row));
        }
    }
    else if (Section == 2)
    {
        // 状态目录（AllDefinitions 已按名称排序）：Category=kind（buff/debuff）。
        // 注意必须在怪物分支之前：怪物分支的条件是“登记表存在”（恒真），放后面永远轮不到。
        TArray<FStatusEffectView> Catalog;
        UStatusEffectsComponent::AllDefinitions(Catalog);
        const FString Key = StatusCategoryKinds[FMath::Clamp(Category, 0, StatusCategoryCount - 1)];
        for (const FStatusEffectView& V : Catalog)
        {
            if (Key != TEXT("all") && V.Kind.ToString() != Key) continue;
            FCodexEntry Row;
            Row.Id = V.Type.ToString();
            Row.Name = V.Name.IsEmpty() ? Row.Id : V.Name;
            Row.Category = V.Kind.ToString();
            Row.Subtitle = V.Kind == TEXT("debuff") ? TEXT("减益") : TEXT("增益");
            Row.SortKey = V.Kind == TEXT("debuff") ? 1 : 0;
            Result.Add(MoveTemp(Row));
        }
    }
    else if (Section == 3)
    {
        // 祭品分区走整页卡片（TributePageCards），不使用网格列表条目；
        // 此分支必须在恒真的怪物登记表分支之前，否则会被误吞。
    }
    else if (const UDevelopmentSpawnComponent* Spawner = ResolveSpawner())
    {
        for (const FDevelopmentMonsterEntry& Entry : Spawner->GetMonsters())
        {
            FCodexEntry Row;
            Row.Id = Entry.Id.ToString();
            Row.Name = Entry.Name.ToString();
            FMonsterCoreStats Stats;
            // 蓝图类未加载或身份未登记时不丢弃条目：仍列出，数值显示为不可用。
            if (!MonsterStatsOf(Entry, Stats))
            {
                Row.Subtitle = TEXT("未登记属性");
                Row.SortKey = 99;
                if (Category > 1) continue;
                Result.Add(MoveTemp(Row));
                continue;
            }
            Row.Subtitle = RankLabel(Stats.Rank);
            Row.CombatLevel = MonsterCoreStats::CombatLevel(Stats, 0., 0.);
            Row.SortKey = (int32)Stats.Rank;
            // 按品阶过滤：用页签→品阶映射表比对，不做下标算术（两者编号不同，见表定义处注释）。
            if (Category != 0 && Category < MonsterCategoryCount &&
                Stats.Rank != MonsterCategoryRanks[Category]) continue;
            Result.Add(MoveTemp(Row));
        }
        Result.Sort([](const FCodexEntry& A, const FCodexEntry& B)
        {
            if (A.SortKey != B.SortKey) return A.SortKey < B.SortKey;
            return A.Name < B.Name;
        });
    }

    return Result;
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

TArray<TSharedRef<SWidget>> UColdSteelCodexPage::WeaponDetailRows(const FString& Definition) const
{
    TArray<TSharedRef<SWidget>> Cards;
    if (!Model) return Cards;
    const FColdSteelItem Probe = Model->CreateItem(Definition);

    {
        TArray<TSharedRef<SWidget>> Rows;
        Rows.Add(DetailRow(TEXT("名称"), ColdSteelInventory::Text(Probe, TEXT("name")), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("类型"), ColdSteelInventory::Text(Probe, TEXT("type")), ColdSteelUI::TextPrimary));
        const FString Rarity = ColdSteelInventory::Text(Probe, TEXT("rarity"));
        Rows.Add(DetailRow(TEXT("稀有度"), ColdSteelUI::RarityLabel(Rarity), ColdSteelUI::RarityColor(Rarity)));
        Rows.Add(DetailRow(TEXT("持握"), ColdSteelInventory::Flag(Probe, TEXT("isTwoHanded")) ? TEXT("双手") : TEXT("单手"), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("装备槽"), ColdSteelInventory::Text(Probe, TEXT("equipSlot")), ColdSteelUI::TextPrimary));
        Cards.Add(SectionCard(TEXT("基本信息"), Rows));
    }

    // 战斗数值与物品浮窗、运行时走同一口径：改造目录 FGunsmithStats 为基础，
    // 再由 ColdSteelWeaponStats 施加敏捷／附魔／加工等后处理。不读物品 Data 里不存在的字段。
    const UGunsmithSystem* Gunsmith = GetGameInstance() ? GetGameInstance()->GetSubsystem<UGunsmithSystem>() : nullptr;
    const FGunsmithWeapon* Weapon = Gunsmith ? Gunsmith->Weapon(Definition) : nullptr;
    if (ColdSteelInventory::Text(Probe, TEXT("category")) == TEXT("equipment"))
    {
        // 装备（2026-09-30 方案 A 进图鉴）：防具/手套走物品 Data 的 stats 数组与说明——
        // 与背包浮窗同一字段；装备无枪械/近战/工具数值，不伪造，也不显示"无参数"占位卡。
        TArray<TSharedRef<SWidget>> Rows;
        TSharedPtr<FJsonObject> Data;
        const TArray<TSharedPtr<FJsonValue>>* Stats = nullptr;
        if (!Probe.Data.IsEmpty() && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Probe.Data), Data) &&
            Data->TryGetArrayField(TEXT("stats"), Stats) && Stats)
            for (const TSharedPtr<FJsonValue>& S : *Stats)
                if (const TSharedPtr<FJsonObject> O = S.IsValid() ? S->AsObject() : nullptr)
                {
                    const FString Sn = O->GetStringField(TEXT("name"));
                    const FString Sv = O->GetStringField(TEXT("value"));
                    if (!Sn.IsEmpty() || !Sv.IsEmpty())
                        Rows.Add(DetailRow(Sn, Sv, ColdSteelUI::TextPrimary));
                }
        if (Rows.IsEmpty()) Rows.Add(Label(TEXT("目录未提供装备属性。"), 12, ColdSteelUI::TextTertiary));
        Cards.Add(SectionCard(TEXT("装备属性"), Rows));
        const FString Desc = ColdSteelInventory::Text(Probe, TEXT("desc"));
        if (!Desc.IsEmpty())
        {
            TArray<TSharedRef<SWidget>> DescRows;
            DescRows.Add(Label(Desc, 14, ColdSteelUI::TextSecondary));
            Cards.Add(SectionCard(TEXT("物品说明"), DescRows));
        }
    }
    else if (Gunsmith && Gunsmith->IsTool(Definition))
    {
        // 采集工具：图鉴给出厂口径的采集与自卫实值，与物品浮窗、工作台走同一评估入口。
        // 玩家实例上的改造不进图鉴（图鉴不读物品 Data）。
        const FProductionToolStats Tool = ColdSteelTool::Evaluate(Probe, Model);
        TArray<TSharedRef<SWidget>> Rows;
        Rows.Add(DetailRow(TEXT("自卫总伤害"), FormatNumber(Tool.Damage.Total(), 1), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(ColdSteelWeaponText::AttackInterval, FormatNumber(Tool.SwingSeconds, 2) + TEXT(" s"), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("体力消耗"), FormatNumber(Tool.StaminaCost, 1), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(ColdSteelWeaponText::AttackDistance, FormatNumber(Tool.CombatReachCM / 100., 2) + TEXT(" m"), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("采集距离"), FormatNumber(Tool.HarvestReachCM / 100., 2) + TEXT(" m"), ColdSteelUI::TextSecondary));
        // 树木与岩块都按生命值结算（2026-09-30 岩块统一）：图鉴列一次挥砍的伤害与
        // 标准树（A 树 60 点）/标准岩（60 点）所需挥砍，挥砍数由伤害对生命求出。
        if (ColdSteelInventory::Text(Probe, TEXT("tool_kind")) == TEXT("pickaxe"))
        {
            Rows.Add(DetailRow(TEXT("采矿伤害"), FormatNumber(ProductionTreeHealth::StrikeDamage(Tool), 1) + TEXT(" / 挥"), ColdSteelUI::TextSecondary));
            Rows.Add(DetailRow(TEXT("标准岩所需挥砍"), FString::Printf(TEXT("%d 次"),
                ProductionTreeHealth::SwingsToFell(ProductionTreeHealth::RockMaxHealth(), ProductionTreeHealth::StrikeDamage(Tool))), ColdSteelUI::TextSecondary));        }
        else
        {
            Rows.Add(DetailRow(TEXT("伐木伤害"), FormatNumber(ProductionTreeHealth::StrikeDamage(Tool), 1) + TEXT(" / 挥"), ColdSteelUI::TextSecondary));
            Rows.Add(DetailRow(TEXT("标准树所需挥砍"), FString::Printf(TEXT("%d 次"),
                ProductionTreeHealth::SwingsToFell(ProductionTreeHealth::BaseHealth(0), ProductionTreeHealth::StrikeDamage(Tool))), ColdSteelUI::TextSecondary));
        }
        Rows.Add(DetailRow(TEXT("采集产出倍率"), FormatNumber(Tool.HarvestYield, 2) + TEXT("×"), ColdSteelUI::TextSecondary));
        Rows.Add(DetailRow(TEXT("改造栏目"), TEXT("握把 · 握柄 · 改件 · 主部件"), ColdSteelUI::TextSecondary));
        Cards.Add(SectionCard(TEXT("采集工具数值"), Rows));

        // 强化阶梯表：图鉴读出厂 Probe，没有实例等级，因此只列全 5 档材质阶梯，
        // 不显示「某件工具现在是几级」。等级与材质名来自 `ColdSteelToolEnhance`，
        // 与工作台第五栏、浮窗读同一份目录；cost／stats 本次恒空，这里如实写「待定」。
        const TArray<FToolEnhanceLevel>& Levels = ColdSteelToolEnhance::Levels();
        if (!Levels.IsEmpty())
        {
            TArray<TSharedRef<SWidget>> EnhanceRows;
            for (const FToolEnhanceLevel& Entry : Levels)
            {
                // 一行一档：等级 → 材质名，右侧说明用目录 description（不改写、不补数字）。
                EnhanceRows.Add(DetailRow(FString::Printf(TEXT("Lv.%d"), Entry.Level), Entry.Name,
                    Entry.Level == 1 ? ColdSteelUI::TextSecondary : ColdSteelUI::TextPrimary));
                if (!Entry.Description.IsEmpty())
                    EnhanceRows.Add(DetailRow(TEXT(""), Entry.Description, ColdSteelUI::TextSecondary));
            }
            EnhanceRows.Add(DetailRow(TEXT("等级规则"), TEXT("逐级 +1 提升，不可降级、不可跳级；出厂为 Lv.1"), ColdSteelUI::TextSecondary));
            EnhanceRows.Add(DetailRow(TEXT("强化消耗"), TEXT("待定"), ColdSteelUI::TextSecondary));
            EnhanceRows.Add(DetailRow(TEXT("强化数值"), TEXT("待定 · 强化只更换金属部位材质，不影响采集与自卫数值"), ColdSteelUI::TextSecondary));
            Cards.Add(SectionCard(TEXT("工具强化材质阶梯"), EnhanceRows));
        }
    }
    else if (Weapon)
    {
        const FGunsmithStats Stats = Gunsmith->Calculate(Definition, FGunsmithParts());
        const bool bMelee = Gunsmith->IsMelee(Definition);
        TArray<TSharedRef<SWidget>> Rows;
        if (bMelee)
        {
            const auto Melee = Stats.Melee;
            Rows.Add(DetailRow(TEXT("普通攻击总伤害"), ColdSteelWeaponStats::Damage(Probe, Model, Melee.Damage) > 0.
                ? FormatNumber(ColdSteelWeaponStats::Damage(Probe, Model, Melee.Damage), 1) : Dash(), ColdSteelUI::TextPrimary));
            Rows.Add(DetailRow(TEXT("攻击间隔"), FString::Printf(TEXT("%d ms"),
                FMath::RoundToInt(ColdSteelWeaponStats::Interval(&Probe, Model, Stats.Interval) * 1000.)), ColdSteelUI::TextPrimary));
        }
        else
        {
            const FWeaponDamageParts Parts = ColdSteelWeaponStats::DamageParts(Probe, Model, Stats.Damage);
            Rows.Add(DetailRow(TEXT("武器总伤害"), FormatNumber(Parts.Total(), 1), ColdSteelUI::TextPrimary));
            Rows.Add(DetailRow(TEXT("攻击间隔"), FString::Printf(TEXT("%d ms"),
                FMath::RoundToInt(ColdSteelWeaponStats::Interval(&Probe, Model, Stats.Interval) * 1000.)), ColdSteelUI::TextPrimary));
            Rows.Add(DetailRow(TEXT("弹匣容量"), FormatNumber((double)Stats.Capacity, 0), ColdSteelUI::TextPrimary));
            Rows.Add(DetailRow(TEXT("普通换弹"), FormatNumber(ColdSteelWeaponStats::Reload(&Probe, Model, Stats.Reload), 2) + TEXT(" s"), ColdSteelUI::TextPrimary));
        }
        Rows.Add(DetailRow(TEXT("有效射程"), FormatNumber(Stats.Range, 1) + TEXT(" m"), ColdSteelUI::TextPrimary));
        if (!bMelee)
        {
            Rows.Add(DetailRow(TEXT("子弹速度"), Stats.Speed <= 0. ? TEXT("即时命中") : FormatNumber(Stats.Speed, 0) + TEXT(" m/s"), ColdSteelUI::TextSecondary));
            Rows.Add(DetailRow(TEXT("后坐力"), FormatNumber(Stats.Recoil, 0), ColdSteelUI::TextSecondary));
        }
        Cards.Add(SectionCard(bMelee ? TEXT("近战数值") : TEXT("枪械数值"), Rows));
    }
    else
    {
        // 未登记进改造目录的物品（如部分工具）没有枪械/近战参数，如实说明而不伪造。
        TArray<TSharedRef<SWidget>> Rows;
        Rows.Add(Label(TEXT("该物品未登记进改造目录，无枪械／近战参数。"), 14, ColdSteelUI::TextTertiary));
        Cards.Add(SectionCard(TEXT("战斗数值"), Rows));
    }

    {
        TArray<TSharedRef<SWidget>> Rows;
        int64 Count = 0;
        bool bEquipped = false;
        for (const FColdSteelItem& Item : Model->Items())
        {
            if (Item.Definition != Definition) continue;
            Count += Item.Count;
            if (Item.Place == 1) bEquipped = true;
        }
        Rows.Add(DetailRow(TEXT("持有数量"), Count > 0 ? FormatNumber((double)Count, 0) : TEXT("未持有"), Count > 0 ? ColdSteelUI::Success : ColdSteelUI::TextTertiary));
        Rows.Add(DetailRow(TEXT("状态"), bEquipped ? TEXT("已装备") : (Count > 0 ? TEXT("在背包／仓库") : TEXT("未获得")), bEquipped ? ColdSteelUI::Success : ColdSteelUI::TextTertiary));
        Cards.Add(SectionCard(TEXT("持有信息"), Rows));

        const FString Description = ColdSteelInventory::Text(Probe, TEXT("desc"));
        if (!Description.IsEmpty())
        {
            TArray<TSharedRef<SWidget>> DescRows;
            DescRows.Add(Label(Description, 14, ColdSteelUI::TextSecondary));
            Cards.Add(SectionCard(TEXT("物品说明"), DescRows));
        }
    }
    return Cards;
}

TArray<TSharedRef<SWidget>> UColdSteelCodexPage::MonsterDetailRows(const FString& MonsterId) const
{
    TArray<TSharedRef<SWidget>> Cards;
    const UDevelopmentSpawnComponent* Spawner = ResolveSpawner();
    if (!Spawner) return Cards;

    const FDevelopmentMonsterEntry* Entry = Spawner->GetMonsters().FindByPredicate(
        [&MonsterId](const FDevelopmentMonsterEntry& E) { return E.Id.ToString() == MonsterId; });
    if (!Entry) return Cards;

    FMonsterCoreStats Stats;
    if (!MonsterStatsOf(*Entry, Stats))
    {
        TArray<TSharedRef<SWidget>> Rows;
        Rows.Add(Label(TEXT("该身份尚未登记防御属性与品阶，档案数值不可用。"), 14, ColdSteelUI::TextTertiary));
        Cards.Add(SectionCard(TEXT("档案状态"), Rows));
        return Cards;
    }

    {
        TArray<TSharedRef<SWidget>> Rows;
        Rows.Add(DetailRow(TEXT("名称"), Entry->Name.ToString(), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("品阶"), RankLabel(Stats.Rank), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("配置等级"), FormatNumber((double)Stats.Level, 0), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("综合战力"), FormatNumber((double)MonsterCoreStats::CombatLevel(Stats, 0., 0.), 0), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("生成半径"), FormatNumber((double)Entry->FootprintRadius, 0) + TEXT(" cm"), ColdSteelUI::TextSecondary));
        Cards.Add(SectionCard(TEXT("基本信息"), Rows));
    }

    {
        // 2026-09-28 六维剔除：改为展示常量表的防御三项（战斗管线实际消费的数值）。
        // 怪物暴击率无消费方，不展示；数值走 JetBrains Mono（DetailRow 既有合同）。
        TArray<TSharedRef<SWidget>> Rows;
        Rows.Add(DetailRow(TEXT("物理防御"), FormatNumber((double)Stats.Def, 0), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("魔法防御"), FormatNumber((double)Stats.Mdef, 0), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("暴击抗性"), FormatNumber((double)Stats.CritRes, 0), ColdSteelUI::TextPrimary));
        Cards.Add(SectionCard(TEXT("防御与抗性"), Rows));
    }

    {
        TArray<TSharedRef<SWidget>> Rows;
        Rows.Add(DetailRow(TEXT("战力加值"), FormatNumber(MonsterCoreStats::RankCombatBonus(Stats.Rank), 0), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("经验倍率"), FString::Printf(TEXT("×%s"), *FormatNumber(MonsterCoreStats::RankExperienceMultiplier(Stats.Rank), 1)), ColdSteelUI::Success));
        Rows.Add(DetailRow(TEXT("金币倍率"), FString::Printf(TEXT("×%s"), *FormatNumber(MonsterCoreStats::RankGoldMultiplier(Stats.Rank), 1)), ColdSteelUI::Success));
        Cards.Add(SectionCard(TEXT("品阶奖励"), Rows));
    }

    {
        TArray<TSharedRef<SWidget>> Rows;
        Rows.Add(Label(TEXT("综合战力为不含生命与移速补充的基础量级；防御与抗性取自档案常量表，感染减益时按系数整体缩放。生命为类基础值乘全局成长系数（现 1.0），实战结算以运行时为准。"), 12, ColdSteelUI::TextTertiary));
        Cards.Add(SectionCard(TEXT("口径说明"), Rows));
    }
    return Cards;
}

TSharedRef<SWidget> UColdSteelCodexPage::BuildSearchRow(const FString& Hint)
{
    // 搜索栏（状态/祭品两页共用同一缓存输入框）：控件规格 §4/§9——ActionHeight 36px、
    // 正文 14px Noto；深底圆角 6px + 1px Border 边。输入只重填当前分区卡片（焦点不丢）。
    if (!SearchEdit.IsValid())
    {
        SearchEditStyle = FEditableTextBoxStyle()
            .SetBackgroundImageNormal(FSlateColorBrush(FLinearColor::Transparent))
            .SetBackgroundImageHovered(FSlateColorBrush(FLinearColor::Transparent))
            .SetBackgroundImageFocused(FSlateColorBrush(FLinearColor::Transparent))
            .SetForegroundColor(FSlateColor(ColdSteelUI::TextPrimary));
        SAssignNew(SearchEdit, SEditableTextBox)
            .Style(&SearchEditStyle)
            .HintText(FText::FromString(Hint))
            .Font(ColdSteelUI::TextFont(14.f * .75f / FMath::Max(Scale, .01f)))
            .OnTextChanged(FOnTextChanged::CreateLambda([this](const FText& NewText)
            {
                SearchText = NewText.ToString();
                RebuildFilterCards();
            }));
    }
    // 提示词按所在分区刷新（输入框本体只建一次，文本与焦点跨分区保留）。
    SearchEdit->SetHintText(FText::FromString(Hint));
    SearchSurfaceBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::ButtonNormal,
        ColdSteelUI::ButtonRadius / FMath::Max(Scale, .01f), ColdSteelUI::Border, 1.f / FMath::Max(Scale, .01f));
    return SNew(SBorder)
        .BorderImage(&SearchSurfaceBrush)
        .Padding(FMargin(12.f / FMath::Max(Scale, .01f) * .8f, 0.f))
        [
            SNew(SBox).HeightOverride(ColdSteelUI::ActionHeight / FMath::Max(Scale, .01f))
            .VAlign(VAlign_Center)
            [ SearchEdit.ToSharedRef() ]
        ];
}

void UColdSteelCodexPage::RebuildFilterCards()
{
    // 搜索输入只重建当前活动分区的卡片区，另一分区的缓存容器不动。
    if (Section == 2) RebuildStatusCards();
    else if (Section == 3) RebuildTributeCards();
}

TSharedRef<SWidget> UColdSteelCodexPage::BuildStatusPage()
{
    // 状态分区整页内容（2026-09-29 二次重排）：顶部搜索栏 +「状态栏卡片」平铺。
    const float Pad = 12.f / FMath::Max(Scale, .01f);
    TSharedRef<SVerticalBox> Column = SNew(SVerticalBox);
    Column->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, Pad)[ BuildSearchRow(TEXT("搜索状态：名称 / 说明 / 效果标识")) ];

    TSharedPtr<SScrollBox> Scroll;
    SAssignNew(Scroll, SScrollBox);
    Scroll->SetScrollBarThickness(FVector2D(6.f / FMath::Max(Scale, .01f)));
    Scroll->SetAllowOverscroll(EAllowOverscroll::No);
    SAssignNew(StatusCardsHost, SVerticalBox);
    Scroll->AddSlot()[ StatusCardsHost.ToSharedRef() ];
    RebuildStatusCards();
    Column->AddSlot().FillHeight(1.f)[ Scroll.ToSharedRef() ];
    return Column;
}

void UColdSteelCodexPage::RebuildStatusCards()
{
    if (!StatusCardsHost.IsValid()) return;
    // 条目弱行底：全条目共用一枚缓存画刷（SBorder 取指针，且 115 条不能各建临时值）；
    // 每次重建按当前 Scale 重算圆角，DPI 变化后随 RefreshLayout 自然刷新。
    StatusEntryBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::AttributeRow,
        ColdSteelUI::CardRadius / FMath::Max(Scale, .01f), FLinearColor::Transparent, 0.f);
    StatusCardsHost->ClearChildren();
    const float Gap = 10.f / FMath::Max(Scale, .01f);
    const TArray<TSharedRef<SWidget>> List = StatusPageCards();
    for (int32 Index = 0; Index < List.Num(); ++Index)
        StatusCardsHost->AddSlot().AutoHeight().Padding(0.f, Index == 0 ? 0.f : Gap, 0.f, 0.f)[ List[Index] ];
}

TArray<TSharedRef<SWidget>> UColdSteelCodexPage::StatusPageCards() const
{
    // 「状态栏卡片」（2026-09-30 三改：按来源分组）：数据走 AllDefinitions（单一事实源）。
    // 过滤 = 分类页签（增益/减益）∧ 搜索关键词；分组为展示维度不过滤——空组直接跳过。
    TArray<TSharedRef<SWidget>> Cards;
    TArray<FStatusEffectView> Catalog;
    UStatusEffectsComponent::AllDefinitions(Catalog);
    const FString Key = StatusCategoryKinds[FMath::Clamp(Category, 0, StatusCategoryCount - 1)];
    const FString Needle = SearchText.TrimStartAndEnd();
    auto MatchesSearch = [&Needle](const FStatusEffectView& V)
    {
        if (Needle.IsEmpty()) return true;
        const FString Hay = (V.Name + TEXT(" ") + V.Description + TEXT(" ") + V.Type.ToString()).ToLower();
        return Hay.Contains(Needle.ToLower());
    };

    for (int32 GroupIndex = 0; GroupIndex < StatusGroupCount; ++GroupIndex)
    {
        const FString GroupKey = StatusGroups[GroupIndex].Key;
        TArray<TSharedRef<SWidget>> Rows;
        int32 Count = 0, Buffs = 0, Debuffs = 0;
        const float Pad = 10.f / FMath::Max(Scale, .01f);
        const float IconColumn = 24.f / FMath::Max(Scale, .01f);
        for (const FStatusEffectView& V : Catalog)
        {
            if (V.Group.ToString() != GroupKey) continue;
            const bool bDebuff = V.Kind == TEXT("debuff");
            if (Key != TEXT("all") && (bDebuff ? TEXT("debuff") : TEXT("buff")) != Key) continue;
            if (!MatchesSearch(V)) continue;
            ++Count; bDebuff ? ++Debuffs : ++Buffs;
            // 名称行：图标用目录语义色着色（效果身份色），右侧固定 增益/减益 标记。
            Rows.Add(SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                  [ Label(V.Icon.IsEmpty() ? TEXT("?") : V.Icon, 16, V.Color) ]
                + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
                  .Padding(6.f / FMath::Max(Scale, .01f), 0.f, 0.f, 0.f)
                  [ LeftLabel(V.Name.IsEmpty() ? V.Type.ToString() : V.Name, 14, ColdSteelUI::TextPrimary, true) ]
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                  [ ValueLabel(bDebuff ? TEXT("减益") : TEXT("增益"), 12,
                       bDebuff ? ColdSteelUI::Danger : ColdSteelUI::Success) ]);
            // 说明行：与名称列对齐缩进。
            Rows.Add(SNew(SBox)
                .Padding(FMargin(IconColumn, 0.f, 0.f, 0.f))
                [ Label(V.Description.IsEmpty() ? TEXT("目录未提供说明。") : V.Description, 12, ColdSteelUI::TextTertiary) ]);
        }
        if (Count == 0) continue;
        // 组头：组名 16px Medium + 组语义说明 + 命中计数（增益/减益分开计）。
        TArray<TSharedRef<SWidget>> GroupRows;
        GroupRows.Add(SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
              [ Label(StatusGroups[GroupIndex].Label, 16, ColdSteelUI::TextPrimary, false, true) ]
            + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Bottom)
              .Padding(8.f / FMath::Max(Scale, .01f), 0.f, 0.f, 2.f / FMath::Max(Scale, .01f))
              [ Label(StatusGroups[GroupIndex].Note, 12, ColdSteelUI::TextTertiary) ]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom)
              [ ValueLabel(Needle.IsEmpty()
                   ? FString::Printf(TEXT("%d 条 · 增%d 减%d"), Count, Buffs, Debuffs)
                   : FString::Printf(TEXT("%d 命中 · 增%d 减%d"), Count, Buffs, Debuffs), 12, ColdSteelUI::TextSecondary) ]);
        // 条目弱行底小块（共享缓存画刷），间隔 6px。
        const float RowGap = 6.f / FMath::Max(Scale, .01f);
        for (int32 Index = 0; Index < Rows.Num(); Index += 2)
        {
            TSharedRef<SVerticalBox> Entry = SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()[ Rows[Index] ]
                + SVerticalBox::Slot().AutoHeight().Padding(0.f, Pad * .3f, 0.f, 0.f)[ Rows[Index + 1] ];
            GroupRows.Add(SNew(SBorder)
                .BorderImage(&StatusEntryBrush)
                .Padding(FMargin(Pad, Pad * .7f))[ Entry ]);
            if (Index + 2 < Rows.Num())
                GroupRows.Add(SNew(SBox).HeightOverride(RowGap));
        }
        Cards.Add(SectionCard(FString::Printf(TEXT("状态栏卡片 · %s"), StatusGroups[GroupIndex].Label), GroupRows));
    }
    if (Cards.IsEmpty())
    {
        TArray<TSharedRef<SWidget>> Rows;
        Rows.Add(Label(Needle.IsEmpty() ? TEXT("此分类暂无状态档案") : TEXT("没有匹配的状态：换个关键词或清空搜索。"), 14, ColdSteelUI::TextTertiary));
        Cards.Add(SectionCard(TEXT("状态栏卡片"), Rows));
    }
    return Cards;
}

TSharedRef<SWidget> UColdSteelCodexPage::BuildTributePage()
{
    // 祭品分区整页内容（2026-09-30）：搜索栏 + 按稀有度分组的「祭品卡片」。
    const float Pad = 12.f / FMath::Max(Scale, .01f);
    TSharedRef<SVerticalBox> Column = SNew(SVerticalBox);
    Column->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, Pad)[ BuildSearchRow(TEXT("搜索祭品：名称 / 说明 / 效果")) ];

    TSharedPtr<SScrollBox> Scroll;
    SAssignNew(Scroll, SScrollBox);
    Scroll->SetScrollBarThickness(FVector2D(6.f / FMath::Max(Scale, .01f)));
    Scroll->SetAllowOverscroll(EAllowOverscroll::No);
    SAssignNew(TributeCardsHost, SVerticalBox);
    Scroll->AddSlot()[ TributeCardsHost.ToSharedRef() ];
    RebuildTributeCards();
    Column->AddSlot().FillHeight(1.f)[ Scroll.ToSharedRef() ];
    return Column;
}

void UColdSteelCodexPage::RebuildTributeCards()
{
    if (!TributeCardsHost.IsValid()) return;
    StatusEntryBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::AttributeRow,
        ColdSteelUI::CardRadius / FMath::Max(Scale, .01f), FLinearColor::Transparent, 0.f);
    TributeCardsHost->ClearChildren();
    const float Gap = 10.f / FMath::Max(Scale, .01f);
    const TArray<TSharedRef<SWidget>> List = TributePageCards();
    for (int32 Index = 0; Index < List.Num(); ++Index)
        TributeCardsHost->AddSlot().AutoHeight().Padding(0.f, Index == 0 ? 0.f : Gap, 0.f, 0.f)[ List[Index] ];
}

TArray<TSharedRef<SWidget>> UColdSteelCodexPage::TributePageCards() const
{
    // 「祭品卡片」（2026-09-30）：物品目录 category=tribute 全量条目（items.json 单一
    // 事实源，与背包/浮窗同一物品 Data）。按稀有度六档分组（高→低），组内名称行右侧
    // 显示类型，效果摘要取 Data 的 stats 数组（物品浮窗同一展示字段）。
    TArray<TSharedRef<SWidget>> Cards;
    if (!Model) return Cards;
    const FString Needle = SearchText.TrimStartAndEnd();

    struct FTributeRow { FString Id, Name, Type, Desc, Glyph, Rarity, StatsLine; };
    TArray<FTributeRow> Rows;
    for (const FColdSteelCatalogEntry& Entry : Model->ItemCatalog())
    {
        const FColdSteelItem Item = Model->CreateItem(Entry.Definition);
        if (ColdSteelInventory::Text(Item, TEXT("category")) != TEXT("tribute")) continue;
        FTributeRow R;
        R.Id = Entry.Definition;
        R.Name = ColdSteelInventory::Text(Item, TEXT("name"));
        if (R.Name.IsEmpty()) R.Name = Entry.Name;
        R.Type = ColdSteelInventory::Text(Item, TEXT("type"));
        R.Desc = ColdSteelInventory::Text(Item, TEXT("desc"));
        R.Glyph = ColdSteelInventory::Text(Item, TEXT("icon_fallback"));
        R.Rarity = ColdSteelInventory::Text(Item, TEXT("rarity"));
        TSharedPtr<FJsonObject> Data;
        if (!Item.Data.IsEmpty() && FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Item.Data), Data))
        {
            const TArray<TSharedPtr<FJsonValue>>* Stats = nullptr;
            if (Data->TryGetArrayField(TEXT("stats"), Stats) && Stats)
                for (const TSharedPtr<FJsonValue>& S : *Stats)
                    if (const TSharedPtr<FJsonObject> O = S.IsValid() ? S->AsObject() : nullptr)
                    {
                        const FString Sn = O->GetStringField(TEXT("name"));
                        const FString Sv = O->GetStringField(TEXT("value"));
                        if (!Sn.IsEmpty() || !Sv.IsEmpty())
                            R.StatsLine += (R.StatsLine.IsEmpty() ? TEXT("") : TEXT(" · ")) + Sn + TEXT(" ") + Sv;
                    }
        }
        if (!Needle.IsEmpty())
        {
            const FString Hay = (R.Name + TEXT(" ") + R.Desc + TEXT(" ") + R.Id + TEXT(" ") + R.StatsLine).ToLower();
            if (!Hay.Contains(Needle.ToLower())) continue;
        }
        Rows.Add(MoveTemp(R));
    }

    const float Pad = 10.f / FMath::Max(Scale, .01f);
    const float IconColumn = 24.f / FMath::Max(Scale, .01f);
    const float RowGap = 6.f / FMath::Max(Scale, .01f);
    const int32 RarityTab = Category - 1;   // 页签 0=全部，1..6=稀有度（与 TributeRarityKeys 同序）
    for (int32 RarityIndex = 0; RarityIndex < TributeRarityCount; ++RarityIndex)
    {
        if (RarityTab >= 0 && RarityTab < TributeRarityCount && RarityTab != RarityIndex) continue;
        TArray<TSharedRef<SWidget>> CardRows;
        int32 Count = 0;
        for (const FTributeRow& R : Rows)
        {
            if (R.Rarity != TributeRarityKeys[RarityIndex]) continue;
            ++Count;
            const FLinearColor RarityColor = ColdSteelUI::RarityColor(R.Rarity);
            TSharedRef<SHorizontalBox> Head = SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                  [ Label(R.Glyph.IsEmpty() ? TEXT("?") : R.Glyph, 16, RarityColor) ]
                + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
                  .Padding(6.f / FMath::Max(Scale, .01f), 0.f, 0.f, 0.f)
                  [ LeftLabel(R.Name, 14, ColdSteelUI::TextPrimary, true) ]
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                  [ ValueLabel(R.Type.IsEmpty() ? ColdSteelUI::RarityLabel(R.Rarity) : R.Type, 12, ColdSteelUI::TextSecondary) ];
            TSharedPtr<SWidget> StatsLine, DescLine;
            if (!R.StatsLine.IsEmpty())
                StatsLine = SNew(SBox).Padding(FMargin(IconColumn, 0.f, 0.f, 0.f))
                    [ ValueLabel(R.StatsLine, 12, ColdSteelUI::TextSecondary) ];
            if (!R.Desc.IsEmpty())
                DescLine = SNew(SBox)
                    .Padding(FMargin(IconColumn, R.StatsLine.IsEmpty() ? 0.f : Pad * .3f, 0.f, 0.f))
                    [ Label(R.Desc, 12, ColdSteelUI::TextTertiary) ];
            TSharedRef<SVerticalBox> EntryCard = SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()[ Head ];
            if (StatsLine.IsValid())
                EntryCard->AddSlot().AutoHeight().Padding(0.f, Pad * .3f, 0.f, 0.f)[ StatsLine.ToSharedRef() ];
            if (DescLine.IsValid())
                EntryCard->AddSlot().AutoHeight().Padding(0.f, Pad * .25f, 0.f, 0.f)[ DescLine.ToSharedRef() ];
            CardRows.Add(SNew(SBorder).BorderImage(&StatusEntryBrush).Padding(FMargin(Pad, Pad * .7f))[ EntryCard ]);
            if (Count > 0) CardRows.Add(SNew(SBox).HeightOverride(RowGap));
        }
        if (Count == 0) continue;
        CardRows.Pop();   // 末条目后的间隔不必保留
        // 组头：稀有度标签（稀有度色）+ 计数，插到卡内容最前。
        TArray<TSharedRef<SWidget>> Out;
        Out.Add(SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
              [ Label(TributeRarityLabels[RarityIndex], 16, ColdSteelUI::RarityColor(TributeRarityKeys[RarityIndex]), false, true) ]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom)
              .Padding(8.f / FMath::Max(Scale, .01f), 0.f, 0.f, 2.f / FMath::Max(Scale, .01f))
              [ ValueLabel(Needle.IsEmpty()
                   ? FString::Printf(TEXT("%d 件"), Count)
                   : FString::Printf(TEXT("%d 命中"), Count), 12, ColdSteelUI::TextSecondary) ]);
        Out.Append(CardRows);
        Cards.Add(SectionCard(FString::Printf(TEXT("祭品卡片 · %s"), TributeRarityLabels[RarityIndex]), Out));
    }
    if (Cards.IsEmpty())
    {
        TArray<TSharedRef<SWidget>> Empty;
        Empty.Add(Label(Needle.IsEmpty() ? TEXT("此分类暂无祭品档案") : TEXT("没有匹配的祭品：换个关键词或清空搜索。"), 14, ColdSteelUI::TextTertiary));
        Cards.Add(SectionCard(TEXT("祭品卡片"), Empty));
    }
    return Cards;
}
