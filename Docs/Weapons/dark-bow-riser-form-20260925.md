# 暗纹猎弓弓体结构重构（2026-09-25）

用户确认按「现轮廓加结构、不再全局磨圆」开工。Blender 5.1 已在原 5.6k 笼子上做出抄把、箭台、凸起镶条、弓臂层板和弦槽；71k 细节弓只作对照，未当底模。无界面 commandlet 已导入 `SM_DarkBow_RiserForm`，当时 `bows.json` 表现版本 12。运行弓体现已换成木质长弓，本网格留作回退。未进游戏验收。

## 现模型

原 Fab 拆分弓去掉 124 个烘焙弦三角后，侧看是 3.51 cm 厚的平板，握把截面约 3.3x3.5 cm，镶条 80 三角。上一轮倒角加细分只把硬边磨顺，轮廓没变。

## 制作

独立目录 SourceAssets/DarkBow20260925/RiserForm20260925/。以 ArmsV2/bow_surface.json 为笼子：

- 握把区顶点向背侧/两侧鼓起（1592 点）
- 镶条外侧面挤出约 2.4 mm
- 弓臂 inset 做出层板台阶
- 弦侧加 4.6x1.4x1.6 cm 倒角箭台
- 在弦口键上 Exact 布尔开槽
- 折痕保护新结构后，全网格一档 Catmull-Clark
- 加权法线；不把弦烘回网格

| 项 | 笼子 | 结构版 |
| --- | --- | --- |
| 三角 | 5666 | 20124 |
| 槽 | Body 3810 / Limb 1776 / Inlay 80 | 11068 / 7952 / 1104 |
| 厚度 | 3.511 cm | 5.306 cm |
| 全长 | 139.999 cm | 139.844 cm |
| 弦口偏差 | 0.32 cm | 0.15 cm |

握把原点仍在 0。弦口键未改。反曲钩梢保留。RiserDetail 与原 SM_DarkBow_Riser 留作回退。

## 接入状态

作者脚本 author_riser_form.py，导出 Export/SM_DarkBow_RiserForm.fbx。导入脚本 import_riser_form.py 已写入 /Game/Weapons/DarkBow20260925/RiserForm20260925/SM_DarkBow_RiserForm（先 ×100 再翻 Y），三槽绑回木纹实例。引擎包络 35.2 × 4.5 × 137.4 cm。回执 import_receipt.json。已打开编辑器时走 mcp_call_codex.ps1 -PythonScript；未运行时走 Scripts/run_headless.ps1。

本次未做游戏测试。
