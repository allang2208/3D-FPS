# 密集高草测试场景

用户请求：制作铺满高草的场景，安排传送门，由用户进入测试。

## 场景与入口

- 地图：`/Game/GameMaps/L_GrassDeformDenseTest`。
- 主体为 64 × 64 米高草，40 cm 间距加随机偏移，固定种子 20260926。除西侧出生／返回门的小块空地外全部铺草。
- 使用现有 PN Grass Library 丘陵复制品 `SM_Meadow_grass_03_08_mesh` / `SM_Meadow_grass_05_03_mesh`，按网格实际包围盒缩放到 130–170 cm，保留原 LOD、材质、顶点色及 Pivot Painter UV。
- 材质沿用 `M_TemperateMeadow` → `MF_GrassDeform`，不复制第二套踩踏系统。两组 HISM 预先烘入地图，无逐实例 Tick 或运行时散布；无草碰撞／阴影，保留地面阻挡与草地脚步材质命名。
- 主场景 `DayNight_Lighting` 和丘陵 `L_TemperateHills_Initial`：玩家出生位置左侧 6 米出现 **TALL GRASS / Dense Test** 门。靠近 2 米内按 **E**。
- 草场出生点 `(-3070, 0, 110)`，朝 +X 面向高草；返回门在身后 `(-3500, 0, 0.5)`。从丘陵进入携带 `GrassReturnHills`，返回带 `HillsContinue`；从主场景进入返回主场景。
- 返回门由 GameMode 幂等安装；任一地图尚未生成玩家时继续等待，避免非丘陵地图错过安装时机。
- 地图加入 `MapsToCook`；此次不执行打包。

## 制作入口

原生类：`Source/FPSGAME/WorldGeneration/GrassDeform/GrassDeformTestField.*`。

工程空闲时先执行 `Tools/Build/Build-Editor.ps1`，再执行 `Tools/GrassDeform/run_dense_test_level.ps1`。作者脚本为 `author_dense_test_level.py`，只重建本地图 `GrassDenseTest.Authored` 标签的对象；再次制作前备份自有地图／地面材质。

制作回执写入 `SourceAssets/GrassDenseTest20260926/authored-*.json`，记录实际实例数量及保存路径。没有运行游戏、PIE、截图或性能采样；效果与性能由用户自行测试。

当前状态：2026-09-26 已完成普通原生构建、后台地图生成及地面材质保存。实际烘入 **25,494 丛**（两组分别 12,876 / 12,618），未运行游戏测试。

- 构建记录：`Saved/BuildEditor/build-20260926-201744.log`。
- 资产生成记录：`Saved/Logs/GrassDenseTest-20260926-201930.log`。
- 制作回执：`SourceAssets/GrassDenseTest20260926/authored-20260926-201943.json`。

用户随后授权了运行检查，结果见 [密集高草运行检查](grass-dense-validation-20260926.md)：核心 24 项断言通过，但存在强压平折片和返回主场景加载失败，不能将本场景标为全部验收通过。
