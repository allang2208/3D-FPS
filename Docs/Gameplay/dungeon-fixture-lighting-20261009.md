# 随机地牢其余场景灯具与光源配对修正（2026-10-09）

**后续纠正：** 本批检查覆盖保存配置与作者样板，未覆盖原生运行时创建时的根组件旋转叠加。正式目录中的 45 盏聚光灯（含接待大厅 6 盏）仍会被错误转成水平；现已修复生成器。参见 [灯光方向根因修复与真实组件检查](dungeon-light-direction-root-fix-20261009.md)，不能用本批配置检查代替运行时方向结论。

已检查正式随机地牢目录中接待大厅以外的 40 个模块：37 个含灯光、3 个无局部灯光。逐盏处理 306 条原始模块灯光配置及固定起始区 13 盏灯。正式目录和两个连接大厅样板已实际保存；未启动游戏、未生成新布局、未截图或渲染。

## 修正内容

- 以 UE 已导入网格的真实发光材质分区、网格放置变换为依据，导出 79 个候选网格并逐盏配对。顶灯发光点位于灯罩下表面外 1 cm；保留向下的聚光灯，将全向顶灯改为朝下的矩形灯。面光源尺寸依据灯罩尺寸设置。
- 点光源改矩形光时流明乘 0.25，按两类光源不同的配光换算保留原本向下的中心照度；保留颜色、有效半径、阴影策略、淡出距离、故障熄灭与闪烁材质。
- 入口两盏椭圆壁灯按倾斜墙面的发光法线朝走廊照射，矩形发光区内接于灯罩投影；车站工作台灯按灯泡和灯罩出口的倾角照射桌面。
- 三种错层坡道的转弯平台原有光源没有灯具。各复用一件已有工业顶灯，挂杆顶部与平台天花板对齐；保留原有三盏光源数量。
- 过渡大厅三个主题入口的通道灯原来位于两盏灯具中间。各分为两盏对齐灯罩的矩形灯，每盏分配原光输出的一半。逐项比对了 3 个入口 × 6 个主题的 18 组灯具布局。
- 移除生态育苗室与水培室中共四盏没有实体灯具的悬空全向补光；其余生态灯按实际灯罩位置校准。
- 固定起始区的裸露神龛灯泡保留全向发光，光源半径约束在玻璃内；工作台原有聚光灯的位置、方向和亮度正确，予以保留。
- 两个连接大厅样板还包含接待大厅副本，连同副本中的 23 盏灯一并同步。正式接待大厅模块保持上一批已保存的修正。

## 已保存

| 地图 | 本轮处理 |
|---|---|
| `/Game/GameMaps/L_Dungeon_Randomized` | 原 306 条其余模块灯光处理后为 305 条，固定区 13 盏；加上已修正接待大厅 23 条，正式目录共 328 条 |
| `/Game/GameMaps/Design/L_FacilityTransit_Subject` | 53 盏：过渡大厅 30 + 接待大厅副本 23 |
| `/Game/GameMaps/Design/L_FacilityTransit_Alternate_Subject` | 53 盏：另三主题的过渡大厅 30 + 接待大厅副本 23 |

## 分模块检查清单

| 模块 | 原配置数 | 保存后光源数 | 灯型 |
|---|---:|---:|---|
| Distribution | 3 | 3 | 2 rect / 1 spot |
| Drainage | 4 | 4 | 2 rect / 2 spot |
| ShoredBreach | 3 | 3 | 2 rect / 1 spot |
| Junction | 4 | 4 | 2 rect / 2 spot |
| RouteEnd | 1 | 1 | 1 rect |
| Transit | 1 | 1 | 1 spot |
| Treasure | 2 | 2 | 2 rect |
| VentilationLoop | 4 | 4 | 2 rect / 2 spot |
| FreightTransfer | 5 | 5 | 3 spot / 2 rect |
| BossConfluence | 4 | 4 | 2 rect / 2 spot |
| BossApproach | 1 | 1 | 1 rect |
| BossPumpHall | 15 | 15 | 6 rect / 9 spot |
| StairDrop1080 | 5 | 5 | 5 rect |
| ForkLeft | 4 | 4 | 2 rect / 2 spot |
| ForkRight | 4 | 4 | 2 rect / 2 spot |
| AbandonedTransitStation | 14 | 14 | 14 rect |
| AbandonedIsolationWard | 26 | 26 | 26 rect |
| AbandonedIncineratorHall | 19 | 19 | 19 rect |
| AbandonedDataArchive | 9 | 9 | 9 rect |
| AbandonedAnatomyTheatre | 9 | 9 | 9 rect |
| AbandonedFlueGasStation | 9 | 9 | 9 rect |
| AbandonedCargoWarehouse | 9 | 9 | 9 rect |
| FreightTransfer_WarehouseLink | 5 | 5 | 3 spot / 2 rect |
| RouteRamp540 | 3 | 3 | 3 rect |
| RouteRamp1080 | 3 | 3 | 3 rect |
| RouteRamp1620 | 3 | 3 | 3 rect |
| StaffDormitory | 11 | 11 | 11 rect |
| StaffChangingShowers | 9 | 9 | 9 rect |
| StaffRecreation | 11 | 11 | 11 rect |
| EcoNursery | 17 | 15 | 15 rect |
| EcoHydroponics | 18 | 16 | 16 rect |
| EcoBiosphere | 12 | 12 | 12 rect |
| SwitchgearGallery | 4 | 4 | 4 rect |
| GeneratorHall | 7 | 7 | 7 rect |
| AccumulatorControl | 16 | 16 | 16 rect |
| FacilityEntrancePassage | 5 | 5 | 5 rect |
| FacilityTransit | 27 | 30 | 9 spot / 21 rect |

无局部光源模块：Threshold、TreasureLink、RouteElbow。

## 保存后核对与重建

回读了正式目录的 305 条本轮模块光源、固定起始区 13 盏，以及两个样板的 106 盏。灯罩间距、朝向、灯型、光源长度、流明与保存后数据相符；对应包无未保存修改。银行目录的 120 套摆放数据保持不变，新的原生合同散列为 `b187bf930b0bf2d963bde23d7d9d323aea55ef26`。这是灯光数据与保存结果核对，不是游戏画面或性能验收。

逐盏记录见 `SourceAssets/DungeonFixtureLighting20261009/Receipts/per-light.csv` 和 `saved-audit.json`；原始网格、逐盏旧位置、修改前后配置分别保存在 `geometry.json`、`Config/bindings.json`、`Receipts/install.json`。

正式作者入口 `DungeonFacilityFlow20261007/extend_catalog.py` 最后重放本轮修订；固定起始区恢复配置及生成脚本同步修正；大厅样板的 `HallLighting20261007/profile.py` 同步重放。新增灯具复用已存在的工业灯资产，并进入模块硬引用及原有房间调度，不新增逐帧扫描。

本轮地图、外部 Actor 包和配置备份：`D:\FPS3D\FPSGAME\SourceAssets\DungeonFixtureLighting20261009\Backups\20261009-203735`。

运行体验交由用户测试；本轮未测试游戏、未做截图或渲染验收。
