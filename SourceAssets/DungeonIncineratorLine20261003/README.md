# 焚化炉线路三房测试地图

地图：`/Game/GameMaps/Design/L_Incinerator_Theme_Subject`

进入：

```text
open /Game/GameMaps/Design/L_Incinerator_Theme_Subject
```

返回主场景：

```text
open /Game/GameMaps/DayNight_Lighting
```

从正式地图 `/Game/GameMaps/L_Dungeon_Randomized` 的已保存生成器目录读取「破损支护室 → 焚化处理厅 → 烟气净化站」，以正式 Transit 走廊连续连接实际门位。
共用现有模型、材质、碰撞和灯光，保留焚化厅上下层、停尸间、灰渣区及净化站检修平台。
栏杆沿用统一翻越标签；焚化厅的地面标线、原生血迹生成和上下层分区曝光随描述导出。
使用正常 FPS GameMode、有效 PlayerStart、两端封口；本地图供用户调整场景，暂未安排怪物生成和清房闸门。
保留医院、车站测试地图，默认启动地图与烹饪清单保持原样。
2026-10-03 容器接入阶段同步保存正式随机地牢的本主题容器配置，并将五类容器布置到本测试图。
破损支护室 4–5 个搜寻入口，焚化处理厅含 B1 停尸间 10–11 个，烟气净化站 8–9 个。
正式线路随机抽取贴墙候选位；测试图固定预览种子，便于用户继续调整。布置源及实际保存回执位于 `SourceAssets/IncineratorContainers20261003`。

`Scripts/create_subject.py` 为作者入口，现有编辑器使用 `install_existing_editor.py` 通过工程 MCP 批次互斥执行；编辑器关闭时使用同一互斥下的 `install_background.ps1` 后台保存。
`Config/source-modules.json` 保存本次使用的正式模块描述，`Config/line.json` 保存连接布局；`Receipts/install.json` 中 `stage: map_saved` 才表示实际保存完成。
未运行 PIE、游戏测试、截图或验收渲染；由用户试玩。
