#pragma once
#include "CoreMinimal.h"
class APlayerController;
class APawn;
class AActor;
class AColdSteelSceneContainer;
class AVillageDefenseSection;
class UWorld;
enum class EHighGateUse : uint8;
namespace ColdSteelWorldInteraction
{
    inline constexpr float DefaultUseReach = 250.f;
    /** Interaction reach stays at the player's eyes when the development camera pulls back. */
    void GetReachViewPoint(const APlayerController* Controller,FVector& Eye,FRotator& View);
    struct FUseTargets
    {
        AActor* Target = nullptr;
        EHighGateUse GateUse{};
        AVillageDefenseSection* RepairTarget() const;
        AActor* CounterResident = nullptr;
        AVillageDefenseSection* NearbyBreach = nullptr;
    };
    /** A visible counter service point is a fallback after the existing E interactions. */
    FUseTargets TraceUseTargets(const APlayerController* Controller,float Reach=DefaultUseReach,bool bFindNearbyBreach=false);
    AActor* TraceTarget(const APlayerController* Controller,float Reach=DefaultUseReach);
    AColdSteelSceneContainer* FocusedSceneContainer(const APlayerController* Controller);
    AColdSteelSceneContainer* UpdateSceneContainerHighlight(const APlayerController* Controller,bool bAllowed);
    /** Display the resident selected by this local player's active E prompt, or clear with nullptr. */
    void UpdateResidentHighlight(const APlayerController* PC, AActor* Target);
    bool IsFocused(const APawn* Pawn,const AActor* Target,float Reach=DefaultUseReach);
    bool CanReachPickup(const UWorld* World,const APawn* Pawn,const AActor* Target,const FVector& Position);
    /** Authored hub altar; the same target predicate drives its prompt and E action. */
    bool IsExpeditionAltar(const AActor* Target);
    /** Hub fountain; shares the 2.5 m eye trace with its prompt and E action. */
    bool IsBlessingFountain(const AActor* Target);
    bool DrinkFromFountain(const APlayerController* Controller,AActor* Target);
    /** Dungeon treasure keeps its own one-shot opening state, separate from warehouse UI. */
    bool IsTreasureChest(const AActor* Target);
    bool IsTreasureChestActivated(const AActor* Target);
    FString TreasureChestPrompt(const AActor* Target);
    bool OpenTreasureChest(const APlayerController* Controller,AActor* Target);
    /** Placed blast furnace (palette id `blast_furnace`, not a falling piece); drives the
     *  smelting prompt and the E action that opens the backpack plus the smelting panel. */
    bool IsSmeltingFurnace(const AActor* Target);
    bool IsForgingStation(const AActor* Target);
    /** Prompt text that also reports the furnace's live state (idle / burning / ready to collect). */
    FString SmeltingFurnacePrompt(const AActor* Target);
    /** Placed crafting / gun workbench (not a falling piece); drives the
     *  workbench prompt and the E action that opens the backpack plus the crafting panel
     *  (Docs/UI/workbench-panel-plan-20260924.md — shell mirrors the smelting panel). */
    bool IsAlchemyBench(const AActor* Target);
    bool IsEnhancementBench(const AActor* Target);
    bool IsWoodworkingBench(const AActor* Target);
    bool IsWorkbench(const AActor* Target);
    FString WorkbenchPrompt(const AActor* Target);
    /** 2026-09-24 用户统一口径：准星下小浮窗（毛玻璃灰黑＋白字）承载一切 E 交互提示，
     *  模型上方不再挂世界空间名牌。返回空文本＝不显示；bAction=false＝只读状态（已开启等），不出现 E 键徽标。 */
    struct FInteractionHint
    {
        FString Text;
        bool bAction=true;
        FString Title;
    };
    FInteractionHint ResolveInteractionHint(const AActor* Target,APawn* Viewer,EHighGateUse GateUse={});
}
