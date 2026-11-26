#include "ColdSteelCodexPage.h"
#include "ColdSteelWeaponText.h"
#include "ColdSteelHUDWidget.h"
#include "ColdSteelEnhancementSystem.h"
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

#include "ColdSteelCodexPrivate.h"
using namespace ColdSteelCodexPrivate;

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
    else if (Section == 4)
    {
        for (int32 Index = 0; Index < EnchantCategoryCount; ++Index) Names.Add(EnchantCategoryLabels[Index]);
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
        : Section == 3 ? TEXT("祭品") : Section == 4 ? TEXT("附魔") : TEXT("怪物档案");
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
    const FString CategoryField = ColdSteelInventory::Text(Item, TEXT("category"));
    if (CategoryField == TEXT("equipment")) return TEXT("equipment");
    if (CategoryField == TEXT("tool")) return TEXT("tool");
    if (CategoryField == TEXT("weapon_magic") || ColdSteelInventory::IsStaff(Item)) return TEXT("weapon_magic");
    if (CategoryField == TEXT("weapon_melee")) return TEXT("weapon_melee");
    if (CategoryField == TEXT("weapon") || CategoryField == TEXT("weapon_ranged")) return TEXT("weapon_ranged");
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
    else if (Section == 4)
    {
        // 附魔分区同样走整页卡片（EnchantPageCards），不使用网格列表条目；
        // 同祭品分区：分支必须在恒真的怪物登记表分支之前。
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

