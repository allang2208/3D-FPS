# 独立工作台建造构件（2026-09-24）

把地牢车间的 L 形工作台（`Content/Dungeons/AtmosphereV2/RoomInteriors/WorkbenchKit`）提取成一件**独立可建造构件**，
在 Blender 中优化细节并在桌面添加工具、图纸与书籍布置，注册进玩家建筑面板（`DA_VoxelBuildPalette` 的「其他」分类，
Id `workbench_table`，显示名「工作台」）。

## 提取范围

保留（`Config` 见 `author_standalone.py` 的 `KEEP`）：

- 台面与框架：`Bench_BenchTop`、`Sculpt_BenchFrame`、`Fab_BenchRetained`（台钳＋工具挂架）；
- 台灯：`Bench_TaskLamp`、`LampFlex`（夹在台面边，不依赖墙）；
- 台面物件：扳手／螺丝刀／钳子／凿子、油壶、除油剂瓶、抹布。

剔除：全部壁挂件（工具墙 `Surface_Toolboard`、洞洞板零件 `Fab_Mounts`、`Fab_LabelsRetained`、
`Surface_Organizer`、`Surface_UtilityDetail`、全部 `Fab_Wall_*` 挂装工具）、
依赖墙面插座的 `PowerLead`/`SocketPlug`，以及与台面共面、合并后会 z-fighting 的 `BenchWear` 贴花层。

## Blender 制作（`Scripts/author_standalone.py`）

- **减面优化**：BenchRetained 204k→37k、台灯 56k→11k、框架 44k→18k、台面 39k→11k、抹布 28k→7k、
  瓶罐与软线同比例削减；最终合并网格 **134,110 三角**（UE 侧 >70k 自动开 Nanite）。
- **工具迁移**：壁挂锤、手锯、活动扳手改为平放桌面（绕轴转正后 AABB 落台面 +1.5 mm）。
- **新增桌面布置**（程序化生成，低模）：
  - 展开图纸 ×2（A2 大图＋A4 小图，蓝晒制图：齿轮主视图、剖视、尺寸线、标题栏）；
  - 图纸卷 ×2；书堆 ×3（红/藏青/墨绿皮面＋烫金书带＋奶油书页）；摊开的书 ×1；
  - 铅笔 ×1；黄铜零件盘＋铁钉 ×7。
- 贴图由 `make_clutter_textures.py`（PIL）生成：`T_WBKC_Blueprint/Books/Misc_BaseColor.png`。
- 全部合并为单一网格 `SM_WBStandalone_Workbench`（34 个材质槽，包围盒居中、底面 z=0），
  导出 `Authored/SM_WBStandalone_Workbench.fbx` + `manifest_build.json`，工程存 `Authored/StandaloneWorkbench.blend`。

## UE 落库（`Scripts/import_standalone.py`，`-run=pythonscript` 后台 commandlet）

- 资产位置：`/Game/Building/Workbench/{Textures,Materials,Meshes}`（与地牢资产解耦）。
- 材质：地牢套件部件直接复用 WorkbenchKit **InUse** 变体 MI（含灯泡自发光）；
  三件新 MI（`MI_WBKC_Paper/Books/Misc`）以套件参数化母材质 `M_WBK_Surface` 为父，仅接基色贴图。
- 网格：合并导入，按槽名映射材质；碰撞 `CTF_USE_COMPLEX_AS_SIMPLE`；>70k 三角开 Nanite。
- 面板注册：`DA_VoxelBuildPalette.Components` 追加/就地替换 `workbench_table`，
  Footprint 按导入后包围盒逐轴向上取整（20 cm 格），`Mount=Free`，`Surface=槽 0 材质`（放置路径
  `SetMaterial(0,Surface)` 为无害同值覆写），`Material` 留空 → 出现在「其他」分类。

## 已知取舍（未测试，按用户规则由用户自行验收）

- 单网格方案没有地牢版的台灯 `SpotLight`（灯泡材质仍自发光）；如需真打光，后续可把它升级成
  `ActorClass` 逻辑构件（参照火把/喷泉先例），面板路径不变。
- 图纸小角、手锯等个别摆件有 ≤1 cm 悬出台缘，属预期生活化效果；Footprint 已按实际包围盒取整。
- 地牢原工作台与 `BP_Workbench_*` 蓝图**未做任何改动**，本构件是独立提取副本。

## 复现

```powershell
python SourceAssets/WorkbenchBuildable20260924/Scripts/make_clutter_textures.py
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' -b --python-exit-code 1 `
  --python SourceAssets/WorkbenchBuildable20260924/Scripts/author_standalone.py
# 编辑器关闭时：
& 'E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe' `
  D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript `
  -script=D:/FPS3D/FPSGAME/SourceAssets/WorkbenchBuildable20260924/Scripts/import_standalone.py `
  -unattended -nop4 -nosplash -NullRHI
```

预览图：`Renders/preview-*.png`（提取子集）、`Renders/built-*.png`（成品四视图）、`Renders/zoom-*.png`（桌面特写）。
回执：`Receipts/ue-import.json`、`Receipts/kit-blend-inventory.json`。


## 桌面布局修正（2026-10-04）

针对实际用于斧头／矿镐制作的 `workbench_table`，仅修正独立工作台，不修改枪械工作台或地牢母版。

- 保留桌架、台灯、抹布、台钳、套筒架与原金属盘；书堆移出台钳，书、锯、纸卷、瓶罐、工具与零件盘分区摆放。锤子和活动扳手按实际薄轴平放；铅笔落在图纸上，七枚钉子在盘内分开。
- 作者入口 `Scripts/author_standalone.py` 调用 `Scripts/layout_tabletop.py`；分件编辑源 `Authored/WorkbenchLayout_Editable.blend`，位置与支撑面回执 `Authored/layout_tabletop.json`。合并 FBX 和 `StandaloneWorkbench.blend` 已同步。
- 源网格仍为 **134,110 三角 / 68,705 顶点 / 34 源材质槽**；UE 保留原 **32 个实际材质槽**（无面源槽由 FBX 导出剔除）、Nanite 设置、复杂网格碰撞以及原资产路径。
- 保留原枢轴和放置包围盒、`13 × 14 × 8` 格占地。收回原来伸出台缘的图纸后，通过 Bounds Extension 保留放置边界，不改变既有调色板或建筑存档合同。`manifest_build.json` 中 `placement_bounds_cm` 随作者入口复现。
- 导入门限改为完整 FBX SHA-256，修正已有网格替换判断。实际执行生产导入器的网格段，在临时未保存资产上将钳子平移 1 cm，保持面数和总包围盒完全相同，确认二次导入触发；临时资产随后移除。

本轮已在 UE 保存正式网格并拍摄前后俯视、观察及原生玩家相机对比。Blender 对移动摆件与其余分件逐对检查，未发现三角面交叉。独立 `WorkbenchLayoutAudit_20261004` 存档通过原建筑 `PlacePrefab` 入口放置，原生 E 打开工作台＋背包，原生键盘选择矿镐后显示木材 1／石块 2；伐木斧显示木材 1／石块 1。隔离存档没有材料，未测试扣料和成品入包事务。

验证没有修改正式玩家存档、配方 JSON、建造调色板、地图或 C++。运行画面存在引擎光追驻留几何预算提示，本次未调整渲染设置，不能据此归因于桌面布局。


## 工程图纸与小工具（2026-10-04）

本轮升级同一个 `workbench_table`，正式网格仍为 `/Game/Building/Workbench/Meshes/SM_WBStandalone_Workbench`。

- 米白工程纸包含斧头正／侧视、矿镐正视、尺寸线、连接剖面、装配细节和标题栏。它是游戏装饰图案，标注 NTS，不作为精密制造图。
- 新增游标卡尺、直角尺与手锉，复用既有材质。保留上轮布局及固定构件；作者源包含 35 个分件，移动摆件三角面交叉检查为空。
- `Scripts/engineering_drawings.py` 生成图集，`make_clutter_textures.py` 调用同一入口；`Scripts/engineering_tools.py` 由 `author_standalone.py` 调用。编辑 Blend、合并 Blend、FBX、清单和布局回执同步。
- 源文件为 `Authored/Textures/T_WBKC_Blueprint_BaseColor.png`；实际 UE 纹理身份是 `/Game/Building/Workbench/Textures/T_WBKC_Paper_BaseColor`，由 `MI_WBKC_Paper` 的 `BaseColorMap` 引用。不要按 PNG 文件名猜 UE 资产名；生产导入器按 `WBKC_Paper` 材质键生成目标名。
- 源网格 149,982 三角／79,509 顶点；UE GeometryScript 转为 DynamicMesh 后读取 149,975 三角（差 7，转换差异原因未追查），32 个 UE 材质槽。原材质映射、Nanite、复杂碰撞、枢轴与 13×14×8 格占地保持。源 FBX SHA-256 与 UE 导入元数据一致。

已完成：UE 严格正交垂直俯视截图；独立 `WorkbenchEngineeringAudit_20261004` 存档使用原生 PlacePrefab 放置并按 E 打开工作台和背包，列表显示伐木斧与矿镐。正式四份玩家存档／校验文件、配方 JSON、建造调色板与 Hub 地图哈希未变。本任务编辑器已关闭，没有提交或推送。

误导入的同目录 `T_WBKC_Blueprint_BaseColor.uasset` 经确认是本任务新增且无包引用，编辑器退出后移入 `trash/workbench-engineering-20261004-misimport/`，保留原路径和 SHA-256，可恢复，未永久删除。

未测试：实际制作扣料／成品入包、完整配方流程、正式存档重载、全面碰撞和性能。回执与修改清单见 `Receipts/engineering-20261004.json`。本轮不把上轮验收结果算作重复通过。
