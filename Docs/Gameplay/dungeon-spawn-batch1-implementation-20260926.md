# 随机地牢刷怪批次一：实现记录（2026-09-26）

状态：实施中。设计依据与用户拍板见 [扩展计划](dungeon-spawn-randomness-playability-plan-20260925.md)（含 2026-09-26 设计冻结节）。

## 交付范围（Phase A+B+C 合并批次）

| 模块 | 文件 | 归属 | 状态 |
|---|---|---|---|
| Run 服务 | `Source/FPSGAME/Dungeons/DungeonRunSubsystem.h/.cpp`（新） | 主会话 | 已落盘；另一会话构建轮已验证 UHT+MSVC+链接（1:01/1:02） |
| 刷怪导演 | `Source/FPSGAME/Dungeons/DungeonSpawnDirector.h/.cpp`（新，136+799 行） | 子代理 W2 | 已交付，主会话逐行审查通过（全部外部符号核实：EMonsterRank、四家族 Combat/Level/Rank 公开、AI 控制器 API、材质资产路径磁盘实证） |
| 封门精英房 | `Source/FPSGAME/Dungeons/DungeonRoomEncounter.h/.cpp`（新，95+323 行） | 子代理 W2 | 已交付，审查通过；含防卡死设计（玩家死亡/离房放行开门、回线重封） |
| 生成器挂接 | `AuthoredDungeonGenerator.cpp`（4 处精确编辑：include、SpawnDirector 装配 job、Bind、Activate 循环） | 主会话 | 已实施（job 期 Configure + 收尾批 Activate 两段式镜像 Boss 先例；OwnGenerated 只能在 BuildState 存活期调用，故 spawn 走装配 job 而非收尾批） |
| 刷怪配置批次 | `SourceAssets/DungeonSpawn20260925/**`（4 新文件） | 子代理 W1 | 已交付，审查通过，离线链验证通过（modules=9 assets=6） |
| RouteRepairs 钩子 | `DungeonRouteRepairs20260922/Scripts/extend_catalog.py`（:71-75）、`install.py`（:33-34） | 子代理 W1 | 已交付，审查通过 |
| native 类加载加固 | 两安装器 `load_class` 覆盖 `/Script/` 路径 | 主会话 | 已实施 |
| 宝箱战利品 | `Source/FPSGAME/UI/ColdSteelDungeonLoot.h/.cpp`（新）、`Content/ColdSteelData/dungeon_loot.json`（新） | 子代理 W3 | 已交付，逐行审查通过；两 TU 已在另一会话构建轮编译通过（1:14） |
| 宝箱挂接 | `ColdSteelWorldInteraction.cpp` :13 include、:163 调用（仅两处插入） | 子代理 W3 | 已交付，审查通过 |

## 关键实现事实（审查中核实）

- **RecordKill 兼容**：`DungeonLayout.cpp:6-17` 前缀＝`DungeonEnemy.<RunId>.`，槽位＝其后全部（含点），与子系统 `EnemySlotTag` 的 `<Node>.<Slot>` 完全兼容；未打标签/无 RunId 恒放行（村庄怪不受影响）。
- **FDungeonRunState 实况**（DungeonTypes.h:49-70）：`ActiveEncounters/Claimed/Events` 均为 TSet<FName>；`GlobalAliveCap` 默认 12 字段已存在（首批用 cvar，不动档案字段）。
- **AddItem 语义**（ColdSteelProfileRuntime.cpp:431）：弹药 id 先走 `GrantAmmo`（弹药袋，不占背包）；未知 id / 背包满 → false；金币是普通定义（category=gold，StackMax 2^53），走 Insert 合并。
- **战利品 id 全集核验**：22/22 存在于 `items.json`（注意：enchant_scroll 系/enhancement_stone/goldIngot/magic_dust/reforge_ticket 为顶层键、无内嵌 "id" 字段）；弹药 6 id 均在 `ammo_types.json`。
- **最终宝箱标签**：生成器 :698-702 打 `DungeonTreasureChest`+`FutureTreasureLoot`；最终箱另有 `DungeonFinalTreasure`+`DungeonReward.Locked`（上锁由 Boss 奖励流程解锁后才可开，OpenTreasureChest:119 拦截上锁箱）。
- **宝箱 finish lambda**：`CreateWeakLambda(Target,...)` 捕获 `[Target,WeakMesh,Duration]`，挂接一行调用无需改捕获。
- **catalog 钩子链**：spawn 钩子位于 room_variants 之后（变体房 anchors 重建完成后注入）；receipt 门控（`Receipts/install.json` 且 stage='map_saved'）未安装时全链静默跳过。
- **anchor roles 实况**：5 房精确 `encounter`；VentilationLoop 变体 `encounter_west/east`；FreightTransfer `encounter_lower/dock`——消费端一律前缀匹配（子系统 RoomAnchors 已按 StartsWith 实现）。
- **生成器挂接点**（已勘定，待实施）：① PrepareAssembly bRuntime 块（:843-860，HomePortal job 旁）加 `Dungeon.SpawnDirector` job（SpawnActor→OwnGenerated(-1)→Configure(this)，job 队列天然单次执行）；② FinishAssembly :1119-1120（Manifest 赋值+stain）后加 bRuntime 门控 BindCompletedDungeon；③ :1131 Boss ActivateEncounter 循环旁加导演 Activate()（该块在导航等待 :1110-1117 通过后单次执行）。

## 合并点流程（WORKFLOW §7）

1. W2 交付 → 主会话逐行审查 4 文件（UHT 风险点逐一核对）。
2. 主会话实施生成器 3 处挂接（唯一共享 C++ 编辑；此前不动该文件以免污染他会话构建轮）。
3. 查无在跑构建（cl/link/dotnet/UBT/编辑器进程、Saved/BuildEditor 队尾）→ 统一构建一次。
4. 构建成功后：编辑器关闭条件下 headless 跑 `DungeonSpawn20260925/Scripts/install.py`（注入实时 Actor + OFPA 保存 + 镜像磁盘 catalog + receipt）；编辑器若在运行则走 MCP 桥批次互斥。
5. 交付说明：未测试（用户全局规则）；实测清单见计划文档"首批验收清单"。

## 构建与安装记录

- 2026-09-26 09:37 第一次合并构建：**失败，仅 1 处错误**——生成器挂接的 `SpawnActor<T>(Transform,Params)` 重载不存在（C2672，正确形态需显式传 `StaticClass()`），5 秒即中止；UHT 对导演/精英房/子系统全部新头文件解析通过，其余 TU 无错误。已修复为 `SpawnActor<ADungeonSpawnDirector>(ADungeonSpawnDirector::StaticClass(),GetActorTransform(),Spawn)`（`build-20260926-093703.log`）。
- 2026-09-26 09:38 **合并构建成功**（pwsh-4，22 秒增量：仅重编修复的生成器 TU + 链接；首败轮已并行编完其余新 TU，链接成功即全符号解析实证）：`UnrealEditor-FPSGAME.dll` 09:38:57，13,986,816 字节。
- 2026-09-26 09:39 **headless 安装成功**（`UnrealEditor-Cmd -run=pythonscript install.py`，退出码 0，26 秒）：
  - 回执 `Receipts/install.json`：stage=`map_saved`，spawn_modules=9，spawn_assets=6，root_map_modified=**false**，tests_run=**false**；
  - 保存包：仅生成器 OFPA `…/L_Dungeon_Randomized/8/N2/KZ839Z5RGFD4Y0908097LH`（09:39:21，383,100 字节；二进制内含 `DungeonSpawn20260925`/`FatZombie`/`PoisonMaggot` 标记实证）；主 `.umap` 未动；
  - 磁盘镜像 `DungeonRoutes20260922/Config/catalog.json`：9 个模块带 `spawn.source=DungeonSpawn20260925`（独立 python 复核）。
- 完整链日志：`Saved/BuildEditor/merge-batch1-20260926-093836.log`；失败首建日志：`build-20260926-093703.log`。

## 交付声明

按用户全局规则：**未做任何运行时测试**（无 PIE、无自动进图、无实测截图）。编译、安装、二进制标记均为静态实证。实测清单见计划文档"首批验收清单"（进图怪物落点/休眠唤醒/警报传播/清房不重生/精英房封门开门/宝箱三档战利品/最终箱三倍/档案 DeduplicationTags 持久化）。

## 已知风险与后续候选

- FatZombie 借 HandBrain 网格（62 净空）：3m 门洞相容，房内窄处卡怪则从池 JSON 移除或补专用 agent（第 5 份 navmesh 代价）。
- Wolf/ZombieDog best-fit 隐式契约：SupportedAgents 增删改会静默改变狼系 navdata 归属；显式化（34/184/40+FromCapsule=false，InfectedDog 同款）列为加固候选，本批不动共享怪物文件。
- ZombieDog 未入池（纯 BP 未验证）；验证后 JSON 一行即可加入。
- 休眠期感知开销未实测（存活上限 12 封顶）。
- AwardKill 金币溢出 Place=2 世界掉落：新 run 重生成后旧坐标掉落物悬空/埋地——列为清理候选（本批未处理）。
- 战利品未发放（背包满）语义：提示+日志，不落地不重发。
