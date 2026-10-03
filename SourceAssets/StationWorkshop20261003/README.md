# 车站维修兼调度工作间

在现有 `AbandonedTransitStation` 内制作固定的 10 × 7 m 工作间，顶棚底面 3.2 m，局部原点 `[-450,850,0]` cm。包含人员门、双扇宽维修门、半高墙与观察窗；开口同时保留在几何和碰撞中。工作间与门外作业区均位于原站台范围内。

维修区复用 `DungeonWorkbenchKit20260921` 的 L 形台、工具板、工具、灯和电源线；新增电机拆检台、零件货架、调度桌与电脑、电话、对讲机、详细告示、线管支架及维修推车。容器复用仓库三类箱子和工具柜，并补做调度文件抽屉。

三种种子布置为 `MaintenanceActive`、`ShiftHandover`、`InterruptedRepair`，改变工具状态、椅子与文件位置、货箱数量和容器初始开启程度。每套 6–7 个可搜寻容器；预览保存第三套，7 个容器。房间建筑及主要家具位置固定。

正式地图 `/Game/GameMaps/L_Dungeon_Randomized`；继续精修的整条线路地图 `/Game/GameMaps/Design/L_FreightTransit_Theme_Subject`。

```text
open /Game/GameMaps/Design/L_FreightTransit_Theme_Subject
```

返回：`open /Game/GameMaps/DayNight_Lighting`。

## 制作源与执行入口

- `Scripts/geometry.py`：本批精确几何、UV、顶点色、UCX 与导出工具。
- `Scripts/author_workshop.py`：21 个新网格，可编辑源 `Authored/StationWorkshop_Source.blend`；`--only=AttachmentMounts` 只导出安装支架，保留其余 FBX。
- `Scripts/prepare_layout.py`：固定位置、三套布置、原比例字形与印刷图集。
- `Scripts/extend_catalog.py`：目录扩展及预览布置。
- `Scripts/materials.py`、`import_assets.py`：七个材质、印刷纹理、实际网格导入/Nanite 构建/保存。
- `Scripts/build_native.ps1`：必要 Editor/Game 构建，不启动可交互编辑器。
- `Scripts/install_background.ps1`、`install_scenes.py`：批次互斥，后台保存生产目录与现有车站样板；保留运行中的编辑器。

状态分别记录在 `Receipts/native-build.json`、`assets.json`、`install.json`；源码、编译、资产保存和地图保存分别交付，不以脚本存在代替导入。私有 Blend/FBX、字体、原始资产和 UE 包继续保留本机。

2026-10-03 后续精修采用 [RefineV2](RefineV2/README.md)：修正整个线路印刷面方向，细化桌面电子设备与连线，增加货架散放变化，门默认关闭并接入 E/冲刺撞门，三块独立可击碎观察窗，桥面增加地牢宝箱。正式目录与现有线路样板一并更新。原作者、布局和导入入口继续复用；V2 保存后自动使用新的制作规则及资产。

未运行游戏、PIE、测试、截图或渲染；由用户试玩。V2 的文字方向排查属于本次用户明确要求的检查。详细记录见 [工作间制作](../../Docs/Gameplay/dungeon-station-workshop-20261003.md) 和 [V2 精修记录](../../Docs/Gameplay/dungeon-station-workshop-refine-v2-20261003.md)。

后续三处局部修正采用 [RefineV3](RefineV3/README.md)：平整混凝土顶棚、托盘旁棘轮扳手错位分离、下层恢复楼梯栏杆逐级落地并接齐平台扶手。独立新资产保留 V2；正式目录和原测试地图同步。V3 布局规则在重新生成作者配置时继续保留。
