#pragma once
#include "CoreMinimal.h"
#include "../UI/ColdSteelInventoryTypes.h"

/**
 * 采集工具（伐木斧、矿镐）强化的等级阶梯目录。
 *
 * 与武器／防具强化（`UColdSteelEnhancementSystem`）不同：工具强化是**外观档位**，
 * 只换金属部位材质槽的材质实例，不换网格、不加数值。独立字段 `tool_enhance_level`
 * 写在物品 Data 里（与 `gunsmith_parts` 同级，不进定义刷新白名单），缺字段＝1 级。
 *
 * 目录条目数就是强化上限；`cost`／`stats` 本次恒为空对象，加载器解析但不使用，
 * 因此这里**不提供**任何消耗或数值访问器。等级规则为逐级 +1、不可降级、不可跳级。
 *
 * 与同目录 `ColdSteelTool::Evaluate` 的分工：那一份只算改造后的实值，不读本等级。
 */
struct FToolEnhanceLevel
{
    int32 Level=1;
    FString Id,Name,Description;
    /** 工具定义 ID（`tool_axe`／`tool_pickaxe`）→ 金属槽材质实例路径。 */
    TMap<FString,FString> Materials;
};

namespace ColdSteelToolEnhance
{
    /** 等级阶梯，按目录顺序。目录缺失时为空。 */
    const TArray<FToolEnhanceLevel>& Levels();
    /** 强化上限＝目录等级条目数；目录缺失时为 1（出厂等级）。 */
    int32 MaxLevel();
    /** 目录 `metal_slot`，缺省 `Metal`。按槽名找材质索引，不按固定索引。 */
    FString MetalSlotName();
    /** 按等级取条目；没有该等级返回空。 */
    const FToolEnhanceLevel* Find(int32 Level);
    /** 物品当前等级：读 Data 的 `tool_enhance_level`，缺字段＝1，夹在 [1,MaxLevel]。 */
    int32 Level(const FColdSteelItem& Item);
    /** 逐级 +1：仅当 Level<MaxLevel 时为真，OutNextLevel＝Level+1。不可降级、不可跳级。 */
    bool CanEnhance(const FColdSteelItem& Item,int32& OutNextLevel);
    /** 金属槽材质路径；LevelOverride<=0 时用实例等级。找不到返回空串＝保持现有材质。 */
    FString MetalMaterialPath(const FColdSteelItem& Item,int32 LevelOverride=0);
    /** 等级中文名；没有该等级返回空。 */
    FString LevelName(int32 Level);
}