# 暗纹猎弓木纹表面（2026-09-25）

当时运行弓体 `SM_DarkBow_RiserDetail`（更早回退件 `SM_DarkBow_Riser`）与箭杆槽改为工程内 Normandy 木纹，并按结构分色：弓体胡桃、弓臂枫木、镶条红木、箭杆白蜡。不再使用 Fab 三槽近黑 Phong。运行弓体现已换成木质长弓源 PBR，本套木纹留作回退。已保存资产，未运行游戏、未截图、未做视觉验收。

## 检查结论

| 项 | 实测 |
| --- | --- |
| 原槽 | Material_003 / Material_005 / Material_002，父材质均为 FBXLegacyPhongSurfaceMaterial，无 BaseColor 贴图参数 |
| 商店缩略图 | 整弓接近灰黑剪影，无木纹结构 |
| 槽 0 | 3810 三角，主体／握把附近，UV0 有岛，约 47 cm／UV |
| 槽 1 | 1900 三角，弓梢与反曲外侧，UV0 有岛，约 24 cm／UV |
| 槽 2 | 80 三角，-Y 侧长条，**UV0 面积为 0**（塌缩到单点） |
| 几何 | 仍是已接入的 140 cm 反曲弓体；本轮不改网格、原点、碰撞或挂点 |

槽 2 塌缩 UV 使任何 UV0 木纹只会采到一个 texel。第一人称弓还会旋转，不能用体素块那套 WorldPosition 三平面，否则木纹会跟着准星漂。

## 制作

第一版把同一张胡桃扫描乘相近棕色并加重 AO，三槽读成一块泥色。第二版新建 `M_BowWood_LocalScanV2`：仍用 LocalPosition 三平面（木纹沿局部 Z），但按扫描亮度重新染色，实例可换贴图族。不新增贴图文件；弓体用 `T_RottenWoodSurface_00A`，弓臂／镶条／箭杆用 `T_WoodSurface_00A`。旧母材质 `M_BowWood_LocalScan` 留盘回退。RHAOM 语义不变：R 粗糙、B AO、A 金属（金属固定 0）；`tangent_space_normal=False`。

| 实例 | 绑定 | 木色 | 扫描 | Tint | TileCm |
| --- | --- | --- | --- | --- | --- |
| MI_BowWood_Body | 弓体槽 0 | 胡桃 | RottenWood | 0.34, 0.18, 0.09 | 26 |
| MI_BowWood_Limb | 弓体槽 1 | 枫木 | WoodSurface | 0.86, 0.58, 0.26 | 20 |
| MI_BowWood_Inlay | 弓体槽 2 | 红木 | WoodSurface | 0.46, 0.11, 0.08 | 12 |
| MI_BowWood_Arrow | 箭 ArrowWood | 白蜡 | WoodSurface | 0.90, 0.68, 0.38 | 16 |

原 Material_002/003/005 与 M_ArrowWood 留在盘上作回退。`bows.json` 的 `bow_part_riser_material` 仍为空，三槽都走网格自身绑定；表现版本 11。弦、箭镞、尾羽、箭尾材质未改。

作者脚本 `SourceAssets/DarkBow20260925/WoodFinish20260925/recolor_structure_woods.py`（`install_bow_wood.py` 已转调此脚本）。已打开编辑器时走 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript`。回执 `structure_woods_receipt.json`。恢复静态件时 `ArmsV2/import_parts.py` 若见到上述实例会重新绑定。

本次未做游戏测试，色调和疏密由用户进游戏看。
