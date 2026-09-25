# 暗纹猎弓木质长弓替换（2026-09-25）

用户提供 `D:\FPS3D\资产\source.glb`（Sadra Medieval Wooden Longbow）。原 Fab 平板弓不再改形。独立目录 `SourceAssets/DarkBow20260925/WoodLongbow20260925/`。未进游戏验收。

## 制作

- 删除烘焙弦 `sweep4`
- 握把缠线中心归零，弦侧翻到局部 -X
- 源网格按米写入会让 5.8 FbxFactory 塌成约 1320 三角；导出前顶点改成厘米
- 米制 FBX、GLB、40k 减面、Content 探针包和一次性日志已归档，清单 [wood-longbow-probes-20260926.json](../AssetArchives/wood-longbow-probes-20260926.json)
- 引擎包络 28.0 x 7.0 x 141.8 cm，219630 三角
- 源 4K PBR（BaseColor / ORM / Normal），不绑木纹 V2
- 弦口按新外形重测；程序化弦、木箭、ContactV9 手臂未改
- `RiserForm` / `RiserDetail` / 原 Fab 拆分弓留作回退

## 接入

`bows.json` 表现版本 14，弓体 `/Game/Weapons/DarkBow20260925/WoodLongbow20260925/SM_DarkBow_WoodLongbow`。旧存档若仍挂 `RiserForm` 等官方弓体，会在加载时换成这把；玩家自制换件不覆盖。回执 `import_receipt.json`。已打开编辑器时走 `mcp_call_codex.ps1 -PythonScript`；未运行时走 `Scripts/run_headless.ps1`。

本次未做游戏测试。