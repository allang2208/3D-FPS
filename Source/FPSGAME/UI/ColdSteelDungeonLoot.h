#pragma once
#include "CoreMinimal.h"

class AActor;

/**
 * 地牢宝箱战利品：运行中（UDungeonRunSubsystem::IsRunActive）的宝箱开启后按房间深度发放随机奖励。
 * 战利品表 Content/ColdSteelData/dungeon_loot.json 一次性读取并静态缓存（不做热重载）。
 * 编辑器摆放的普通宝箱／非运行场景不进入本逻辑，开启行为与旧版完全一致。
 * 挂接点：ColdSteelWorldInteraction::OpenTreasureChest 的 finish 定时器 lambda（Tags 打上
 * DungeonTreasure.Opened 之后）。全部随机走运行种子的 GameplayStream(ChestLoot^节点散列)，同 seed 可复现。
 */
class FColdSteelDungeonLoot
{
public:
    /** 唯一入口：按档位 roll 战利品并经 UColdSteelStatusModel::AddItem 发放（自动提交），最后一条 PostNotice 播报。 */
    static void GrantFromChest(AActor* Chest);
};
