# 接待大厅一楼覆盖范围调整

用户希望灯光覆盖更广，并询问二楼灯照不到一楼是否应加亮度。本次调整照射距离，光强和朝下方向保持原值。

- 二楼局部回廊灯原射程 704 cm，发光高度约 822.8 cm；其功能仍是二楼本层照明。楼板下方由一楼对应灯具负责，不能靠增亮实现穿楼板照明。
- 中庭 6 条主吊灯配方的 `radius` / `optimized_radius_cm` 由 1496 cm 改为 2000 cm，扩大一楼开放区域内的可覆盖范围并减轻远处的半径衰减。原锥角 74° 已较宽，保持不变。
- 主灯亮度、颜色、灯位、故障闪烁和熄灭状态不变。原未投影的常亮中间主灯启用阴影，扩大范围后仍由墙体和楼板阻挡；实际常亮/故障主灯的投影数由 4 增至 5。没有添加新灯。
- 全局 Lumen、曝光、地牢房间调度和原有最大绘制距离保持不变。

正式地图 `/Game/GameMaps/L_Dungeon_Randomized` 的灯光目录已保存；接待大厅样板及两个连接大厅样板中的接待厅副本也已保存，共 4 张地图。源目录与布局 bank 的签名同步更新，120 套摆放数据未调整。当前正在游玩的 PIE 副本未改；重新进入随机地牢后使用新目录。

重建入口通过 `SourceAssets/ReceptionLighting20261009/recipe.py` 的 `apply_coverage` 与 `apply_subject_coverage` 重放；两个连接大厅副本的恢复入口为 `SourceAssets/DungeonFixtureLighting20261009/world_lights.py`。安装源与保存回执位于 `SourceAssets/ReceptionCoverage20261009`，回执 `Receipts/install.json` 的最终状态为 `maps_saved`。

本轮完成参数修改与实际保存，没有运行游戏测试、方向回归、截图或渲染；覆盖效果由用户体验。此次为资产参数调整，无 C++ 编译需要。
