# 停尸房：复用医院扫描血迹与随机生成器

按用户要求直接引用医院现有模板：`/Game/Dungeons/IsolationWard20260929/BloodScan/M_WardBlood_Quixel`，运行类为 `ADungeonBloodScatter`。未复制或重新制作血迹材质、纹理，也未改医院原有分布。素材来源和既有使用记录继续见 `SourceAssets/DungeonIsolationWard20260929/BloodScan20260929/README.md`。

## 地下室配置

大开间、整理清洗间、制冷设备间分别保存一个生成器，独立保留各自的数量目标：

| 区域 | 地面目标 | 墙面目标 |
| --- | ---: | ---: |
| 大开间 | 34 | 14 |
| 整理清洗间 | 8 | 4 |
| 制冷设备间 | 8 | 4 |
| 合计 | 50 | 22 |

扫描宽度范围 60–100 cm；地面沿用医院 2.5 倍缩放，即 1.5–2.5 m，墙面保持 0.6–1 m。保留原扫描长宽比，随机旋转、位置及现成材质变化；这是同一张扫描的随机复用，不是新素材池。

配置只保存接收区域，不烘焙固定血迹。每次进入关卡，生成器在 BeginPlay 取新种子并一次性放置；无 Tick、无定时器、无持续重绘。沿用现有按面积抽样、范围边界、射线命中、表面法线、接收标签及有限尝试机制；被阻挡或容不下的位置可以跳过，所以实际数量可能少于目标。

地下地板、墙体和瓷砖下墙登记独有标签 `Incinerator.MorgueBlood.Receiver`。墙面接收区避开门洞、转运双门、墙面标牌和冷藏柜占位；地面接收区不进入楼梯范围或柜体占位。两间房使用独立预算，避免大厅消耗全部随机数量。血迹仅为装饰，不改变碰撞和伤害。

## 制作与落盘

- 源目录：`SourceAssets/DungeonIncineratorHall20260929/MorgueBlood20260930/`。
- `Scripts/prepare.py`、`Config/blood.json`：地下接收区域、尺寸与数量。
- `Scripts/install_blood.py`：复用类和材质、登记接收对象、保存三个生成器。
- 地图：`/Game/GameMaps/Design/L_AbandonedIncineratorHall_Subject`。
- 菜单入口：废弃焚化处理厅 · 主体样板。

主重建配置与 B1 安装链已接入本批，后续重建地下布局会恢复对应生成器。三个生成器和接收标签均已后台保存到地图，commandlet 退出码 0；本批 `Receipts/install.json` 记录 `stage=morgue_hospital_blood_generators_saved`、`map_saved=true`。原地图副本保留在 `Backup/`。

本次未启动游戏、PIE、截图、渲染或测试。编辑器中只保存生成器，实际随机血迹在进入游戏时产生；由用户确认密度与显示效果。
