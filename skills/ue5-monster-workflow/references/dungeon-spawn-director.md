# 随机地牢运行时刷怪：导演模式（2026-09-26 批次一沉淀）

适用：运行时随机装配地牢的战斗房刷怪、休眠管理、警报传播、清房登记与封门精英房。
实现文件：`Source/FPSGAME/Dungeons/DungeonRunSubsystem.*`、`DungeonSpawnDirector.*`、`DungeonRoomEncounter.*`、
`Source/FPSGAME/UI/ColdSteelDungeonLoot.*`、`SourceAssets/DungeonSpawn20260925/**`。
设计与冻结决策：`Docs/Gameplay/dungeon-spawn-randomness-playability-plan-20260925.md`；
实现与实证记录：`Docs/Gameplay/dungeon-spawn-batch1-implementation-20260926.md`。
状态：编译+headless 安装实证，**未做运行时测试**（用户全局规则）。

## 架构（目录驱动，四段式）

```
catalog.modules[].spawn（唯一数据源，覆盖批次注入实时 Actor）
  → UDungeonRunSubsystem（world subsystem：清单/目录解析、BFS 深度、图查询、档案集成、种子流工厂）
  → ADungeonSpawnDirector（定时器 Actor：编成、落点闸门、休眠/唤醒、警报、清房；bCanEverTick=false）
  → ADungeonRoomEncounter（封门精英房：Boss 遭遇的泛化兄弟，多怪、无奖励门）
```

`spawn` 段 schema（冻结）：`{source, theme, count:[min,max], anchor_roles:["encounter"], pool:[{id,class,weight}]}`。
`anchor_roles` 按**前缀**匹配锚点 role tag（`encounter_west`/`encounter_lower` 等变体自动命中）。
首批冻结池：Mutant3、NurseZombie、PoisonMaggot、Wolf、InfectedDog、FatZombie；
排除 ZombieDog（纯 BP 未验证）、HandBrain（Boss 身份）、Witch（规划决策）。

## 休眠配方（顺序严格，PoisonMaggotAudit.cpp:201 先例）

- 休眠：`SetDecisionEnabled(false)` → `SetActorTickEnabled(false)`
- 唤醒：`SetActorTickEnabled(true)` → `SetDecisionEnabled(true)`
- 不用 `StopLogic`（仓库无 `ResumeLogic` 先例）；死亡/交战中（`Combat->IsBusy()`）跳过休眠。
- 远房休眠判据：房间不在活动集（灯光调度同口径）且无警报且玩家距离远；本 run 内进过警报集的房间不再休眠。

## 落点闸门管线（任一环节失败→销毁重试，绝不降标）

1. 类解析 + CDO 校验：四家族基类（护士系/狼系/手脑/毒蛆）公开 `Combat` 字段判家族（CDO 的 OwnedComponents 不可靠）；BP 路径 `_C` 加载失败时回退去后缀再试。
2. nav 严格投影：按实例 `GetNavAgentPropertiesRef()`（或碰撞胶囊推导）经 `GetNavDataForProps` 选**正确 navdata**，`ProjectPointToNavigation` 容差 |ΔZ|≤55、2D≤150。
3. 地面 trace：向下 1500，命中法线 Z≥0.94（村庄 spawner 坡度口径）。
4. 胶囊 sweep：生成尺寸扫一次，DontSpawnIfColliding 兜底。
5. 玩家闸门：距玩家 ≥1500 且视线被遮挡才落点；无玩家视为通过。玩家阻挡**不消耗**槽位尝试次数。
6. `SpawnDeferred`：FinishSpawning **前**写槽位标签与实例 `Level`/`Rank`（绝不写 CDO；Level=0 表示保留类默认，LevelBonus 恒叠加）。
7. 事后校验：tick 启用、物理资产、控制器、行为树齐备，缺任一立即销毁。

重试模型：每槽 3 次、每房 10s 定时器（村庄 spawner 口径）、0.25s 全局巡检；
全局存活上限 cvar `fps.Dungeon.Spawn.GlobalCap`（默认 12），**到上限只延后，绝不销毁已生成的怪**。

## 警报、清房与持久化

- 警报：任一怪 `OnTakeAnyDamage` → 该房进警报集（本 run 不休眠）+ 共享 connector 的 1 跳邻房临时唤醒 12s（对齐 AI 记忆 MemorySeconds）。
- 清房：全槽 `Combat->IsDead()`（尸体销毁=弱引用失效同样判死）；清房后**本 run 不重生**；未清完的房玩家离开后导演会补满剩余槽位（设计行为）。
- 槽位标签：`DungeonEnemy.<RunId>.<node>.<slot>`，与 `DungeonLayout::RecordKill` 前缀解析逐字兼容（前缀=`DungeonEnemy.<RunId>.`，其后全部为槽位），5 条奖励路径按槽去重；未打标签的怪（村庄）恒放行。
- 档案：`FColdSteelProfile.DungeonRun`（FDungeonRunState）低频 CommitState（SyncRuntime→Snapshot→改→CommitState，冶炼先例）；RunId=`Seed-hextimestamp`，新 run 重置 DefeatedEnemies/Cleared/Explored；跨 run 提交以 RunId 匹配防污染。

## 独立种子流（可复现且不串流）

gameplay 流 = `seed ^ 域常量`（SpawnComposition/SpawnPlacement/EliteSelection/ChestLoot/Alarm，0x5D0E1A01..05），
每房再混节点：`GameplayStream(域 ^ uint32(NodeId)*0x9E3779B9)`。绝不触碰布局/dressing/水渍既有流。

## 封门精英房（Boss 遭遇泛化，不改 Boss 类）

玩家越过门内侧触发线 → 落门板（/Engine Cube + 结构钢材质，`SetCanEverAffectNavigation(false)`，几何包含判定不产 overlap）→ 房内落点生成精英组（唤醒态，LevelBonus+2，Rank=Elite）→ 全员死亡开门并登记清房。
**防卡死**：门口估算无效则不封门只生成；玩家死亡/离房放行开门（怪保留），回触发线重封；落点全放弃也会开门。
门板绝不参与导航重建；精英组同样走导演静态闸门（共用 `SpawnMonsterAtGround`）。

## 生成器挂接三段式（镜像 Boss 先例）

1. PrepareAssembly `bRuntime` 块装配 job：`SpawnActor`（模板重载必须显式传 `StaticClass()`，两参 Transform 重载不存在——C2672 教训）→ `OwnGenerated(-1)` → `Configure(this)`（只缓存指针）。job 队列天然单次执行；编辑器预览路径零怪物。
2. FinishAssembly Manifest 赋值后：`bRuntime` 门控 `BindCompletedDungeon`（必须先于武装）。
3. 导航就绪收尾批（Boss ActivateEncounter 循环旁）：`Activate()`（开局规划+落怪+巡检启动）。
**OwnGenerated 只能在 BuildState 存活期调用**（收尾批 `BuildState.Reset()` 之后解引用即崩）。

## 目录覆盖批次纪律（三件套，纯磁盘编辑会被覆盖）

覆盖脚本（纯函数 extend+deepcopy+双向校验+source 标记幂等整段替换）+ receipt 门控 runpy 钩子（挂在 room_variants 之后，变体房 anchors 重建完再注入）+ 安装器（读**实时 Actor** 的 module_catalog_json 而非磁盘；备份首装原状；module_assets 并集去重；native `/Script/` 与 `_C` 类统一 `load_class`，其余 `load_asset`，失败必须保存前显式报错；只保存名字含目标地图名的脏 OFPA 包；镜像回磁盘 catalog；写 `stage=map_saved` 回执）。
headless 安装：`UnrealEditor-Cmd <uproject> -run=pythonscript -script=<install.py> -unattended -nopause -nosplash -stdout`。

## 已知风险（首批遗留）

- nav agent best-fit 隐式契约：SupportedAgents（DefaultEngine.ini）容差 5cm 内自动匹配；FatZombie 借 HandBrain 网格（62 净空过 3m 门洞）、Wolf 借 Nurse 网格——增删改 SupportedAgents 会静默改变归属；显式化列为加固候选。
- 休眠期感知开销未实测（存活上限封顶兜底）。
- 宝箱战利品为直入背包（AddItem：弹药走弹药袋、金币入 Items、背包满则提示+日志不落地）；世界掉落 Place=2 在重生成布局下会悬空/埋地，金币溢出掉落的新 run 清理列为候选。
