# FPSGAME 联机系统策略与实施计划

日期：2026-09-30
状态：**M1 已启动**（隔离 worktree + 插件骨架 + 基线冒烟）。进展与断点续接见活文档 [MultiplayerWorkLog.md](MultiplayerWorkLog.md)——**接手者从那里读起**。主线 worktree 上有 1154 个并行 WIP 改动在飞，联机开发全程不触碰（开发在隔离分支进行，接入窗口见 §7）
依据：FAB 市场调研（2026-09-30，结论：无"直接套用"级方案）+ 三路代码审计（玩家侧 / 世界侧 / 物品战斗侧，全部带 file:line 证据）

---

## 0. 定案摘要

| 决策点 | 结论 | 理由 |
|---|---|---|
| 网络模型 | **UE 原生复制 + 监听服务器（listen server）起步，预留专用服** | 现有 C++ 架构可延续；`FPSPlayerBodyComponent` 已按原生复制规范预留；怪物/地牢已有 `HasAuthority()` 守卫 |
| 拒绝方案 | Photon Fusion（备选保留） | 自带网络对象模型 = 563 文件按其 API 重写网络层，改造量不比原生小，还要接受 CCU 计费；仅当未来需要大 CCU 房间服务时重评 |
| 会话/大厅 | 裸 IP 直连（`open IP:7777`）先行；**M6 再挂 Epic 官方 OnlineServices（EOS）** | EOS 免费（引擎内置插件），负责匹配/好友/跨平台，不做玩法同步 |
| 参考件 | Lyra 样例（只参考不引入）：PlayerState 承载玩家数据、FastArray 序列化、复制节奏 | 引入 Lyra 的 GameFeatures/模块化整套架构对本工程是过度工程 |
| 权威模型 | **服务端权威**：伤害/档案/世界编辑/怪物全部服务器结算，客户端只做输入+预测+表现 | 技能结算侧已有 `Shooter->HasAuthority()` 门禁，方向一致 |
| 开发隔离 | **git worktree（从 HEAD 拉分支）+ 新插件模块承载新增代码**，主线零接触 | 见 §6 |

---

## 1. 现状审计结论（三路并行，2026-09-30）

### 1.1 全局硬事实

- **全库零 RPC**：`UFUNCTION(Server/Client/NetMulticast)` 0 命中；复制代码仅 1 处（玩家身体组件）+ 1 处显式关闭（`FPSWeaponFXComponent.cpp:262`）。
- **10+ 处 `NM_Standalone` 硬闸门**：多人模式下一大批系统会**直接拒绝初始化**，不是"悄悄不同步"。完整清单见 §1.4。
- GameMode 是 `AGameModeBase`（单机基类）；`DefaultEngine.ini` 无任何联网配置。

### 1.2 最大结构性障碍（按优先级）

**障碍 A：`UColdSteelStatusModel` 是 UGameInstanceSubsystem 单例档案**（`UI/ColdSteelStatusModel.h:19`）
背包、装备、技能 CD、蓝量、快捷栏、地牢进度、掉落物全在这一个全局单例里，只有单个 `CurrentPawn` 弱指针（`:417`）。监听服务器上只有主机侧有一份，且被 `GetPlayerPawn(this,0)`（`ColdSteelSkillModel.cpp:136`、`ColdSteelQuickBarModel.cpp:123`）硬编码玩家 0。客户端进程里那份与服务端完全隔离。**这是联机改造的第一优先级，高于一切单点问题。**

**障碍 B：玩家 pawn 没有权威/本地模型**（`FPSGAMECharacter.cpp`，216KB god class）
- Tick（`:746-798`）无门禁跑全套玩法（换弹、持续开火结算 `ServiceHeldFire:775`、viewmodel、后坐力直写 `ControlRotation:2381-2387`）。
- 输入全绑在 pawn 的老式 `BindAxis/BindAction`（`:723-744`），弹匣/备弹/武器状态全是非复制字段（`FPSGAMECharacter.h:578-580`）。
- 开火→命中→伤害全链路本地执行：`FireShot:2226` 本地双 LineTrace → `ColdSteelSkills::ApplyHit`（`ColdSteelSkillRules.cpp:402`）→ `ApplySkillWeaponHit`（`ColdSteelSkillModel.cpp:153-228`）。客户端打出的伤害在服务端世界不存在（被技能侧 `HasAuthority()` 门禁吞掉）。

**障碍 C：世界侧运行时生成且零复制**
- 丘陵世界 `TemperateHillsWorld.cpp:168` 非 Standalone 直接 Error+return——客户端什么都不生成（地形/河水/植被/碰撞全是挂在世界 actor 上的组件，非复制）。
- 地牢 `AuthoredDungeonGenerator.cpp:402` 同款闸门，数百个 runtime spawn 的非复制 actor。
- 建造 `VoxelBuildWorld` 是"每客户端一个本地 actor + 本地 .sav"（`VoxelBuildComponent.cpp:158`、`VoxelBuildWorld.cpp:110` 双闸门）。

### 1.3 现成可复用资产（好消息清单）

| 资产 | 位置 | 价值 |
|---|---|---|
| **玩家第三身复制骨架** | `Characters/FPSPlayerBodyComponent.h:41-46`（ReplicatedState/Weapons/Outfit + OnRep + DOREPLIFETIME + 服务器时钟 `GetServerWorldTimeSeconds`） | 全工程唯一网络代码，注释明写"给未来权威战斗适配器发布"（`SetAuthoritativeState`，目前零调用）。多人互相看见对方的第一块砖已就位 |
| **怪物/地牢已按服务器权威写** | `HandBrainMonster`/`NurseZombie`/`WitchMonster` 等 20+ 处 `HasAuthority()` 守卫；`DungeonSpawnDirector.cpp:104-110` 双闸 | 监听服务器上怪物逻辑天然跑在服务端 |
| **AIPerception 多目标天然友好** | `MonsterAIController.cpp:34-42` | 感知任意 `IsPlayerControlled()` 的 pawn，不挑玩家 0 |
| **世界生成完全确定性** | 同 seed 同布局（自研整型 hash，`TemperateHillsWorld.cpp:43-44`），地形编辑存档重放（`:121-151`） | "服务端发 seed+delta，客户端本地重建同样世界"路线可行，免去海量几何体复制 |
| **天气纯表现** | `FPSWeatherManager` 无 gameplay 消费方（怪物系统零引用），seed 固定 | 客户端各自确定性跑即可两端一致 |
| **UI 全部本地创建** | `FPSGAMEPlayerController.cpp:109-127` 已有 `IsLocalController()` 门禁 | 客户端侧 UI 天然安全，不需要大改 |
| **地牢刷怪确定性随机流** | `FRandomStream GameplayStream(Domain^NodeSalt)`（`DungeonRunSubsystem.h:13-21`） | seed 同步后两端/服务器一致 |

### 1.4 `NM_Standalone` 硬闸门清单（多人模式第一批要拆的雷）

| 位置 | 后果（监听服务器形态） |
|---|---|
| `UI/ColdSteelProfileRuntime.cpp:135`（PersistState） | **所有人（含主机）档案写不进去**——"能玩不能存" |
| `Building/VoxelBuildWorldSave.cpp:44,49` | 建造存档拒写 |
| `Monsters/FPSCombatHealthComponent.cpp:46` | 玩家防御公式静默跳过（数值行为变化） |
| `WorldGeneration/TemperateHillsWorld.cpp:168` | 开放世界客户端零生成 |
| `Dungeons/AuthoredDungeonGenerator.cpp:402` | 地牢生成器停摆 |
| `Building/VoxelBuildComponent.cpp:158`、`VoxelBuildWorld.cpp:110` | 建造初始化直接失败 |
| `SceneTestPortal.cpp:93,113,177` | 传送门完全不工作（且 runtime spawn 不复制） |
| `Building/ForgingSystem.cpp:75,218`、`GunAssemblySystem.cpp:78,195` | 锻造/拼装拒绝多人 |
| `Items/FPSPotionUseComponent.cpp:73`、`Skills/FPSLightningComponent.cpp:85` | 喝药/闪电技能多人下失效 |

另有一批 `GetFirstPlayerController/GetPlayerController(0)` 命中需要分两类处理：
- **玩法语义（必须改）**：`Building/ColdSteelDoor.cpp:203`、`ColdSteelWindow.cpp:262`（门/窗开向判定）、`Dungeons/DungeonSpawnDirector.cpp:829`（刷怪落点只躲玩家 0）、怪物 AwardKill 的 `IsLocalController()` 门槛（服务端对远程玩家不成立，击杀奖励会丢：`HandBrainMonster.cpp:203` 等 6 处）。
- **表现语义（低危，批量后置）**：水面/草/特效取第一玩家视点做 LOD/降频（`FluidPresentationSubsystem`、`GrassDeformSubsystem`、怪物 FX 等 ~15 处）——监听服上只按主机视角算，客户端表现打折但不坏玩法。

---

## 2. 目标架构

### 2.1 权威与数据流总图

```
┌─ 客户端（每个玩家进程）──────────────┐      ┌─ 监听服务器（主机进程，首期）─────────────┐
│ 输入(Axis/Action 绑定保留在 pawn)      │      │ AFPSNetGameMode(AGameMode)                 │
│  ├─ 移动: CharacterMovement 预测      │      │  ├─ 出生点轮询分配(不再 first-fit 挤同点)  │
│  ├─ 开火: ServerRPC(FireRequest) ────────►──►│  ├─ 服务端射线/弹道模拟 → ApplyHit 权威结算 │
│  └─ UI/装备/消耗: 请求→等待回执         │      │  ├─ 怪物 AI/刷怪/地牢(已有权威守卫)         │
│                                      │      │  ├─ 档案会话(per PlayerController)         │
│ UColdSteelStatusModel = 服务端镜像 ──◄───复制──│  │   (权威数据 + 节流落盘)                  │
│  (读 API 不变 → UI 零改动)            │      │  ├─ VoxelBuildWorld 服务器单实例           │
│                                      │      │  └─ TemperateHillsWorld: seed 广播+编辑delta│
│ FPSPlayerBodyComponent(现成) ◄──────────────复制── ReplicatedState/Weapons/Outfit          │
│ 表现: 天气/音效/FX 本地确定性跑        │      └───────────────────────────────────────────┘
└──────────────────────────────────────┘
```

### 2.2 档案多人化设计（障碍 A 的解法，改动最小路径）

核心思路：**保留 `UColdSteelStatusModel` 的读 API，把它降级为"服务端状态的客户端镜像"**，UI 层（几十个直接读它的 widget）零改动。

- 服务端：新增 `UColdSteelPlayerSession`（每 `APlayerController` 一个，挂在控制器或 PlayerState 上）——权威持有 `FColdSteelProfile`，加载/落盘磁盘档案（主机磁盘），驱动 `ApplyToPawn`。
- 客户端：`UColdSteelStatusModel` 保留单例身份（每进程本来只有本地一个玩家），内容来源从"本地磁盘事务"改为"服务端复制回推"。写操作（MoveItem/UseItem/装备）改为发请求 RPC，服务端事务后回推结果。
- 关键取舍：现有"每次换装=同步双槽写盘事务"（`ColdSteelProfileRuntime.cpp:129-166`）必须先**内存权威化**（写盘节流到退出/定时），否则多人下每次操作都是游戏线程磁盘事务 + 网络往返，延迟不可接受。
- 首版简化：**只支持主机档案 + 客人临时档案**（客人进度不落盘或落到独立 slot），把"多玩家档案管理"推迟到 M6 之后。理由：先把玩法同步跑通，档案归属是运营问题不是同步问题。

### 2.3 世界同步设计（障碍 C 的解法）

- **丘陵开放世界**：走确定性重建。服务端 `TemperateHillsWorld` 保留为权威（地形编辑/树桩再生/矿脉枯竭），通过复制字段下发 `Seed/WorldId`，客户端收到后本地跑同一套确定性生成（拆掉 `:168` 闸门改为 `IsNetMode(NM_Client) ? 重放模式 : 权威模式`）。动态变化走 delta 通道：地形编辑本就存档重放（复用同一条 `PersistTerrainEdits` 数据结构做复制）；采割状态从玩家档案迁到世界权威侧（现状在玩家档案里：`TemperateHillsProduction.cpp:23-35`，多人下"我砍的树别人看不见"）。
- **地牢**：`DungeonSeed` 同样复制下发，两端确定性生成（生成器本身是确定性的，去掉闸门即可各自装配）；怪物由服务端权威 spawn（pawn 默认复制）。首版可选降级：地牢暂缓多人，先开放世界+hub。
- **建造**：`AVoxelBuildWorld` 改为服务端单实例 + 客户端镜像：放置/拆除走 Server RPC，服务端改格子后把 EditCells delta 复制（或粗粒度：构件级复制）。存档槽从"玩家槽|地图|Guid"改为服务器共享世界槽。
- **传送门/旅行**：`OpenLevel` 硬旅行换 seamless travel（`AGameMode::bUseSeamlessTravel`），传送门 actor 改服务器 spawn+复制。

---

## 3. 分阶段里程碑

> 通用规则：每阶段必须过"验收门"才进下一阶段；**每阶段对主线的接触点为 0**（全部在隔离分支，见 §6）；每阶段结束打 tag。

### M0 计划与地基准备（本文档）
- 交付：本计划 + 审计结论固化。
- 验收：用户认可路线与隔离方案。

### M1 联机地基（双进程互见）
- 范围：
  - 新建 `ColdSteelNet` 插件（模块 `ColdSteelNet`）：`AFPSNetGameMode : AGameMode`（含出生点轮询分配）、连接/断线日志、基础 net 配置。
  - `FPSGAMECharacter` 补本地门禁：Tick/BeginPlay 的玩法驱动（换弹/开火/viewmodel/后坐力）加 `IsLocallyControlled()` 分叉（在分支上改）；`SetupPlayerInputComponent` 保持只在本地绑定（引擎自动：仅 owned pawn 绑定，无需改）。
  - 激活 `FPSPlayerBodyComponent` 的权威喂料：服务端按档案 `ApplyToPawn` 后调 `SetAuthoritativeState/...Equipment`（把现有"本地 Tick 直写复制字段"路径在服务端补全）。
  - net 配置进 `DefaultEngine.ini`（GameEngine/NetDriver 段、`GameSession`、复制间隔调优项留注释）。
- 验收门（自动化双进程冒烟，见 §5）：主机+客户端两窗口，日志断言双方 pawn 存在、位置互见、第三身身体/武器外观互见、主机档案可正常读档（闸门 A 已拆或绕过——若 M1 先不动 `ColdSteelProfileRuntime.cpp:135`，则临时以 `?ColdSteelProfile=` 独立槽+允许 ListenServer 写盘的最小补丁处理）。
- 已知风险：`LoadSynchronous` 在远端首包同步会卡（装备软路径加载）——M1 只做"能看见"，卡顿优化放 M5。

### M2 档案权威化（最重结构工程）
- 范围：§2.2 全部——三闸门拆除（`ColdSteelProfileRuntime.cpp:135`、`VoxelBuildWorldSave.cpp:44/49`、`FPSCombatHealthComponent.cpp:46`）、`UColdSteelPlayerSession`、StatusModel 镜像化、写操作请求化、写盘节流。
- 验收门：双进程下客人能开背包、拖动物品、装备武器、喝药（喝药闸门 `FPSPotionUseComponent.cpp:73` 同步拆除），两端 UI 与服务端状态一致；主机磁盘档案正确落盘。
- 风险：UI 写路径直改 API 的面较大（InventoryWidget/QuickBar/SkillPage 等），逐面板迁移，先背包后技能。

### M3 战斗权威化
- 范围：开火/近战/施法 Server RPC 通道；服务端弹道模拟（`FPSBallisticsComponent` 在服务端跑，命中结果 Multicast 表现）；弹匣/备弹复制；怪物血量/死亡/削韧复制（`UFPSCombatHealthComponent` 补复制声明）；AwardKill 改按 `PlayerState/Controller` 归属发放；门/窗开向与刷怪落点的多玩家化（`GetFirstPlayerController` 玩法语义 4 处）。
- 验收门：双进程对射木桩/怪物，伤害数字、击杀奖励、怪物死亡两端一致；弹匣同步正确；主机打客户端、客户端打主机均有效。
- 性能预算（按用户性能优先规则）：开火 RPC ≤ 1 次/枪/秒级；怪物复制走条件属性（`bReplicateMovement` 关掉非根骨位移的怪用 NetUpdateFrequency 降频），单怪复制字节数在验收时量化记录。

### M4 世界同步
- 范围：§2.3 前半——丘陵 seed 复制+客户端确定性重建+地形编辑 delta；采割状态迁世界侧；传送门 seamless travel；天气/昼夜本地确定性（seed 已固定，几乎白捡）。
- 验收门：客人加入主机开放世界，地形/植被/河流肉眼一致；主机挖坑客人可见；双向传送门双端可用；昼夜两端同步。
- 已知深坑（提前挂号）：PCG 植被分区分帧调度在客户端重放时的耗时对齐；`FlushLevelStreaming(Full)` 每登录一次的代价（改增量流送确认）。

### M5 建造服务端权威 + 表现打磨
- 范围：VoxelBuildWorld 服务器单实例+编辑 RPC+复制；存档共享槽；锻造/拼装多人化（拆 `ForgingSystem/GunAssemblySystem` 闸门）；装备复制 `LoadSynchronous` 换异步预载；第一玩家视点 LOD 类 `GetPlayerController(0)` 表现命中批量改为"每玩家本地视角各自算"。
- 验收门：双端共同盖房、拆房触发同一倒塌；存档重进一致；加入过程无秒级卡顿。

### M6 会话与外围
- 范围：引擎内置 **OnlineServices(EOS)** 插件接入（会话/好友/加入邀请，需注册 Epic 开发者账号+产品凭证）；语音（EOS Voice 或先不做）；带宽复核（NetCullDistance/优先级；可选 ReplicationGraph）；防作弊基础（服务端校验速度/射速/弹药）；客人档案策略定案。
- 验收门：通过会话列表（而非裸 IP）完成一次完整的加入-游玩-退出。

### 地牢多人化的位置
M4 只做"传送与种子同步"，地牢内玩法依赖 M3 的怪物复制；完整地牢多人体验排在 M4-M5 之间的独立小阶段（M4.5），不阻塞主线里程碑。

---

## 4. 隔离开发策略（不干扰主线的硬保证）

1. **代码隔离：git worktree。** 从 `main` HEAD（`da91c6d6`）拉独立分支 `feature/multiplayer`，worktree 放 `D:\FPS3D\FPSGAME-mp`（junction 方式，拆除前先 `rmdir` 断链——见既有教训）。主仓 1154 个 WIP 文件完全不被触碰。
   - 已知风险：HEAD 干净树的可编译性未经证实（历史上出现过坏 HEAD；近期 Game 双编成功均含 WIP）。缓解：M1 起步先只做"插件骨架 + 配置"，等主线 WIP 落盘后的下一个接入窗口再 rebase 到新 HEAD 做涉及深改的阶段（M2+ 的 Character/StatusModel 改动都在 rebase 之后）。
2. **新增代码以插件承载**：`Plugins/ColdSteelNet/`（运行时模块）。好处：对主树是纯增量目录；merge 时冲突面最小；将来不想联机可以整插件禁用。
3. **构建错峰**：完全遵守 WORKFLOW.md 构建串行化三条（先查 UBT/cl.exe 进程与排队日志，等当前构建结束再提交，等待期做不依赖构建的编码）。联机构建一律用独立目标输出目录，不与主线共用 Binaries 锁。
4. **测试不占编辑器**：双进程测试全部用 `-game` 独立进程（见 §5），不碰编辑器会话；避免与其他会话的 PIE/输入锁冲突。
5. **文档与 JSON 表**：联机相关文档全部新文件（本文件即如此）；不改 `items.json` 等主线也在改的共享表——联机不引入任何表结构变更。

## 5. 测试策略

- **双进程冒烟（每阶段验收的标准姿势）**：
  1. 主机：`FPSGAME.exe /Game/GameMaps/DayNight_Lighting?listen -game -log -Windowed`
  2. 客人：第二个进程 `-game -log -Windowed`，进入后控制台/启动参数 `open 127.0.0.1:7777`
  3. 断言走日志：两份 `FPSGAME.log` 里 grep 关键行（`Join succeeded`/`Possess`/自定义 `MPTEST` 标记行），不依赖人工盯屏。
  - 已知坑：`-RenderOffscreen` 模式自 2026-09-18 起约 15s 崩溃——一律用 `-Windowed`；`-unattended` 下 actor 变换不生效，测试脚本不用它。
- **确定性校验**：世界重建一致性用既有布局哈希审计思路（同 seed 双端各跑布局 hash 比对，可写成 commandlet）。
- **回归保护**：所有"本地门禁"改动必须同时跑单机路径（Standalone 模式冒烟），确保单机玩法零回归——单机仍是第一交付形态。

## 6. 对主系统的接入点清单（最终 merge 时的全部触碰面）

| 接入点 | 类型 | 阶段 |
|---|---|---|
| `Plugins/ColdSteelNet/` 整目录 | 纯新增 | M1 |
| `Config/DefaultEngine.ini` 联网段 + GameMode 映射（若换 NetGameMode） | 配置增量 | M1 |
| `FPSGAMECharacter*` 本地门禁与 RPC 通道 | 分支内改，merge 进主线 | M1-M3 |
| `ColdSteelProfileRuntime`/`StatusModel` 镜像化 | 分支内改，merge 进主线 | M2 |
| `TemperateHillsWorld`/`VoxelBuildWorld` 权威化 | 分支内改，merge 进主线 | M4-M5 |
| `WORKFLOW.md` 增补联机构建/测试守则 | 文档增量 | M1 |

接入窗口触发条件（满足其一）：主线大 WIP 落盘出现静默期；或用户点名接入测试。

## 7. 风险登记册

| 风险 | 等级 | 缓解 |
|---|---|---|
| 216KB Character god class 改造牵一发动全身 | 高 | 分文件拆改（该类本就是多 cpp 分文件），每步 Standalone 回归 |
| HEAD 不可编译 | 中 | M1 只做插件骨架；M2+ 前 rebase 到已验证 HEAD |
| 工程级构建互斥（引擎级锁） | 中 | 错峰规则 + 独立输出目录 |
| 客户端首次加入卡顿（装备 LoadSynchronous/世界重建） | 中 | M1 接受、M5 异步化；加入过程复用 TransitLoadingSubsystem 遮罩 |
| 档案归属/客人进度方案未定 | 中 | 首版"客人临时档案"，M6 定案 |
| 单机回归 | 高 | §5 明确单机冒烟为每阶段硬门 |
| 采割状态迁移影响现有存档兼容 | 中 | 世界存档加版本字段，旧档迁移读入 |

---

## 附：本计划的证据坐标索引（审计原始结论速查）

- 档案单例：`UI/ColdSteelStatusModel.h:19-20`、`CurrentPawn :417`、玩家0硬编码 `ColdSteelSkillModel.cpp:136`
- 角色 Tick 无门禁：`FPSGAMECharacter.cpp:746-798`；开火链 `:2226-2340`；后坐力直写 `:2381-2387`
- 身体复制骨架：`Characters/FPSPlayerBodyComponent.h:18-46`、`cpp:158,215-252,282-296`
- 硬闸门全表：§1.4
- 世界确定性：`WorldGeneration/TemperateHillsWorld.cpp:43-44,103-160,555-562`
- 怪物权威守卫：`MonsterAIController.cpp:47`、`DungeonSpawnDirector.cpp:104-110` 等 20+ 处
- 存档双槽事务：`ColdSteelProfileRuntime.cpp:76-83,129-166`；建造 VBX：`VoxelBuildWorld.cpp:108-116`
- UI 本地门禁：`FPSGAMEPlayerController.cpp:109-127`
