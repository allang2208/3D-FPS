# 车站整条线路测试场景

已保存地图：`/Game/GameMaps/Design/L_FreightTransit_Theme_Subject`。

```text
open /Game/GameMaps/Design/L_FreightTransit_Theme_Subject
```

顺序为货运中转区 → 废弃货仓 → 废弃中转车站，闸门保持开启，便于继续精修。
返回命令：`open /Game/GameMaps/DayNight_Lighting`。

作者描述在 `Config/line.json`，真实保存回执在 `Receipts/install.json`。
生成脚本位于生活主题的 `Production20261002/Scripts/create_station_line_subject.py`。
详细制作记录见 [车站线路样板](../../Docs/Gameplay/dungeon-station-line-subject-20261002.md)。

2026-10-03：同一地图的仓库已保存 9 个可搜寻容器，包含木箱、周转箱、金属运输箱和工具柜。实际新增保存回执在兄弟目录 `WarehouseContainers20261002/Receipts/install.json`，详细制作源见 [仓库容器](../WarehouseContainers20261002/README.md)。正式随机地牢按种子选择 9–13 个。

未运行游戏、PIE、截图、渲染或测试，由用户自行试玩。

2026-10-03：车站区域新增 10 × 7 m 维修兼调度工作间、观察窗和门外维修推车区，样板保存“检修中断”布置及 7 个工作间容器。制作源与保存回执见 [StationWorkshop20261003](../StationWorkshop20261003/README.md)，仓库已有容器继续保留。

工作间 V2：文字方向修复覆盖线路印刷面和共用容器标签，货架采用散放变体，调度电脑设备细化并重走电线；入口门默认关闭，按 E 或沿用冲刺撞门打开；观察窗可独立击碎。车站上层桥面增加一只地牢宝箱，样板可打开并使用原战利品面板。详见 [V2](../StationWorkshop20261003/RefineV2/README.md)。
