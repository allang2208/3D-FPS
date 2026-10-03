# 车站线路精修样板

用户指定生成车站整条路线，用于继续优化。已后台保存到：

`/Game/GameMaps/Design/L_FreightTransit_Theme_Subject`。

在游戏控制台进入：

```text
open /Game/GameMaps/Design/L_FreightTransit_Theme_Subject
```

返回：

```text
open /Game/GameMaps/DayNight_Lighting
```

## 构成

`FreightTransfer_WarehouseLink → AbandonedCargoWarehouse → AbandonedTransitStation`。

沿用当前生产目录中的三个作者模块，使用 80 cm 短接段和 400 cm 仓库至车站通道连接，
保持门口和楼面位置。货运升降闸门放在开启位置，线路两端封闭，玩家从货运区开始。
样板不布置刷怪导演，方便用户连续查看与精修场景。

初次保存内容为可编辑的关卡 Actor：126 个网格 Actor、27 盏作者灯光，
包含一扇保持抬起的货运闸门。原网格、材质、布景、碰撞及灯光参数沿用生产源。
没有重新接入旧独立车站样板、祭坛菜单或临时打包入口。

## 来源与产物

- 作者描述：`SourceAssets/DungeonStationLine20261002/Config/line.json`。
- 实际后台保存回执：`SourceAssets/DungeonStationLine20261002/Receipts/install.json`，`stage=map_saved`。
- 生成入口：`SourceAssets/DungeonStaffLiving20261002/Production20261002/Scripts/create_station_line_subject.py`。
- 单独后台保存入口：同目录 `install_background.ps1 -StationLineOnly`。
- 生产模块来源：`SourceAssets/DungeonRoutes20260922/Config/catalog.json`。

关卡已经实际保存，不是仅生成脚本。未启动可交互编辑器、游戏、PIE、截图、渲染或测试。
后续由用户试玩并继续提出场景优化要求。

## 2026-10-03 仓库容器

已在同一地图的仓库区域后台保存 9 个可搜寻容器：4 个地面货箱、3 个货架周转箱及 1 组工具柜（柜门、抽屉分别搜寻）。选中点位的旧货物 Actor 已替换，其余线路保留。容器有独立箱盖、柜门或抽屉，使用既有交互面板及聚焦轮廓。

正式随机地牢每间仓库按种子选择 9–13 个容器。制作源及实际地图保存回执在 `SourceAssets/WarehouseContainers20261002`，详见 [仓库容器](dungeon-warehouse-containers-20261003.md)。未运行游戏或测试，由用户试玩。

## 2026-10-03 车站工作间

同一地图的车站站台内新增 10 × 7 m 维修兼调度工作间，带人员门、宽维修门、观察窗、L 形维修台、调度桌及门外维修作业区。当前保存“检修中断”布置，增加 43 个静态 Actor、7 个可搜寻容器和 3 盏局部灯；仓库已有容器及其余线路保留。

正式车站按局种子选择三种室内布置之一，包含 6–7 个容器。详见 [车站工作间](dungeon-station-workshop-20261003.md)，实际资产和地图保存回执在 `SourceAssets/StationWorkshop20261003/Receipts`。没有运行游戏、测试或渲染，由用户继续试玩。
