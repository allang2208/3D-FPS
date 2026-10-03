# 枪械工作台实际实例定位及材质修复

2026-09-28，用户反馈已摆好的枪械工作台外观未变化，明确要求读取实际场景实例。

## 实际读取结果

- `runtime-120124.json`：`DayNight_Lighting` 中，角色身边约 136 cm 的 `VoxelBuildPrefabActor_4` 已引用 `GunWorkbenchLibraryTools20260928/SM_GunWorkbench`。
- 建造目录与该实例一致。当前模型的 23 个材质槽包括原库台灯、螺丝刀、钳子、扳手、锤子、油壶的材质。
- 此实例没有禁用 Nanite；全局 `r.Nanite=1`。不能把普通 LOD0 的 1430 个回退三角形数量当作实际 Nanite 显示面数，也没有据此修改原模型。
- 先前“旧实例仍引用旧模型”的猜测在该实例上不成立。

## 本次确实发现并修复的问题

原游戏日志明确报告 `M_GW3_Mat` 和 `M_GW3_Index` 缺少 Nanite 使用标记，游戏将使用默认材质。后台加载也读到两者标记为 false。

已启用并保存这两个材质的 Nanite 使用标记。其它已绑定的原库材质具备该标记，无需修改。同步补齐 `import_station_polish.py` 与 `import_library_tools.py` 中的对应导入设置。

`material-fix-commandlet.log` 与 `material-fix.json` 记录保存成功；后台 commandlet 退出码 0。修改前资产保存在本目录 `Before` 下。

## 范围与限制

用户随后选择“先修复已发现的问题，我之后自行测试”。因此没有继续启动游戏、截图或视觉验收。本次修复的是已证实的工作垫及刻度材质问题，不能声称它解释或解决了全部台灯、工具观感问题。

`runtime-before.png` 实际捕获到的是游戏结束后的编辑器空场景，不是工作台效果图，不得当作视觉验收证据。
