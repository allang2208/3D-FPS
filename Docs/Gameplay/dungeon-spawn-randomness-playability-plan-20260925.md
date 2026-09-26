# 随机地牢：刷怪、随机性与可玩性扩展计划（2026-09-25）

状态：实施中（2026-09-26 起）。批次一实施记录与合并点流程见 [实现记录](dungeon-spawn-batch1-implementation-20260926.md)。

## 用户拍板（2026-09-25）

1. 第一批合并交付 Phase A+B+C：Run 服务、刷怪导演、封门精英房、宝箱掉落、警报传播。
2. 普通怪刷新策略：**清完不重生**（本 run 内房间清空即安全；重新进入地牢＝新布局全部重掷）。
3. 封门精英房纳入第一批；**Boss 支线随机化暂缓**（中路固定为 Boss 路线，不动 compact 路由搜索）。

## 设计冻结（2026-09-26，四份只读审计结论）

四份审计（catalog 链、loot/奖励通路、9 怪导航规格、AI 休眠/警报/leash/清房）全部完成，以下为冻结决定：

**首批怪池（6 种）**：Mutant3、NurseZombie、PoisonMaggot、Wolf、InfectedDog、FatZombie。
- 导航依据：Mutant3/InfectedDog 显式 34/184/40 精确匹配 Nurse agent；NurseZombie C++ 基线 34/184/40 精确匹配（BP 覆写待实测）；PoisonMaggot 专属 agent 70/140/40 精确匹配（窄通道覆盖待实测）；Wolf 34/120 无等价 agent → best-fit 确定性落 Nurse（隐式契约：Nurse 条目不可删改，显式化加固列为后续候选）；FatZombie 44/172 无 agent → best-fit 借 HandBrain 网格（62 净空；地牢门洞 300cm 相容，村庄实战佐证；卡怪则从池 JSON 移除或补专用 agent 44/172/40，代价第 5 份 navmesh）。
- **不入池**：ZombieDog（纯 BP，父类/参数未验证）、HandBrain（Boss 身份）、WitchRebuilt（既定拍板）。池为数据驱动，验证后加 ZombieDog 只是 JSON 一行。

**休眠/唤醒配方（全 9 怪一致适用）**：休眠＝`SetDecisionEnabled(false)` → `SetActorTickEnabled(false)`（先例 PoisonMaggotAudit.cpp:201）；唤醒＝逆序（先 tick 后决策，SetDecisionEnabled(true) 内部读 IsActorTickEnabled）。不用 StopLogic（仓内无 ResumeLogic 先例）、不用 UnPossess（代价大）。跳过 `Combat->IsBusy()` 与已死怪。订阅每怪 OnTakeAnyDamage：被打即醒＋房间入警报集（本 run 不再休眠）＋唤醒 1 跳相邻房（只唤醒不注入目标；受击者已被 ReceiveHit 自动 RememberDamage）。休眠中感知仍写记忆、唤醒瞬间索敌是设计行为。

**Leash**：Home=刷怪点（四家族 BeginPlay 自动缓存），零代码。护士家族接受组件兜底 24m；feral（Mutant3/InfectedDog）交战期越界追击为既有有意设计（MonsterAIController.cpp:108-111），接受溢出、脱战/记忆过期后自动回家。不使用 SetEncounterTarget（Boss 专用锁）。

**清房判定**：按房存活数组，全员 `Combat->IsDead()` 即判灭（即时，不等 15s 尸体 LifeSpan）；OnDestroyed 仅清数组条目；胖子 PusPool 为独立 Actor 不计数。清房后本 run 不重生（用户拍板 2）。

**刷怪执行模型**：全定时器（0.25s 巡检），无每帧 tick。落点＝encounter 锚点优先（SpawnPlacement 流打乱）＋房间 Volume 散点回退；闸门＝Boss 口径全套（CDO 资产、nav 投影 extent(150,150,100)、agent 尺寸适配、|ΔZ|≤55/2D≤150 防跨房、Deferred+DontSpawnIfColliding、生成后校验回滚）＋玩家距离 ≥1500cm 且无视线。失败＝10s 定时器重试，同槽 3 次后放弃并告警。全局存活上限 cvar `fps.Dungeon.Spawn.GlobalCap` 默认 12（超限延后生成，不杀怪）。

**生成器挂接（主会话持有，待导演 API 定稿后实施）**：① PrepareAssembly 的 bRuntime 块（HomePortal job 旁，:843-860）加一次性 `Dungeon.SpawnDirector` job：SpawnActor → OwnGenerated(-1) → Configure(this)；② FinishAssembly 完成块 :1119（Manifest 赋值）后加 bRuntime 门控 `UDungeonRunSubsystem::Get(World)->BindCompletedDungeon(this)`；③ :1131（Boss ActivateEncounter 循环）旁加导演 `Activate()`。编辑器预览路径零怪物（job 与绑定均 bRuntime 门控）。

**随机流域（DungeonRunSubsystem.h）**：SpawnComposition/SpawnPlacement/EliteSelection/ChestLoot/Alarm，`seed ^ 域常量`，每房再用 `域 ^ NodeId*0x9E3779B9` 去相关；绝不触碰布局/dressing/stain 流。精英房＝每支线（Route1/2/3）用 EliteSelection 流抽 1 间（排除 Boss 区/Approach/已清除，偏深层），count+1、Level+2、Rank=Elite，配 ADungeonRoomEncounter 封门（门口位置由 subsystem EstimateDoorway(房, EntryConnectorFor(房)) 估算；估算失败则不封门只刷精英组并告警）。

**存档**：复用 `FColdSteelProfile.DungeonRun`（RecordKill 已接入全部 5 条奖励通路）；Bind 时重置 DefeatedEnemies/Cleared/Explored 并写新 RunId（`Seed-时间戳hex`）；每怪打 `DungeonEnemy.<RunId>.<Node>.<Slot>` 标签做每槽去重；提交走 `SyncRuntime→Snapshot→改→CommitState`（RunId 不匹配时拒写防跨 run 污染）。宝箱战利品直发背包（AddItem），不做世界掉落（重生成后旧坐标掉落物会悬空/埋地）；AwardKill 金币溢出的 Place=2 世界掉落在新 run 生成时的清理列为已知风险项。

**执行方式（WORKFLOW §7，2026-09-26）**：主会话持有 DungeonRunSubsystem（已落盘）与生成器挂接；三路写入子代理按文件切分并行（W1 目录批次脚本、W2 导演+精英遭遇 4 新文件、W3 宝箱战利品 2 新文件+交互脚本一处精确编辑），子代理一律不构建；全部落盘并经主会话逐行审查后，合并点统一构建一次。

**遗留实测项（用户口径，默认不自动测试）**：BP 覆写核实（Nurse/PoisonMaggot/Wolf/InfectedDog 胶囊与导航参数）、FatZombie/PoisonMaggot 窄通道寻路、休眠期感知开销（存活上限 12 已封顶）、ZombieDog 入池前 BP 验证。

## 现状基线（本文依据）

- 生成器 `Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.*`（+7 个 .inl）：
  前段 3–5 房 → Junction → 三支线各 3–5 房；compact boss v2 地下终点
  （StairDrop1080 → BossConfluence → BossApproach → BossPumpHall）；
  宝箱侧室 10%/合格房；`CompleteSocketGraph` 强制门洞闭合与连通。
- 目录 `SourceAssets/DungeonRoutes20260922/Config/catalog.json`：20 模块，
  普通房 9 配置/5 家族（Distribution、Drainage×3、ShoredBreach、VentilationLoop×3、FreightTransfer）。
- 每间战斗房已布 `encounter` 锚点（TargetPoint role 标签），当前无消费者。
- 宝箱可开盖（`ColdSteelWorldInteraction::OpenTreasureChest`）但无掉落（`FutureTreasureLoot` 占位）。
- Boss 遭遇 `DungeonBossEncounter`：nav 严格投影、封门、死亡开门、奖励机械门+最终宝箱+返回门。
- 怪物侧可复用：9 种注册怪（`MonsterCoreStats` 六维/等级/品阶/击杀奖励）、
  `MonsterAIController`（遭遇锁、leash 回家、感知/最后位置调查）、
  村庄 spawner 模式（单实例+失败重试+计时）、等级差经验公式。
- 旧废案 `Source/FPSGAME/Dungeon/DungeonTypes.h`（FDungeonRunState）仅存档兼容，不作生产复用；
  其数值（GlobalAliveCap=12、房间 AliveCap=6）作为首批上限参考。

## 全局原则

- **独立种子流**：所有玩法随机（刷怪编成、loot、精英房选择）用 `seed ^ 域常量` 派生流，
  与布局流、dressing 流、水渍流互不干扰；同种子+同操作可复现整局。
- **性能有界**：全局存活上限+每房上限、远房休眠、生成摊帧；对齐房间灯光调度的房间集合判定。
- **装配纪律**：刷怪导演的怪物类路径进入生成器资产清单（`QueueAsset`/`ModuleAssets` 硬引用），
  打包不依赖磁盘 JSON 之外的软加载；catalog 改动链以 `extend_catalog.py` 收尾。
- **生命周期**：导演为生成器拥有（`OwnGenerated`），布局重生成/地图卸载时销毁自有怪物，
  沿 Boss 遭遇先例；仅 `NM_Standalone`/authority 生效。
- **导航**：只在 `DungeonAssembly.Ready` 且 nav 构建完成后武装；
  每种入池怪物先做规格盘点（胶囊/NavAgent/SupportedAgents/运行时 nav 数据相容），
  落点校验复用 `DungeonBossEncounter::SpawnBoss` 的口径（agent 匹配、Z 偏差≤55、2D≤150，失败延迟重试）。
- 存档（2026-09-25 loot 审计后修订）：**复用档案已有 `FColdSteelProfile.DungeonRun`
  （FDungeonRunState）的 RunId/Seed/DefeatedEnemies/Cleared/Explored/bCompleted 字段**，
  不新增存档结构；旧 Rooms/Connections/EnemySlots 字段仍不进生产。
  `DungeonLayout::RecordKill` 闸门已被全部 5 条击杀奖励路径调用（AwardKill+四法术模型）：
  刷怪导演给每只怪打 `DungeonEnemy.<RunId>.<节点号.槽位>` 标签即自动获得
  "同槽位击杀奖励只发一次"的持久防刷；新开局重置 DefeatedEnemies 并写入种子派生的新 RunId。
- 交付：后台构建/导入/保存完成即交付，不主动 PIE/测试（AGENTS.md 全局规则）。

## 第一批（A+B+C）

### A. UDungeonRunSubsystem（新文件 `Dungeons/DungeonRunSubsystem.h/.cpp`）

- UWorldSubsystem；监听生成器 `DungeonAssembly.Ready`，解析 `LayoutManifestJson`
  构建房间图：节点（id/module/route/floor/origin/yaw/volume/side_socket）、门洞邻接。
- Run 状态：种子、每房 `cleared`/`looted` 集合、击杀数、死亡数、耗时。
- 查询接口：房间世界变换与锚点（按 `DungeonModule.<i>.<id>` 标签与 role 标签检索 TargetPoint）、
  邻接集、路线深度（前段第 N 房 / 支线号+房内序号）、玩法随机流工厂。
- “玩家当前房间+邻接”判定：复用房间灯光调度器的 portal-BFS 模式
  （占用 cells 距离 + 门洞矩形候选，见 `AuthoredDungeonLighting.cpp::UpdateRoomLighting`）。

### B. ADungeonSpawnDirector（新文件 `Dungeons/DungeonSpawnDirector.h/.cpp`）

- 由生成器在 `FinishAssembly` 收尾批创建并武装（与 Boss `ActivateEncounter` 同批，nav ready 之后）。
- **编成规划**（武装时一次完成，消费玩法流）：
  - 每间普通房按房型主题从 spawn 表抽怪物池，数量与等级按路线深度取值；
  - 深度口径：`depth = 前段房序 或 (支线号, 房内序)`；等级加成建议基线
    `+1 级 / 每 4 深度`（首值，可调）；数量基线 2–4/房（首值，可调）。
- **落点**：优先 `encounter` 系 role 锚点，其次房间 cells 内 nav 投影；
  禁止在玩家视线内与 15 m 内落点（首值）；不满足则该槽位延迟重试（村庄 spawner 模式），
  重试有次数上限，超限放弃该槽位并记录。
- **上限与休眠**：全局存活上限 12、每房 6（首值，取旧废案口径；cvar
  `fps.Dungeon.Spawn.GlobalCap` / `fps.Dungeon.Spawn.RoomCap` 可调）；
  玩家不在“当前+邻接”房间集的怪物 `SetDecisionEnabled(false)` 并关动画/移动 tick，进入集合唤醒。
- **清房**：房内怪物全部死亡→run 状态标记 cleared，本 run 不重生；
  尸体沿用怪物自身生命周期（布娃娃/残留物/回收不另做）。
- **生成摊帧**：复用装配预算模式（每帧固定 ms 预算），避免进房瞬间批量 SpawnActor 尖峰。
- **清理**：EndPlay/重生成时销毁自有怪物（Boss 遭遇同款），跨布局零残留。

### B-数据. 刷怪表（catalog 扩展，2026-09-25 目录链审计后定稿）

接入必须走"overlay 脚本 + receipt 钩子 + 安装器"三件套（所有增量安装器读 live Actor
而非磁盘；纯改磁盘 catalog.json 会被任一安装器回写覆盖）：

1. 新批次 `SourceAssets/DungeonSpawn20260925/`，最小文件集：
   - `Config/spawn-groups.json`：每普通房的怪物池/数量/锚点角色（数据事实源）；
   - `Scripts/extend_catalog.py`：字段级 overlay（WallDamage/FinalReward 范本）——
     deepcopy、按 **catalog['room_ids']（现 9 个：5 基础+4 变体，勿硬编码 5 个基础 id）**
     整段替换 `m['spawn']={..., "source":"DungeonSpawn20260925"}`（幂等），
     附 `asset_paths()` 与 `__main__` candidate 输出；
   - `Scripts/install.py`：照抄 RoomVariants 骨架——读 live `module_catalog_json`+备份、
     runpy 自家 extend、module_assets **union**（`_C` 用 load_class）、
     只保存名字含 l_dungeon_randomized 的脏 OFPA 包（不调 save_current_level、不动主 umap）、
     回写磁盘镜像、Receipts/install.json(stage='map_saved')。
2. 登记钩子：`DungeonRouteRepairs20260922/Scripts/extend_catalog.py` 第 70 行
   （room_variants 块）之后追加同款 receipt 门控 runpy 块——唯一要改的共享脚本；
   **不登记 room-extensions.json**（整模块替换通道会把后续字段改动回滚成快照）。
3. 同时给 RouteRepairs `install.py` 的资产收集清单补 `spawn` 字段，
   否则全量重装后 ModuleAssets 缺怪物类、cook 不含、运行时加载失败。
4. C++ 消费端（生成器侧）：`PrepareAssembly` 的 QueueAsset 把池内每个 class 排进
   Dungeon.Resources 段；刷怪 job/导演创建**必须挂 `State->bRuntime` 门**——
   既有安装器会跑 GeneratePreview 并存图，编辑器预览刷怪会把怪写进 OFPA 包
   （且 AutoPossessAI 会在编辑器里跑行为树）。
5. Boss 类校验硬编码 `IsChildOf(AHandBrainMonster)`（generator cpp:737），
   普通池消费端需自定基类约束（ACharacter + MonsterCombatComponent 存在性）。
6. 执行环境：离线段纯 Python；安装走 headless `UnrealEditor-Cmd -run=pythonscript`；
   已有交互编辑器在跑时不能再起 commandlet（端口冲突），须走桥批次；
   commandlet 已知 exit 1 噪声以脚本成功标记+回执为准。
7. `spawn` 段格式（每房）：
   `{ "theme": "wet", "count": [2,4], "anchor_roles": ["encounter"],
      "pool": [ { "id": "PoisonMaggot", "class": "/Game/...", "weight": 3, "cost": 1.5,
                  "level": 4, "rank": "elite" } ] }`
   密度模型候选：threat-budget（废案 `industrial_exploration_v1.json` 保留的原版数值口径：
   房间预算 10×类型倍率×进度 0.85→1.3，怪物 cost 表，alive cap 6/8/12）——
   该文件的空间配方已被用户退回，**只取数值语义，不取布局语义**；schema 冻结时定夺。
- 家族主题基线（首批，用现有已验证怪物，全部走注册表类路径）：
  | 房型 | 池（权重示意） |
  |---|---|
  | Drainage×3 | 毒蛆(3)、护士(1) |
  | Distribution | 护士(3)、胖子(2) |
  | ShoredBreach | 野狼(2)、僵尸犬(2)、感染犬(1) |
  | VentilationLoop×3 | 突变体-3(2)、护士(2) |
  | FreightTransfer | 胖子(3)、突变体-3(1) |
- 入池前置：每种怪完成地牢 nav 规格盘点（不合规者先不进池）；
  巫婆/手脑不入普通池（手脑保留 Boss 身份；巫婆体型/动作未在地牢验证）。

### C1. 封门精英房（ADungeonRoomEncounter，新文件）

- 每支线随机 1 间普通房为精英房（玩法流抽取；run 内共 3 间）。
- 编成：1 精英（`EMonsterRank::Elite`，等级+2，经验×2/金币×3 走现有倍率）+2–3 护卫。
- 门闸复用 Boss gate 构件模式（ISM 格栅+Box 碰撞）：玩家越过门内触发线→
  全部怪物成功生成后才封门；生成失败保持开门、离场再进入重试（Boss 遭遇同款，避免每帧刷怪）；
  清完开门并标记 cleared；玩家死亡/离场→重置开门。
- 实现为 `DungeonBossEncounter` 的泛化兄弟类（多怪、任意类、无奖励门），不改动 Boss 类本身。

### C2. 宝箱掉落（2026-09-25 loot 审计后细化）

- 挂接点：`ColdSteelWorldInteraction::OpenTreasureChest` 完成定时器内、
  `TreasureOpenedTag` 之后（开盖动画播完才出货）；lambda 补捕 PC 与
  `UColdSteelStatusModel`（GameInstanceSubsystem）弱引用。
- 发放路径：**首批直接入包**（`AddItem`：弹药自动转 `GrantAmmo` 进弹药袋，
  失败有"背包空间不足"提示；金币沿 AwardKill 口径 `CreateItem("gold",n)`+Insert 合并堆叠）。
  不走世界掉落：地牢每次进入重新随机布局，`Place=2` 档案条目会被 `RefreshDrops`
  在旧坐标复活（悬空/埋墙）；光柱拾取表现留作后续可选（需配套"新局清除
  Map==L_Dungeon_Randomized 的 Place=2 条目"）。
- Loot 表：工程内无现成 loot 文件，新建 `Content/ColdSteelData/dungeon_loot.json`
  （进程启动读一次，沿 items/smelting 惯例）；候选 id 已从 items.json 盘点
  （金币/8 口径弹药/hp、mp 药水四档/附魔卷轴/强化石/魔法粉尘/锭与矿/祭品稀有物）。
- 深度档位：manifest 的 `floor` 字段或 Run 子系统房间图 BFS 步数；
  随机流 = `GeneratedSeed ^ 新常量 ^ 节点号`（同箱内容确定、与布局/dressing/水渍流互不干扰）。
- 最终宝箱（`DungeonFinalTreasure`）接同一 loot 表高档位；既有锁定/解锁流程不动。
- 配套风险处理：`AwardKill` 满包兜底会在地牢图内产生 `Place=2` 世界掉落，
  跨局残留问题与上同；首批在新局生成完成时清除地牢图的旧 Place=2 条目（小改动、定向）。

### C3. 警报传播（最简版）

- 导演维护“警报集”：枪声/受击/嚎叫（AI Perception 已有事实）所在房间的邻接房提前唤醒；
  狼嚎沿用现有 howl 警戒半径。不做跨全屋全图拉怪。

### 首批验收清单（用户实测口径）

- 进入地牢：普通房有怪、编成随深度增强、不在视线内凭空出现；
- 清完的房间往返不再刷怪；重开一局（新种子/同种子）编成分别重掷/可复现；
- 精英房封门→清完开门；玩家死亡或离场门恢复；
- 宝箱与最终宝箱出掉落；Boss 流程与奖励门不受影响；
- 重新生成布局/返回基地无残留怪物；帧率无明显尖峰（休眠与摊帧生效）；
- 同一种子多次进入，房间布局与既有版本完全一致（玩法流未污染布局流）。

## 第二批（Phase D，随机性扩展）

- 支线主题化：三条支线每轮随机分配主题（战斗重/宝物多/危害重/安静），
  驱动 spawn 密度、宝箱概率、粘液通道数量、灯光色调；全部走玩法/装饰独立流。
- 每局词缀（mutators）：种子驱动 0–2 个全局词缀（停电/粘液潮/群涌/富矿），
  只改灯光/危害/数量/掉落倍率；数值 cvar 化交用户调。
- 房型扩容：按 V3 管线给 Distribution/FreightTransfer/ShoredBreach 补结构变体，
  新增 1–2 新房型（Blender authoring → import → extend_catalog 链）。
- 危害随机化：粘液通道位置/开关进随机层。
- Boss 支线随机化：**暂缓**（用户拍板）；如后续纳入，需单独评估 compact lane
  与 `AnchorCompactTerminal` 对中路假设的路由改动。

## 第三批（Phase E，元循环）

- 起始神像赐福作为 pre-run 选择（README 既有留待项）。
- 种子输入 UI/每日种子；run 结算统计（击杀/宝物/耗时/死亡）。
- 难度档位：词缀数量与等级基线随玩家等级或通关次数递进。

## 风险与边界

- 多体型怪物与单一运行时 nav volume 的规格相容是首批最大技术风险；
  不合规怪物延后入池，不为刷怪绕过导航限制强行生成。
- 休眠/唤醒与感知系统的交互需防止“唤醒瞬间索敌穿墙”；唤醒只在玩家邻接集发生，天然限距。
- 掉落表数值全部为首值建议，来源标注旧废案口径或现有公式；实装后由用户试玩调参。
- 本批不新增存档结构、不做联机（沿用 NM_Standalone 守卫）、不动旧 `Dungeon/` 兼容代码。
- 全程后台制作：构建/导入/保存完成即交付，不自动 PIE、截图或验收；实机手感由用户测试。
