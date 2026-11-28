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

TArray<TSharedRef<SWidget>> UColdSteelCodexPage::WeaponDetailRows(const FString& Definition) const
{
    TArray<TSharedRef<SWidget>> Cards;
    if (!Model) return Cards;
    const FColdSteelItem Probe = Model->CreateItem(Definition);

    {
        TArray<TSharedRef<SWidget>> Rows;
        Rows.Add(DetailRow(TEXT("名称"), ColdSteelInventory::Text(Probe, TEXT("name")), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("类型"), ColdSteelInventory::Text(Probe, TEXT("type")), ColdSteelUI::TextPrimary));
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
    else if (Gunsmith && Gunsmith->IsStaff(Definition))
    {
        const auto Stats = Gunsmith->Calculate(Definition, FGunsmithParts());
        TArray<TSharedRef<SWidget>> Rows;
        Rows.Add(DetailRow(ColdSteelWeaponText::EquipmentMagicAttack, FormatNumber(Model->ItemMagicAttack(Probe), 2), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("杖击伤害"), FormatNumber(ColdSteelWeaponStats::Damage(Probe, Model, Stats.Damage), 1), ColdSteelUI::TextPrimary));
        Rows.Add(DetailRow(TEXT("杖击间隔"), FormatNumber(ColdSteelWeaponStats::Interval(&Probe, Model, Stats.Interval), 2) + TEXT(" s"), ColdSteelUI::TextPrimary));
        Cards.Add(SectionCard(TEXT("法杖数值"), Rows));
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
        Rows.Add(DetailRow(TEXT("灵魂倍率"), FString::Printf(TEXT("×%s"), *FormatNumber(MonsterCoreStats::RankGoldMultiplier(Stats.Rank), 1)), ColdSteelUI::Success));
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
    else if (Section == 4) RebuildEnchantCards();
}

TSharedRef<SWidget> UColdSteelCodexPage::BuildStatusPage()
{
    // 状态分区整页内容（2026-09-29 二次重排）：顶部搜索栏 +「状态栏卡片」平铺。
    const float Pad = 12.f / FMath::Max(Scale, .01f);
    TSharedRef<SVerticalBox> Column = SNew(SVerticalBox);
    Column->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, Pad)[ BuildSearchRow(TEXT("搜索状态：名称 / 说明 / 效果标识")) ];

    TSharedPtr<SScrollBox> Scroll;
    SAssignNew(Scroll, SScrollBox);
    Scroll->SetAllowOverscroll(EAllowOverscroll::No);
    ColdSteelUI::ApplyGoldScroll(Scroll.ToSharedRef(), FVector2D(6.f / FMath::Max(Scale, .01f)), FMargin(4.f / FMath::Max(Scale, .01f), 0.f, 0.f, 0.f), true);
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
    Scroll->SetAllowOverscroll(EAllowOverscroll::No);
    ColdSteelUI::ApplyGoldScroll(Scroll.ToSharedRef(), FVector2D(6.f / FMath::Max(Scale, .01f)), FMargin(4.f / FMath::Max(Scale, .01f), 0.f, 0.f, 0.f), true);
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

TSharedRef<SWidget> UColdSteelCodexPage::BuildEnchantPage()
{
    // 附魔分区整页内容（2026-10-03）：搜索栏 + 按稀有度分组的「附魔卡片」。
    // 数据走 UColdSteelEnhancementSystem::Scrolls()（enhancement.json 单一事实源，与强化台同一入口）。
    const float Pad = 12.f / FMath::Max(Scale, .01f);
    TSharedRef<SVerticalBox> Column = SNew(SVerticalBox);
    Column->AddSlot().AutoHeight().Padding(0.f, 0.f, 0.f, Pad)[ BuildSearchRow(TEXT("搜索附魔：名称 / 说明 / 兼容")) ];

    TSharedPtr<SScrollBox> Scroll;
    SAssignNew(Scroll, SScrollBox);
    Scroll->SetAllowOverscroll(EAllowOverscroll::No);
    ColdSteelUI::ApplyGoldScroll(Scroll.ToSharedRef(), FVector2D(6.f / FMath::Max(Scale, .01f)), FMargin(4.f / FMath::Max(Scale, .01f), 0.f, 0.f, 0.f), true);
    SAssignNew(EnchantCardsHost, SVerticalBox);
    Scroll->AddSlot()[ EnchantCardsHost.ToSharedRef() ];
    RebuildEnchantCards();
    Column->AddSlot().FillHeight(1.f)[ Scroll.ToSharedRef() ];
    return Column;
}

void UColdSteelCodexPage::RebuildEnchantCards()
{
    if (!EnchantCardsHost.IsValid()) return;
    StatusEntryBrush = ColdSteelUI::RoundedBrush(ColdSteelUI::AttributeRow,
        ColdSteelUI::CardRadius / FMath::Max(Scale, .01f), FLinearColor::Transparent, 0.f);
    EnchantCardsHost->ClearChildren();
    const float Gap = 10.f / FMath::Max(Scale, .01f);
    const TArray<TSharedRef<SWidget>> List = EnchantPageCards();
    for (int32 Index = 0; Index < List.Num(); ++Index)
        EnchantCardsHost->AddSlot().AutoHeight().Padding(0.f, Index == 0 ? 0.f : Gap, 0.f, 0.f)[ List[Index] ];
}

TArray<TSharedRef<SWidget>> UColdSteelCodexPage::EnchantPageCards() const
{
    // 「附魔卡片」（2026-10-03）：卷轴目录全量条目。图鉴是档案页，收录全部 14 条卷轴，
    // 不沿用强化台「只计背包正数量堆叠」的合同——那是可用性过滤，不是目录口径。
    // 过滤 = 分类页签（前缀/后缀）∧ 搜索关键词；稀有度分组为展示维度（组序高→低，空组跳过）。
    TArray<TSharedRef<SWidget>> Cards;
    UGameInstance* GI = GetGameInstance();
    const UColdSteelEnhancementSystem* Enhancement = GI ? GI->GetSubsystem<UColdSteelEnhancementSystem>() : nullptr;
    if (!Enhancement) return Cards;

    const FString SlotKey = EnchantCategorySlots[FMath::Clamp(Category, 0, EnchantCategoryCount - 1)];
    const FString Needle = SearchText.TrimStartAndEnd();

    struct FEnchantRow { FString Id, Name, Slot, Restriction, Desc, Glyph, Rarity; int64 Dust = 0; };
    TArray<FEnchantRow> Rows;
    for (const FColdSteelEnchantOption& Option : Enhancement->Scrolls())
    {
        if (SlotKey != TEXT("all") && Option.Slot != SlotKey) continue;
        FEnchantRow R;
        R.Id = Option.Id;
        R.Name = Option.Name;
        R.Slot = Option.Slot;
        R.Restriction = EnchantRestrictionText(Option.Restriction);
        R.Desc = Option.Description;
        R.Dust = Option.Dust;
        // 稀有度与字形取卷轴物品 Data（与背包/浮窗同一物品字段）；目录缺物品时不伪造，留空落「其他」组。
        if (Model)
        {
            const FColdSteelItem Item = Model->CreateItem(Option.Item);
            R.Glyph = ColdSteelInventory::Text(Item, TEXT("icon_fallback"));
            R.Rarity = ColdSteelInventory::Text(Item, TEXT("rarity"));
        }
        if (!Needle.IsEmpty())
        {
            const FString Hay = (R.Name + TEXT(" ") + R.Desc + TEXT(" ") + R.Restriction + TEXT(" ") + R.Id).ToLower();
            if (!Hay.Contains(Needle.ToLower())) continue;
        }
        Rows.Add(MoveTemp(R));
    }
    // 组内排序：粉尘消耗升序、再按名称，形成同组内按代价递增的查阅顺序；组间已按稀有度高→低。
    Rows.Sort([](const FEnchantRow& A, const FEnchantRow& B)
    {
        if (A.Dust != B.Dust) return A.Dust < B.Dust;
        return A.Name < B.Name;
    });

    const float Pad = 10.f / FMath::Max(Scale, .01f);
    const float IconColumn = 24.f / FMath::Max(Scale, .01f);
    const float RowGap = 6.f / FMath::Max(Scale, .01f);
    // 稀有度分组复用祭品组序表（高→低）；目录物品缺 rarity 或 rarity 不在表内的条目
    // 落入末尾「其他」组，保证目录条目不因字段缺失而整条消失。
    // 组序表：稀有度高→低，末尾追加 -1（「其他」兜底组），循环按表序出卡。
    const int32 GroupOrder[] = {0, 1, 2, 3, 4, 5, -1};
    static_assert(UE_ARRAY_COUNT(GroupOrder) == TributeRarityCount + 1,
        "附魔组序表必须覆盖全部稀有度与兜底组");
    for (const int32 RarityIndex : GroupOrder)
    {
        const TCHAR* GroupKey = RarityIndex < 0 ? nullptr : TributeRarityKeys[RarityIndex];
        TArray<TSharedRef<SWidget>> CardRows;
        int32 Count = 0;
        for (const FEnchantRow& R : Rows)
        {
            const bool bOther = RarityIndex < 0;
            const bool bInGroup = bOther
                ? !MatchesTributeRarity(R.Rarity)
                : R.Rarity == GroupKey;
            if (!bInGroup) continue;
            ++Count;
            const FLinearColor RarityColor = bOther ? ColdSteelUI::TextSecondary : ColdSteelUI::RarityColor(R.Rarity);
            // 名称行：字形用稀有度色着色，右侧固定 前缀/后缀 标记（未知 slot 如实显示原文）。
            TSharedRef<SHorizontalBox> Head = SNew(SHorizontalBox)
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                  [ Label(R.Glyph.IsEmpty() ? TEXT("?") : R.Glyph, 16, RarityColor) ]
                + SHorizontalBox::Slot().FillWidth(1.f).VAlign(VAlign_Center)
                  .Padding(6.f / FMath::Max(Scale, .01f), 0.f, 0.f, 0.f)
                  [ LeftLabel(R.Name, 14, ColdSteelUI::TextPrimary, true) ]
                + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
                  [ ValueLabel(R.Slot == TEXT("prefix") ? TEXT("前缀")
                      : R.Slot == TEXT("suffix") ? TEXT("后缀") : R.Slot, 12, ColdSteelUI::TextSecondary) ];
            // 兼容与消耗行：与祭品 StatsLine 同规格（数值 12px），文本与物品浮窗口径一致。
            TSharedRef<SWidget> CostLine = SNew(SBox).Padding(FMargin(IconColumn, 0.f, 0.f, 0.f))
                [ ValueLabel(FString::Printf(TEXT("兼容 %s · 魔法粉尘 %lld"), *R.Restriction, R.Dust),
                     12, ColdSteelUI::TextSecondary) ];
            // 效果说明行：enhancement.json description 原文（强化台悬停同一字段），成段换行。
            TSharedRef<SWidget> DescLine = SNew(SBox)
                .Padding(FMargin(IconColumn, Pad * .3f, 0.f, 0.f))
                [ Label(R.Desc.IsEmpty() ? TEXT("目录未提供说明。") : R.Desc, 12, ColdSteelUI::TextTertiary) ];
            TSharedRef<SVerticalBox> EntryCard = SNew(SVerticalBox)
                + SVerticalBox::Slot().AutoHeight()[ Head ]
                + SVerticalBox::Slot().AutoHeight().Padding(0.f, Pad * .3f, 0.f, 0.f)[ CostLine ]
                + SVerticalBox::Slot().AutoHeight().Padding(0.f, Pad * .25f, 0.f, 0.f)[ DescLine ];
            CardRows.Add(SNew(SBorder).BorderImage(&StatusEntryBrush).Padding(FMargin(Pad, Pad * .7f))[ EntryCard ]);
            CardRows.Add(SNew(SBox).HeightOverride(RowGap));
        }
        if (Count == 0) continue;
        CardRows.Pop();   // 末条目后的间隔不必保留
        const TCHAR* GroupLabel = RarityIndex < 0 ? TEXT("其他") : TributeRarityLabels[RarityIndex];
        // 组头：稀有度标签（稀有度色）+ 计数，插到卡内容最前。
        TArray<TSharedRef<SWidget>> Out;
        Out.Add(SNew(SHorizontalBox)
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Center)
              [ Label(GroupLabel, 16, RarityIndex < 0 ? ColdSteelUI::TextSecondary
                   : ColdSteelUI::RarityColor(TributeRarityKeys[RarityIndex]), false, true) ]
            + SHorizontalBox::Slot().AutoWidth().VAlign(VAlign_Bottom)
              .Padding(8.f / FMath::Max(Scale, .01f), 0.f, 0.f, 2.f / FMath::Max(Scale, .01f))
              [ ValueLabel(Needle.IsEmpty()
                   ? FString::Printf(TEXT("%d 种"), Count)
                   : FString::Printf(TEXT("%d 命中"), Count), 12, ColdSteelUI::TextSecondary) ]);
        Out.Append(CardRows);
        Cards.Add(SectionCard(FString::Printf(TEXT("附魔卡片 · %s"), GroupLabel), Out));
    }
    if (Cards.IsEmpty())
    {
        TArray<TSharedRef<SWidget>> Empty;
        Empty.Add(Label(Needle.IsEmpty() ? TEXT("此分类暂无附魔档案") : TEXT("没有匹配的附魔：换个关键词或清空搜索。"), 14, ColdSteelUI::TextTertiary));
        Cards.Add(SectionCard(TEXT("附魔卡片"), Empty));
    }
    return Cards;
}
