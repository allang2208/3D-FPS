# 医院线路测试地图

地图包：`/Game/GameMaps/Design/L_Hospital_Theme_Subject`

进入命令：

```text
open /Game/GameMaps/Design/L_Hospital_Theme_Subject
```

返回主场景：

```text
open /Game/GameMaps/DayNight_Lighting
```

从正式地牢 `/Game/GameMaps/L_Dungeon_Randomized` 的已保存 `module_catalog_json` 读取医院线路，
按「排水检修区 → 废弃隔离病区 → 解剖教学厅」连续布置，中间复用正式连接走廊。
地图使用正常 FPS GameMode 和排水区入口 PlayerStart；共用正式模型、材质、灯光与碰撞资产。
保留统一翻越栏杆标记、排水积液的原生组件、隔离区玻璃门窗的击碎/开门交互，以及解剖厅的分区曝光。
分区曝光使用本次保存的 `/Game/Dungeons/HospitalLine20261003/Blueprints/BP_HospitalLineExposure`，
各实例分别保存原作者描述中的范围与曝光参数。

病床、医疗推车、输液架和血迹使用既有原生布置组件，在用户进入地图时生成一次。
布局种子固定为 `20261003`，血迹种子为 `20261004`，便于重复进入时对照位置。
排水区采用 `pump_service / maintenance` 作者场景组合。
地图供场景与交互调整，暂未配置怪物生成导演和清房战斗闸门。

`Config/production-catalog-snapshot.json` 保存本次使用的正式目录快照，
`Config/line.json` 保存各段位置、种子与来源散列。
`Receipts/install.json` 中 `stage: map_saved` 表示地图实际已保存；脚本本身不代表完成落盘。

作者入口：`Scripts/create_subject.py`；已有编辑器用 `install_existing_editor.py` 经工程 MCP 批次互斥接入，
编辑器关闭时用 `install_background.ps1` 在相同互斥下后台保存。
保留原场景和车站测试图。未运行 PIE、测试、截图或渲染，由用户试玩。
