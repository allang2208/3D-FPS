#pragma once
#include "CoreMinimal.h"
class APlayerController;
class APawn;
class AActor;
namespace ColdSteelWorldInteraction
{
    /** Interaction reach stays at the player's eyes when the development camera pulls back. */
    void GetReachViewPoint(const APlayerController* Controller,FVector& Eye,FRotator& View);
    AActor* TraceTarget(const APlayerController* Controller,float Reach=250.f);
    bool IsFocused(const APawn* Pawn,const AActor* Target,float Reach=250.f);
    /** Authored hub altar; the same target predicate drives its prompt and E action. */
    bool IsExpeditionAltar(const AActor* Target);
    /** Dungeon treasure keeps its own one-shot opening state, separate from warehouse UI. */
    bool IsTreasureChest(const AActor* Target);
    bool IsTreasureChestActivated(const AActor* Target);
    FString TreasureChestPrompt(const AActor* Target);
    bool OpenTreasureChest(const APlayerController* Controller,AActor* Target);
    /** Placed blast furnace (palette id `blast_furnace`, not a falling piece); drives the
     *  smelting prompt and the E action that opens the backpack plus the smelting panel. */
    bool IsSmeltingFurnace(const AActor* Target);
    /** Prompt text that also reports the furnace's live state (idle / burning / ready to collect). */
    FString SmeltingFurnacePrompt(const AActor* Target);
    /** Placed workbench (palette id `workbench_table`, not a falling piece); drives the
     *  workbench prompt and the E action that opens the backpack plus the crafting panel
     *  (Docs/UI/workbench-panel-plan-20260924.md — shell mirrors the smelting panel). */
    bool IsWorkbench(const AActor* Target);
    FString WorkbenchPrompt(const AActor* Target);
}
