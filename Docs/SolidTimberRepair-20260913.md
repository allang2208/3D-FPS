# 可拾取原木空心、碎面修复

用户明确问题发生在地上可拾取的短原木。本次针对三款原木进行几何、材质绑定和实际模型渲染检查，并修复、导入和切换运行引用。

## 原因

初版模型从带纹理的生成母版直接减面，没有先处理 UV 分岛处重复顶点。减面后表面分裂成大量碎片；随后对边界统一补洞，也未形成两端的完整截面。生成母版本身另有残余裂缝，单纯焊接仍剩 1752 条开口边，不能用双面材质掩盖。

初版 FBX 的有效开口边数为 A=10698、B=10129、C=10670；负 X 端均无封面，正 X 端仅存在几乎零面积的碎面。检查图：`SourceAssets/HarvestTimber20260913/SolidRepair/before_logs.png`；数据：同目录 `before_geometry.json`。

## 修复

沿保留母版的外形采样，重建连续的环形网格与统一侧面 UV；从母版重新烘焙 2K 树皮颜色、粗糙度及切线法线。按各自长度切割，用同一圈边界完整封住两端、显式三角化，并赋予独立年轮材质。树皮和端面均为不透明材质。

新资源为 `/Game/Items/HarvestTimber/SM_PoplarLog_Solid_A/B/C`，C++ `ProductionHarvestAssets::PickupMesh` 已切换。保留原有物品 ID、数量、拾取及物理接口；读档中的旧木材也按同一物品定义选用新版网格。原树树桩和倒树系统不在此次修改范围。

## 本次检查结果

将已保存的 UE 网格再次导出，在 Blender 中检查并渲染：

| 原木 | 三角形 | 连通体 | 开口边 | 非流形边 | 两端朝向 |
|---|---:|---:|---:|---:|---|
| A | 6332 | 1 | 0 | 0 | 全部朝外 |
| B | 5756 | 1 | 0 | 0 | 全部朝外 |
| C | 6332 | 1 | 0 | 0 | 全部朝外 |

每端为 94 个三角形，断面和树皮共享边界，正体积且封闭。已确认 UE 材质槽分别绑定 `M_PoplarSolidBark` 与 `M_PoplarSolidEnd`。最终图为 `SolidRepair/engine_logs.png`，属于 **UE 导出网格在 Blender 中的检查图，不是游戏截图**；所用材质为对应源 PBR。`engine_geometry.json` 按导入对象的真实变换换算为米，记录两端面积和朝向。

Editor 原生构建成功，资源导入脚本执行成功。未运行 PIE 或整局玩法回归；用户重启 UE 后复看拾取木材。Commandlet 仍记录项目已有的 GameFeatureData 配置与 MCP 端口占用错误，因此只报告本次脚本完成，不宣称整个进程无错误。

## 文件

- `SourceAssets/HarvestTimber20260913/repair_solid_logs.py`：连续表面重建、PBR 烘焙和封口。
- `import_solid_logs.py`：导入并导出保存后的 UE 网格。
- `inspect_log_geometry.py`：初版/修复版/UE 导出网格的定向检查和渲染。
- `SolidRepair/SolidTimber_Editable.blend`：可编辑修复源；`SolidRepair/Delivery`：FBX 和 PBR 贴图。
- `Saved/Logs/SolidTimber-Build.log`、`SolidTimber-Import.log`：本次构建和导入记录。

仍使用上一轮生成母版及年轮参考，没有购买新资产。初版二进制和旧作者脚本已移入本机 `trash/harvest-timber-superseded-20260913`；冻结母版与当前重建依赖照常保留。运行版本的重建入口以 `repair_solid_logs.py` 为准，恢复顺序见 [当前制作入口](../SourceAssets/HarvestTimber20260913/README.md)。
