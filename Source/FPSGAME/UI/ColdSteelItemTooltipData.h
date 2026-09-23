#pragma once
#include "CoreMinimal.h"
#include "ColdSteelInventoryTypes.h"
class UColdSteelStatusModel;
class UGunsmithSystem;
struct FColdSteelTooltipRow
{
    FString Label, Value;
    int32 Tone=0;
    bool bSection=false;
    bool bContinuation=false;
    FString CompactValue;
    bool bStacked=false;
    bool bDashedAfter=false;
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
struct FColdSteelTooltipContent
{
    FString Name,Type,Rarity,Description,Icon,Enhancement;
    FString Location,ValueScope,ComparisonTitle;
    int32 Level=0;
    bool bWideIcon=false;
    TArray<FColdSteelTooltipRow> Summary,Comparison;
    TArray<FColdSteelTooltipCard> Cards; // enchant, craft, main
    /** 武器特殊性质；为空时工具提示不渲染该段。 */
    TArray<FColdSteelTooltipTrait> Traits;
};
FPSGAME_API FColdSteelTooltipContent BuildColdSteelItemTooltip(const FColdSteelItem& Item,UColdSteelStatusModel* Model,UGunsmithSystem* Gunsmith);
void CompleteColdSteelTooltipSummary(const FColdSteelItem& Item,UColdSteelStatusModel* Model,UGunsmithSystem* Gunsmith,FColdSteelTooltipContent& Content);
void AppendColdSteelTooltipAttackFormula(const FColdSteelItem& Item,UColdSteelStatusModel* Model,double WeaponBase,FColdSteelTooltipCard& Card);
