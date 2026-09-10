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
    int32 Level=0;
    TArray<FColdSteelTooltipCard> Cards; // enchant, craft, main
};
FPSGAME_API FColdSteelTooltipContent BuildColdSteelItemTooltip(const FColdSteelItem& Item,UColdSteelStatusModel* Model,UGunsmithSystem* Gunsmith);
