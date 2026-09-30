#pragma once
#include "CoreMinimal.h"
#include "ProductionToolEnhance.h"

class UStaticMeshComponent;
class USkeletalMeshComponent;

/**
 * 采集工具强化的**唯一外观落地点**：把 `tool_enhance_level` 对应的金属材质实例
 * 设到网格的 `Metal` 槽上。世界／掉落／工作台预览走静态网格重载，第一人称视模走
 * 骨骼网格重载。
 *
 * 只换已存在槽的材质，**不换网格、不换挂载角度、不新建 `UMaterialInstanceDynamic`**
 * （材质实例是共享资产，每实例建 MID 会撑爆着色器变体）。因此本模块对升级路径是
 * 安全的：`DataHash` 变化 → `RefreshHeldTool` 路径 ② → `ApplyToolStats` → 这里。
 *
 * 资产（阶段 2）未到位时的降级：材质路径仍指向不存在的资产，`LoadObject` 返回空，
 * 此时**保持现有材质**、只 log 一次 Warning，不报错、不弹窗、不刷屏。同样地，
 * 当前世界网格与视模还是单槽（未拆槽），找不到 `Metal` 槽也保持现状、只 log 一次。
 */
namespace ProductionToolAppearance
{
    /** 世界／掉落／工作台预览网格。LevelOverride<=0 时用实例等级。 */
    void ApplyLevel(UStaticMeshComponent* Mesh,const FColdSteelItem& Item,int32 LevelOverride=0);
    /** 第一人称视模。LevelOverride<=0 时用实例等级。 */
    void ApplyLevel(USkeletalMeshComponent* Mesh,const FColdSteelItem& Item,int32 LevelOverride=0);
}