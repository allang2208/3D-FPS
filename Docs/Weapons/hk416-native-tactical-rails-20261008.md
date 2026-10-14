# HK416 双战术位原装导轨修正

2026-10-08，按用户截图反馈修正 HK416 的普通镭射、战术手电、赐福激光，两侧共 6 份正式资产。其余 10 款枪本次未修改或重新检查。

## 原因与撤回

上一轮通用贴合流程给已有导轨的 HK416 增加了承接块，并改变原装红外组件远端电池盒、线缆的布局，破坏了原装装配关系。第二侧旧旋转轴在真实枪械坐标中的高度约为 96.242 mm，而两侧导轨中心约为 79.134 mm，进一步造成错位。通用坐标下的接触距离与三角面无交叉不足以证明安装合理；撤回该枪此前的合格结论。

本次按实际 HK416 枪械坐标查看侧面、另一侧与顶部。宿主采用 UE 先前实际导出的 `SK_HK416_Manny`，使用前确认包未晚于该导出；原装静态配件重新从 UE 导出。没有将不一致的供应商整枪替代运行时宿主。

## 当前处理

- 普通镭射Ⅰ：恢复原装红外发射器、夹具、盖体、电池盒、线缆的完整源装配，不增加衔接块。
- 普通镭射Ⅱ：按两侧真实导轨中心转到另一侧，发射器、原装夹具和插座作为整体前移 32 mm；远端电池盒后移 16 mm，线缆保留原来的绕枪走向并沿纵向延长，避开另一侧配件。主体与夹具之间没有再做独立偏移。
- 手电Ⅰ、Ⅱ：原装手电和自带夹具整体侧转，将原下导轨夹持面配准到对应侧导轨，不另做承接件。
- 赐福激光Ⅰ、Ⅱ：保留已有主体和键块，复用 HK416 原装 `Laser_sight/mount_low` 夹具，直接接到侧轨；Ⅱ位沿导轨前移 4 mm，错开另一侧原装线缆。夹具原形状及 UV 保留。
- 删除前一轮生成的 `Tactical_Fitted_Bearing` 几何和材质槽。普通镭射与手电保持原材质槽名，保留运行时表面覆盖入口。
- Emitter、AimGuide 随各自主体变换。第二侧导出中补偿旧运行时旋转轴，因此正式路径和 C++ 安装入口无需变更。

## 已保存的正式资产

目录 `/Game/Weapons/TacticalDevices20260913/DualFit20261008/HK416/`：

| 类型 | Ⅰ位 | Ⅱ位 |
|---|---|---|
| 普通镭射 | `SM_laser_1` | `SM_laser_2` |
| 手电 | `SM_flashlight_1` | `SM_flashlight_2` |
| 赐福激光 | `SM_blessed_laser_1` | `SM_blessed_laser_2` |

原装源资产没有覆盖。现有角色、预览、掉落、图标等共用路径直接获得替换模型，双光束与最强数值的逻辑未改动。本次没有 C++ 变更，不需要为此重新编译或重启编辑器。

任务目录：`D:/FPS3D/FPSGAME/SourceAssets/DualTactical20261008/HK416NativeRailCorrection/`。

- `author_native.py`、`Editable/`、`Exports/`、`manifest.json`：可编辑源、导出及安装参数。
- `import_native.py`、`import-receipt.json`：6 份实际导入保存记录。重导入先重建本批 6 份目标的材质槽表，避免 UE 保留已废弃的承接块槽位。
- `readback_saved.py`、`SavedExport/`、`saved-readback.json`：正式包回读和重新导出。
- `review-report.json`：6 份装配范围、原装夹具来源和 9 种两侧组合检查。
- `saved-geometry-report.json`：正式包与源装配的整体表面、逐材质分区比较。

`FitReview/repair_fits.py` 已排除 HK416，显式请求 HK416 时提示使用专用作者入口；`FitReview/import_repaired.py` 跳过 HK416，防止旧通用流程覆盖本修正。

## 本次请求范围内的检查

查看了 6 份修正装配的侧视图，以及双镭射、镭射与手电的顶部组合视图。9 种跨槽配件搭配未检出配件之间的三角面交叉。该结果不等同于游戏内动作或光束效果验收。

6 份正式包回读的材质绑定与插槽一致；Emitter/AimGuide 的记录差异为 0 cm。镭射、手电、赐福激光分别为 1、2、6 个材质分区，没有废弃承接块槽位。重新导出后，整体几何和逐材质分区与修正版的最大表面差异均约为 0.000156 mm，低于 0.025 mm 比较阈值。

后台制作、导入和保存；执行时若编辑器已由外部启动则复用现有桥及互斥。没有主动打开、关闭或重启编辑器，没有运行游戏或 PIE。游戏内装配外观、动作中的遮挡与光束效果由用户测试。

以下为静态几何检查图，金色用于突出配件，实际材质沿用正式资源：

![Ⅰ位原装红外组件](../../SourceAssets/DualTactical20261008/HK416NativeRailCorrection/Review/corrected-laser-1.png)

![Ⅱ位原装红外组件](../../SourceAssets/DualTactical20261008/HK416NativeRailCorrection/Review/corrected-laser-2.png)

![双镭射顶部装配](../../SourceAssets/DualTactical20261008/HK416NativeRailCorrection/Review/dual-laser-and-laser-top.png)
