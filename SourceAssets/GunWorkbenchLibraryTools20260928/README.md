# 枪械工作台：复用库内成品工具

用户要求直接拿现有螺丝刀等小件使用。本批复制已有工具原网格，不新建几何，不减面，不重新展开 UV，不重做材质。

| 桌面工具 | 现有独立对象 | 来源 |
| --- | --- | --- |
| 螺丝刀 | SM_WBK_Fab_Bench_Screwdriver | DungeonWorkbenchKit20260921 |
| 钳子 | SM_WBK_Fab_Bench_Pliers | 同上 |
| 扳手 | SM_WBK_Fab_Bench_Wrench | 同上 |
| 锤子 | SM_WBK_Fab_Wall_Hammer | 同上，原挂墙姿态仅旋转放平 |
| 油壶 | SM_WBK_Bottle_OilCan | 同上 |

保留上一版已恢复的桌子、原版台灯和工作垫。上述工具置于 L 形桌的侧边台面，原尺寸保留，只改变位置和朝向，中央组装工作垫留空。

四件金属工具沿用工程现存 Fab 工具来源与材质，来源记录在 `../DungeonWorkshopFabTools20260921/README.md`。油壶沿用工作台组件库原件。导入时按原独立网格的实际材质槽获取 MaterialInterface，不新建或改写共享材质。

- 可编辑场景：`Authored/GunWorkbench_Editable.blend`，仍保留独立工具对象。
- 作者清单：`Authored/manifest.json`，记录原件路径、摆放、材质槽和复用范围。
- 制作脚本：`Tools/GunWorkbench/place_library_tools.py`。
- 导入脚本：`Tools/GunWorkbench/import_library_tools.py`。
- 目标资产：`/Game/Building/GunWorkbenchLibraryTools20260928/SM_GunWorkbench`，接入既有 `gun_workbench_table`，保留占地、交互和制造页面。

该宿主仍按现有单网格建造流程导出合并副本；可编辑原件与材质引用没有简化。导入保存结果记录在 `import.json` 和 `import.log`。默认不运行游戏、截图或测试。

后台导入已完成，commandlet 返回 0，输出 `LIBRARY_TOOLS_WORKBENCH_SAVED`、`saved: true`、`reused_tools: 5`；模型和建造目录均已保存。未启动游戏或进行视觉测试。

2026-09-28 后续按用户要求读取了已摆放的游戏实例，确认其指向本版本。另修复并保存工作垫与刻度材质缺少 Nanite 使用标记的问题，导入脚本也补上对应设置。详见 `../GunWorkbenchVisibleFix20260928/README.md`；修复后的视觉效果由用户自行测试。
