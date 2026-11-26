#pragma once
#include "CoreMinimal.h"
#include "ColdSteelInventoryTypes.h"
class UColdSteelStatusModel;
class UGunsmithSystem;
/** A read-only instance supplied by a view which owns its own item list. */
struct FColdSteelItemTooltipPreview
{
    FColdSteelItem Item;
    FString Location, ActionHint;
};
struct FColdSteelTooltipRow
{
    FString Label, Value;
    int32 Tone=0;
    bool bSection=false;
    bool bContinuation=false;
    FString CompactValue;
    bool bStacked=false;
    bool bDashedAfter=false;
    // Show this mechanism after the core grid in both hover and pinned views.
    // Its source stays in the main card for other item-detail consumers.
    bool bPreview=false;
    bool bInlineStatModifier=false;
    bool ShowsEffectArrow() const;
};
struct FColdSteelTooltipCard
{
    FString Title;
    float MinimumWidth=460;
    TArray<FColdSteelTooltipRow> Rows;
};
/**
 * 「特殊性质」段的一行。Icon 只是语义标签，由 UI 层映射成颜色，
 * 所以目录里新增武器写 traits 就行，不必动 C++。
 */
struct FColdSteelTooltipTrait
{
    FString Icon, Text;
};
/**
 * 套装在缩略浮窗里的显示数据：先报「锁子甲套装（4/5）」，再列出
 * 凑齐后才生效的属性。未凑齐也照列，供玩家判断差的那一件值不值得换。
 */
struct FColdSteelTooltipSetInfo
{
    /** 套装显示名，如「锁子甲套装」。 */
    FString Name;
    /** 已装备件数 / 该套总件数。 */
    int32 Equipped = 0, Total = 0;
    bool bComplete = false;
    /** 凑齐后生效的属性，已按语义判好正负；显示占用同一套增益/减益色。 */
    TArray<FColdSteelTooltipRow> Bonuses;
};
struct FColdSteelTooltipContent
{
    FString Name,Type,Rarity,Description,Icon,Enhancement;
    FString Location,ValueScope,ComparisonTitle;
    int32 Level=0;
    int32 EnhancementLevel=0;
    bool bEquipment=false;
    double FoodLifetimeDays=0;
    float FoodProgress=0;
    bool bTorchFuel=false;
    bool HasLifetimeBar() const { return bTorchFuel || FoodLifetimeDays>0.; }
    bool bWideIcon=false;
    TArray<FColdSteelTooltipRow> Summary,Comparison;
    TArray<FColdSteelTooltipCard> Cards; // enchant, craft, main
    /** 武器特殊性质；为空时工具提示不渲染该段。 */
    TArray<FColdSteelTooltipTrait> Traits;
    /** 装备所属套装；不是套装件时用 bHasSet=false，浮窗不渲染该段。 */
    FColdSteelTooltipSetInfo Set;
    bool bHasSet=false;
};
FPSGAME_API FColdSteelTooltipContent BuildColdSteelItemTooltip(const FColdSteelItem& Item,UColdSteelStatusModel* Model,UGunsmithSystem* Gunsmith,const FString& Location = FString());
/** Updates food progress and existing freshness rows; no widget rebuild, catalog parse or icon load. */
void RefreshColdSteelFoodTooltip(const FColdSteelItem& Item,UColdSteelStatusModel* Model,FColdSteelTooltipContent& Content);
void CompleteColdSteelTooltipSummary(const FColdSteelItem& Item,UColdSteelStatusModel* Model,UGunsmithSystem* Gunsmith,FColdSteelTooltipContent& Content);
/**
 * 单独问一句「这件装备的套装信息能否渲染」。主卡构建早于摘要完成，
 * 需要它来避免「套装效果」段与摘要套装块重复；无法统计时返回 false。
 */
FPSGAME_API bool ResolveColdSteelTooltipSet(const FColdSteelItem& Item,UColdSteelStatusModel* Model,FColdSteelTooltipSetInfo& Out);
void AppendColdSteelTooltipAttackFormula(const FColdSteelItem& Item,UColdSteelStatusModel* Model,double WeaponBase,FColdSteelTooltipCard& Card);

void AppendColdSteelTooltipMagicFormula(const FColdSteelItem& Item,UColdSteelStatusModel* Model,FColdSteelTooltipCard& Card);
