# 手脑在 Boss 房的追击与二层寻路修正

用户反馈：玩家登上二层后手脑无法有效追击/攻击。此次只读取相关日志、源码、已导入网格参数，修改代码并尝试后台构建；未启动编辑器界面、PIE 或游戏。

## 已找到的原因

- `Saved/Logs/FPSGAME.log` 记录 2026-09-23 06:18:55 UTC 的 `MONSTER_BT_READY`、`HANDBRAIN_READY`、`DUNGEON_BOSS_STARTED`；Boss 已生成、行为树已启动。06:19:07 起连续出现 `MONSTER_NAV_FAILED`，目标高度包含二层 552 cm、中间平台 372 cm、地面 192 cm 的玩家身体中心坐标。不是“Boss 没生成”。旧日志未区分投射失败与完整路径失败，因此不能仅凭它认定每次失败的几何原因。
- `MonsterBTNodes.cpp` 原来仅用二维距离判断追到玩家。玩家在上方时，Boss 会在下层提前停步。
- 原 `MoveToLocation` 把身体中心交给默认导航投射。玩家可贴近栏杆，而手脑半径 62 cm 的导航边界更靠内，默认查询范围可能无法找到对应的大体型可走面。
- 手脑的起手只检查水平距离，但实际砸地/嚎叫伤害有 170 cm 的高度门槛。会对不在可命中高度的玩家空放，期间阻断追击。
- 共用 AI 的 12 秒记忆适用于普通怪物；手脑速度为 100 cm/s，在大房间绕行楼梯和掩体期间，失去视线可能先让记忆到期。
- 已导入的楼梯、钢格平台使用完整复杂三角形碰撞，未开 Nanite，导航数据存在。细钢格直接同时承担胶囊接地和导航光栅化，缺少简化的连续支撑面；本次补齐。未在游戏中重新生成并测量导航连通性，不把该几何风险写成已实测确认的唯一根因。

## 修改

1. 共用 AI 的目标、伤害记忆、出生点导航坐标统一为脚下位置；返回判定也考虑高度。
2. 停步需要脚下高差不超过 50 cm。跨层追击使用 40 cm 接近距离，继续让真实 NavMesh 规划楼梯路线。
3. 按自身 NavAgent 查找导航数据，再显式投射目标：水平范围 `max(100, 2*AgentRadius+30)`，手脑为 154 cm；垂直范围 100 cm，防止二层目标被投到下层。仍要求完整路径，不启用穿墙直线移动、传送或部分路径冒充到达。
4. 手脑砸地起手使用预期落点的高度和遮挡判定，嚎叫起手使用现有伤害的高度和遮挡判定；伤害数值、距离、冷却、动作时钟保持原值。
5. 只有 `DungeonBossEncounter` 指定的入场玩家保持战斗目标，遮挡时仍追踪位置；攻击继续要求视线。现有离场/死亡/完成逻辑负责结束遭遇并销毁 Boss，普通怪物保留原感知记忆。
6. Boss 遭遇 Actor 增加 55 个原生盒体：5 块二层平台、48 级踏步、2 块中间平台。位置、厚度由现有 `Config/rooms.json` 生成到 `DungeonBossWalkSurfaces.inl`，与房间变换一起移动；仅覆盖原钢格的厚度和轮廓，不覆盖中央挑空，不取消栏杆、设备的阻挡。盒体为隐藏 QueryOnly，阻挡 Pawn 和 WorldStatic 地面查询，Visibility 仍使用可见网格。生成阶段自动参加原有动态导航构建，无需重新导入网格或重存关卡。
7. 寻路失败日志现在区分 `reason=goal_projection` 与 `reason=path`，附脚下目标、起点及导航数据，方便下一次用户实测定位。

## 文件与制作入口

- `Source/FPSGAME/Monsters/MonsterAIController.{h,cpp}`、`MonsterBTNodes.cpp`
- `Source/FPSGAME/Monsters/HandBrainMonster.{h,cpp}`、`MonsterCombatComponent.cpp`
- `Source/FPSGAME/Dungeons/DungeonBossEncounter.cpp`、`DungeonBossWalkSurfaces.inl`
- `SourceAssets/DungeonBossHall20260922/Scripts/build_walk_surfaces.py`：根据房间源配置生成盒体；`build_terminal.py` 已接入该步骤。楼梯/平台尺寸变更后重新执行生成并编译。
- `SourceAssets/DungeonBossHall20260922/Scripts/inspect_navigation.py`：读取已导入资源的导航输入；没有启动游戏或保存资源。
- 读取结果：`SourceAssets/DungeonBossHall20260922/Receipts/navigation-inputs-20260923.json`。

## 构建和生效状态

常规后台构建日志：`Saved/BuildEditor/build-20260923-152652.log`。

本轮 AI 和 Boss 房修改对应的编译单元均已完成编译。整体构建在其他正在修改的建筑文件中失败：

- `VoxelBuildComponent.cpp`：`FName::GetPlainNameHash` 不存在。
- `VoxelBuildWorld.cpp`：对 `TMap::Add` 返回的 bool 解引用。
- `VoxelBuildWorld.cpp`：`TSet::RemoveAll` 不存在。

保留这些并行修改，未改动建筑模块，未替换或回退旧 DLL。后续需在建筑构建错误解决后执行 `Tools/Build/Build-Editor.ps1` 完成链接；本次源码不能被视为已在用户游戏中生效。未进行运行测试。

用户后续可重点观察：从地面绕掩体到达两侧楼梯、登上两边平台及后侧平台、玩家贴栏杆时追击、上下层投影重合时不提前停步，以及离场/死亡后按原规则重置。
