# 联机世界功能修复 · 2026-10-13

范围：双人监听服务器；延续 `basic-feature-repairs-20261013.md` 中已完成的库存与战斗接入。本轮补充采集、体素建造、制作工作站、神龛、组队换图。未启动编辑器、PIE、游戏或运行验收。

| 功能 | 源码接入 |
| --- | --- |
| 采集 | 客机工具在本地拥有角色后初始化；采集/回填发往拥有者 PlayerState，服务器按工具、距离和资源身份结算。资源生命、树桩与生长归共享世界；产物进共享掉落，丘陵不同世界 ID 分开保存。 |
| 建造 | 客机读取服务器建筑，保留本地预览；放置、拆除、撤销由服务器处理材料与世界改变。撤销按操作者维护；构件和逻辑 Actor 同步身份、外观与位置。 |
| 工作站 | 普通制作、锻造、枪械拼装、木工、冶炼/添柴/升级/取锭接入服务端。客机有独立制作会话，木工输入在服务器重放；材料与成品沿用带版本号的库存回执。 |
| 神龛 | 按玩家本次 RunId 的领取记录判断，回血与记录一起提交；属性和 Buff 图标按对应玩家查询。 |
| 组队换图 | 祭坛和传送门通过服务器换图；换图前等待队员档案上行和库存回执，保存客机档案；PlayerState 复制服务端档案身份供无缝换图续接。地牢共享种子和 RunId，客机生成本地场景，服务端管理战斗、进度和闸门。 |

世界快照沿用压缩和限速分块；库存回执优先，建筑只在版本变化后重传。实时工作站状态不携带完整物品或材料表。接收端等待对应建筑 Actor / 地牢准备完成后再应用世界状态。丘陵服务器的地形碰撞加载范围覆盖全部玩家。

相关入口：`Source/FPSGAME/Multiplayer/ColdSteelHarvestAuthority.cpp`、`ColdSteelStationNetwork.cpp`、`ColdSteelTeamTravel.cpp`、`ColdSteelWorldNetwork.cpp`，以及 `Building/VoxelBuildNetwork.cpp`、`Dungeons/DungeonRunNetwork.cpp`。

后台构建结果：`Saved/MultiplayerWorldRepairs20261013/game-build-r3.log` 为 `Result: Succeeded`（25 个动作，含 `FPSGAME.exe` 链接；110.49 秒）。之前 `game-build-r2.log` 因并行双持手枪源码/头文件更新时序未通过，r3 已完成对应重建。

用户保存并关闭 UE 后，Editor 基础构建已完成：`Saved/MultiplayerWorldRepairs20261013/editor-build-final.log` 为 `Result: Succeeded`（186 个动作；135.79 秒），已链接 `UnrealEditor-FPSGAME.dll` 和 `UnrealEditor-ColdSteelNet.dll`。本轮 Game / Editor 构建产物均已落盘；未自动重开编辑器。

没有运行 PIE、游戏或自动测试。编译成功不代表五项功能已通过双人运行验收。

后续战斗、奖励、状态效果、商店与环境同步修复见 [联机战斗与世界状态修复](combat-and-world-sync-repairs-20261013.md)。
