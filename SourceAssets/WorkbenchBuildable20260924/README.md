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
