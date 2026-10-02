#pragma once
#include "CoreMinimal.h"

class AActor;

struct FColdSteelDungeonLootPreview
{
    FString Definition;
    int32 MinimumDepth=0;
    bool bInFinalTier=false;
};

/**
 * 地牢宝箱战利品：运行中（UDungeonRunSubsystem::IsRunActive）的宝箱开启后按房间深度 roll 出随机奖励，
 * 2026-10-02 起不再直接发放/播报——roll 结果写进宝箱自己的仓库容器（Place 4 + DungeonChest.<领取键>），
 * 由交互层打开与仓库宝箱同款的面板（一页 18×12），玩家按仓库规则拖动／右键取出。
 * 战利品表 Content/ColdSteelData/dungeon_loot.json 一次性读取并静态缓存（不做热重载）。
 * 编辑器摆放的普通宝箱／非运行场景不进入本逻辑，开启行为与旧版完全一致。
 * 挂接点：ColdSteelWorldInteraction::OpenTreasureChest 的 finish 定时器 lambda（Tags 打上
 * DungeonTreasure.Opened 之后）。全部随机走运行种子的 GameplayStream(ChestLoot^节点散列)，同 seed 可复现。
 */
class FColdSteelDungeonLoot
{
public:
    /** Read the same cached candidates as StoreFromChest, without drawing or granting loot. */
    static TArray<FColdSteelDungeonLootPreview> PreviewItems();
    static double FinalQuantityMultiplier();
    /** 宝箱容器键（由房间节点/领取标记推导，未开箱也稳定可算）；非运行场景返回空。 */
    static FString ChestStorageKey(AActor* Chest);
    /** roll 全量写进宝箱容器（同事务打领取标记），失败返回 false 允许宝箱重试；
     *  已领取（重复开箱）不重 roll，返回 true 并经 OutContainerKey 让交互层重开面板。 */
    static bool StoreFromChest(AActor* Chest,FString& OutContainerKey);
};
