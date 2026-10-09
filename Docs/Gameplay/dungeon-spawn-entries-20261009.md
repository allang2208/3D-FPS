# 房间出怪设施 — 2026-10-09

## 布置与接入

27 个房间模板、87 个设施：33 处双扇检修门、28 处井盖、26 处通风口。小房间 2 个，普通房间 3 个，大开间 4 个；按照真实几何挑选位置，狭窄房间不硬塞。连接道路、坡道和封端模块不额外设置。

正式目标为 `/Game/GameMaps/L_Dungeon_Randomized` 的生成目录。设施随每个房间的平移和旋转生成，不改变房间 Cells、边界或连接口。重新生成地牢后生效。

用户随后要求先撤下怪物刷新扩展。现仅保留关闭的静态设施模型和布局，后续重新设计刷怪规则；既有普通房间和 Boss 刷怪系统保留。

| 房间 | 检修门 | 井盖 | 通风口 | 合计 |
|---|---:|---:|---:|---:|
| 配给室 (`Distribution`) | 1 | 0 | 1 | 2 |
| 排水室 (`Drainage`) | 1 | 1 | 1 | 3 |
| 破洞入口通道 (`ShoredBreach`) | 1 | 1 | 1 | 3 |
| 宝藏室 (`Treasure`) | 1 | 0 | 1 | 2 |
| 通风回廊 (`VentilationLoop`) | 1 | 1 | 1 | 3 |
| 货运转运室 (`FreightTransfer`) | 1 | 1 | 1 | 3 |
| Boss 前汇聚室 (`BossConfluence`) | 0 | 1 | 1 | 2 |
| Boss 泵房 (`BossPumpHall`) | 2 | 1 | 1 | 4 |
| 车站 (`AbandonedTransitStation`) | 2 | 1 | 1 | 4 |
| 隔离病房 (`AbandonedIsolationWard`) | 2 | 1 | 1 | 4 |
| 焚化间 (`AbandonedIncineratorHall`) | 1 | 1 | 1 | 3 |
| 资料档案室 (`AbandonedDataArchive`) | 1 | 1 | 1 | 3 |
| 解剖室 (`AbandonedAnatomyTheatre`) | 0 | 2 | 1 | 3 |
| 烟气处理站 (`AbandonedFlueGasStation`) | 1 | 1 | 1 | 3 |
| 货物仓库 (`AbandonedCargoWarehouse`) | 2 | 1 | 1 | 4 |
| 仓库转运室 (`FreightTransfer_WarehouseLink`) | 1 | 1 | 1 | 3 |
| 员工宿舍 (`StaffDormitory`) | 1 | 1 | 1 | 3 |
| 更衣淋浴间 (`StaffChangingShowers`) | 1 | 1 | 1 | 3 |
| 员工休息室 (`StaffRecreation`) | 2 | 1 | 1 | 4 |
| 育苗室 (`EcoNursery`) | 1 | 1 | 1 | 3 |
| 水培室 (`EcoHydroponics`) | 2 | 1 | 1 | 4 |
| 生态花园 (`EcoBiosphere`) | 2 | 1 | 1 | 4 |
| 配电室 (`SwitchgearGallery`) | 1 | 1 | 1 | 3 |
| 发电机房 (`GeneratorHall`) | 1 | 1 | 0 | 2 |
| 蓄能总控室 (`AccumulatorControl`) | 0 | 3 | 1 | 4 |
| 接待大厅 (`FacilityReceptionHall`) | 2 | 1 | 1 | 4 |
| 分流大厅 (`FacilityTransit`) | 2 | 1 | 1 | 4 |

## 2026-10-09 按用户要求撤下刷怪扩展

- 删除本次 `ADungeonSpawnEntry` 原生类与组装入口。
- 撤下房间遭遇对设施的扫描、兼容筛选、排队、爬出/落下、AI 接管及中断重试分支；恢复原有房间刷怪路径，不改 Boss 系统。
- 设施转为 `parts` 中的普通静态模型，保持关闭，不绑定怪物、动画或波次。
- 井盖下恢复原始完整地板；检修门使用静态网格碰撞。布局、模型制作源及为避免家具遮挡设置的净空保留。
- 从正式生成目录和依赖数组移除设施动作、切孔地板及原生运行对象的引用；旧动作和切孔副本不再接入。
- 制作脚本仅维护静态布景，不会在重建时恢复已撤下的逻辑。
- 退役源码和修改前备份：`trash/dungeon-emergence-withdrawn-20261009/`，散列见该目录 `manifest.json`。

本次撤下不运行游戏或追加检查测试。用户关闭 UE 后，`FPSGAMEEditor Win64 Development` 原生构建成功，DLL 已落盘；记录见 `withdraw-build-receipt.json`。正式地图和静态设施资产已通过现有编辑器桥保存，收据为 `install-receipt.json`（`mode=closed_static_fixtures`）。
