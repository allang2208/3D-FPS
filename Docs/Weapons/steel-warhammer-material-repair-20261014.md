# 战锤白模修复

用户反馈战锤显示为白模。本次只排查战锤材质资产、当前视模槽位及对应导入链；没有运行游戏。

## 已定位原因

1. 当前实际加载的 `SprintDragV1/SK_Warhammer_BareArmsSprintV1` 四个材质槽在独立进程读取时均为 `null`，其中第 0 槽为战锤本体。导入脚本遍历 Unreal struct 数组时，只修改了循环中的 `SkeletalMaterial` 值，没有将它重新写入 `slots[i]`。旧版网格的锤体槽有材质，但当前冲刺版网格没有。
2. `M_SteelWarhammerSurface` 原始基色、法线与金属度/粗糙度贴图均存在，骨骼网格用途也已开启；但材质仅连接传统通道，`FrontMaterial` 为空。项目已启用 Substrate，需接通该渲染路径。

原始证据：`SourceAssets/SteelWarhammer20261014/MaterialRepairV1/material_before.json`。

## 修复范围

- 将现有三个 PBR 贴图通过 UV0 接入 `MaterialExpressionSubstrateShadingModels`，保留粗糙度 G、金属度 B、基色 RGB 与法线 RGB 的原通道，连接 `FrontMaterial`。
- 当前视模锤体槽重新绑定共同的战锤材质；三个手臂槽按名称恢复到原生 V7 Pickaxe 裸臂材质。
- 修改初次导入和冲刺版导入脚本，在更新每个材质结构后写回数组。原始导入脚本复用 `warhammer_surface.py`，后续导入继续生成正确的 Substrate 图。
- 只保存战锤共同材质和当前视模两个资产；保持模型几何、骨架、三连击动画、握姿和伤害逻辑。

## 记录

修复脚本、原资产备份、材质编译/保存回执及独立进程回读结果位于 `SourceAssets/SteelWarhammer20261014/MaterialRepairV1/`。此次没有 C++ 修改，无需重新构建游戏模块。未进行游戏画面验收。
