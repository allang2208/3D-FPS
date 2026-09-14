# 胖子僵尸只攻击、不移动 · 2026-09-14

用户在 F6 面板生成胖子僵尸后发现它无法移动，靠近后才会攻击。本次针对已有运行日志和实际使用的 `DayNight_Lighting` 场景排查并修复导航，没有启动游戏复测。

## 原因

`MONSTER_BT_READY FatZombie_0` 表明行为树已运行；随后反复出现 `MONSTER_NAV_FAILED FatZombie_0`，直到玩家走近才出现近战命中。保存的地图包含可碰撞地面与测试障碍，但没有 `NavMeshBoundsVolume` 或 `RecastNavMesh`。因此物理落点有效，AI 却无法创建移动路径。攻击判断不依赖导航，仍然能够执行。

胖子胶囊半径 44 cm、高度 172 cm，使用现有配置中能容纳它的 HandBrain 导航数据（62 / 204 cm）；Nurse 的 34 cm 半径不足。未改全局 SupportedAgents 或胖子的移动、攻击与动画时序。

## 修改

- 给 `Content/GameMaps/DayNight_Lighting.umap` 增加实体笔刷导航区域并构建现有三个 Agent 的导航数据。区域中心为 `(1000,1000,300)` cm，半尺寸为 `(10000,10000,600)` cm，覆盖出生点、台阶/障碍与周围 200 × 200 米开发区域。5 公里天气背景地板未全部生成导航。
- `DevelopmentSpawnComponent` 根据怪物最终胶囊选择合适导航数据，落点必须同时满足物理放置和对应导航覆盖。缺少导航或前方无合适导航位置时在面板提示原因，不再生成无法寻路的实例。
- 修改通过当前已打开的编辑器保存，保留场景其它内容。可重复执行的地图制作脚本为 `Tools/FatZombie/build_daynight_navigation.py`，需在编辑器打开该地图并停止游戏后运行。

## 排查数据与构建

- 原日志相关段：`Saved/FatZombieNavigation/reported_runtime_before.log`；原地图数据：`saved_map_before.json`。
- 地图保存前备份：`Saved/FatZombieNavigation/before_20260914_090533/DayNight_Lighting.umap`。
- 地图修复记录：`Saved/FatZombieNavigation/repair.json`，包含保存前后散列及导航配置。
- 对已有日志中 `(1629.017,2017.575,88.150)` 到 `(1292.926,1647.383,98.150)` 的单条失败路径重新查询，得到有效、非局部路径，长度约 499.8 cm。这是针对原故障的导航数据排查，不代表游戏移动、动画或实战效果通过验收。
- `FPSGAMEEditor Win64 Development` 与 `FPSGAME Win64 Development` 原生构建成功。日志为 `Saved/Logs/FatZombie-navigation-Editor-build.log`、`FatZombie-navigation-Game-build.log`。

离线 commandlet 第一次制作遇到编辑器异步导航锁及已打开地图的文件占用，未能保存；随后改用当前编辑器完成导航构建和保存。没有更改其它插件设置或强制关闭编辑器。

## 用户复测

当前编辑器中的地图已经更新。进入游戏，通过 F6 清除旧实例并重新生成胖子僵尸，观察其追击以及接近后的攻击。未进行游戏实测、截图或其它怪物回归，由用户测试。
