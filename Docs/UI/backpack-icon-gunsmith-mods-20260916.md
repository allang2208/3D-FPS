# 背包与装备栏枪械图标的改造同步（2026-09-16）

## 现象

背包、装备格、仓库、物品浮窗和拖动预览共用 `UColdSteelWeaponIcons` 的透明底实时图：先显示目录底图 `Content/ColdSteelData/Icons/<定义>.png`，实时改装图就绪后替换。实际游戏中只有 M4、M1911 的图标反映了已安装改造，AKM 与 QBZ-191 始终停在基础目录图。

## 排查

1. 现有运行日志（`Saved/Logs/FPSGAME-backup-2026.09.16-11.59.10.log`）显示 AKM/QBZ-191 的任务已按实例配件入队并完成组装（`parts=8` / `parts=10`），随后失败：
   - `WeaponIcon: material compile failed /Game/Weapons/QRPerformanceStock/Meshy20260913/M_Stock_Rubber: (Node Clamp) Missing Clamp input`
   - `WeaponIcon: render failed ue_akm|…; using catalog image`、`… ue_qbz191|…; using catalog image`
   M4 之所以正常，是因为当前 M4 实例使用 `tactical_telescopic` 枪托与 `balanced_reargrip`，没有加载到有缺陷的材质。
2. 面板代码本身没有问题：`ColdSteelInventoryWidget`/`ColdSteelItemTooltip`/拖动预览都优先取 `WeaponIcons->Find(Item)`。问题在生成端——`UColdSteelWeaponIcons::Tick` 在编辑器下遇到任一参与材质编译错误就放弃本次任务（该退避用于避免等待永远不就绪的 shader），于是整张改装图退回基础目录图。
3. 扫描 `Content/Weapons` 全部 504 个材质资产（其中 35 个含 Clamp 节点），确认 8 个同类缺陷材质：clamp 已接到 `MP_ROUGHNESS`，但 clamp 的输入引脚为空。

| 材质 | 影响 | 作者脚本记录的原始接线 |
| --- | --- | --- |
| `QRPerformanceStock/Meshy20260913/M_Stock_Rubber` | `qr_performance` 枪托橡胶件（AKM/M4/QBZ-191） | `T_Stock_Roughness` 采样 `.R` → Clamp 0.75–1 |
| `CoreStock20260914/M_CoreStock_Rubber` | `core_stock` 橡胶件 | `T_CoreStock_MetalRough` 采样 `.G` → Clamp 0.75–1 |
| `CoreStock20260914/Meshy0914005605/M_CoreStock_Rubber` | `core_stock`（AKM/M4/QBZ-191 实际网格） | `T_CoreStock_Roughness` 采样 `.R` → Clamp 0.75–1 |
| `ReferenceStock5080/Refined91379/M_SkeletonStock_Rubber` | `skeleton` 枪托橡胶件 | `T_SkeletonStock_MetalRough` 采样 `.G` → Clamp 0.75–1 |
| `StableAntiSlipRearGrip/Selected91727/M_StableAntiSlipRearGrip` | `stable_antislip_reargrip` | `T_StableAntiSlipRearGrip_MetalRough` 采样 `.G` → Clamp 0.55–0.95 |
| `QBZ191/SurfacePolish/M_QBZ191_Body_SurfacePolish` | 未被当前网格引用 | `Multiply → Add` 链输出 → Clamp 0.28–0.78 |
| `QBZ191/SurfacePolish/M_QBZ191_Irons_SurfacePolish` | 未被当前网格引用 | 同上，Clamp 0.38–0.78 |
| `QBZ191/SurfacePolish/M_QBZ191_Magazine_SurfacePolish` | 未被当前网格引用 | 同上，Clamp 0.28–0.78 |

接线依据来自各自作者脚本，不是推测：`SourceAssets/MeshyPerformanceStock20260913/import_assets.py`、`SourceAssets/CoreStock20260914/import_assets.py`、`SourceAssets/CoreStock20260914/Meshy0914005605/import_assets.py`、`SourceAssets/ReferenceSkeletonStock5080_20260913/Refined/import_assets.py`、`SourceAssets/StableAntiSlipRearGrip20260913/Selected91727/import_assets.py`、`SourceAssets/QBZ19120260912/SurfacePolish/import.py`。

## 修改

- 按作者脚本恢复这 8 个材质的 clamp 输入接线；不改贴图、不改 clamp 区间、不动其它属性和材质槽。未通过编译的资产不写盘（修复失败等于完全不动）。
- 无界面扫描与修复：`Tools/UI/scan_weapon_material_clamps.py`（只读审计）、`Tools/UI/repair_weapon_roughness_clamps.py`（按材质表恢复接线）。
- `M_Stock_Rubber` 修复时被正在运行的编辑器独占（Restart Manager 确认持有者 `UnrealEditor.exe`），改用 `Tools/UI/repair_qr_stock_rubber_in_editor.py` 通过该编辑器的远程执行写入同一接线，`before=(Node Clamp) Missing Clamp input` → `after=<clean>` → 保存成功。
- 备份与记录：`Saved/BackpackIconModFix20260916/before/`（8 个原始 `.uasset`）、`repair-report.json`、`repair.log`、`repair-retry.log`、`scan-after.log`。

## 结果与边界

- 复核结果：504 个材质、35 个含 clamp，编译失败 0（修复前 8）。依据为无界面 `recompile_material`，未启动游戏。
- 这批材质同属游戏内视图模型的枪托/阻手外观，因此同时消除了视模上"材质编译失败 → 默认材质回退"的隐患。
- 未重跑目录图导出，未做视觉验收；背包与装备栏的实际表现由用户测试。
- 失败键在 `UColdSteelWeaponIcons` 生命周期内记入 `Failed`，已运行过的编辑器/游戏进程需重启后才会重新生成这些改装图。
- 仍无可视化资产的改造项：M1911 扳机 `m1911_lightweight_fast`、Dan-Wesson 715 扳机 `dw715_lightweight_fast`、装填装置 `dw715_speedloader`。这些槽位目前没有独立静态网格模型，图标无法表现；模型补齐后无需改代码即可走同一条实时图路径。

## 工具注意事项

- `unreal.MaterialEditingLibrary.get_material_property_input_node` 在交互编辑器的远程执行里会让 `UnrealEditor-MaterialEditor.dll` 访问违例崩溃（本次已发生一次，未保存任何资产）。材质属性/接线查询请放在无界面 `UnrealEditor-Cmd -ExecutePythonScript` 进程内，或在编辑器内改用只依赖 `get_material_expressions` / `connect_material_expressions` / `recompile_material` 的脚本。
- 读取被打开资产的独占锁归属可用 Restart Manager（`rstrtmgr.dll` 的 `RmStartSession`/`RmRegisterResources`/`RmGetList`）确认，不必强杀进程。
