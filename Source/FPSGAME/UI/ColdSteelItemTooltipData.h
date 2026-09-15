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
struct FColdSteelTooltipContent
{
    FString Name,Type,Rarity,Description,Icon,Enhancement;
    FString Location,ValueScope,ComparisonTitle;
    int32 Level=0;
    bool bWideIcon=false;
    TArray<FColdSteelTooltipRow> Summary,Comparison;
    TArray<FColdSteelTooltipCard> Cards; // enchant, craft, main
};
FPSGAME_API FColdSteelTooltipContent BuildColdSteelItemTooltip(const FColdSteelItem& Item,UColdSteelStatusModel* Model,UGunsmithSystem* Gunsmith);
void CompleteColdSteelTooltipSummary(const FColdSteelItem& Item,UColdSteelStatusModel* Model,UGunsmithSystem* Gunsmith,FColdSteelTooltipContent& Content);
void AppendColdSteelTooltipAttackFormula(const FColdSteelItem& Item,UColdSteelStatusModel* Model,double WeaponBase,FColdSteelTooltipCard& Card);
