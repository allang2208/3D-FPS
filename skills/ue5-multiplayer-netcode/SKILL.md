---
name: ue5-multiplayer-netcode
description: UE5 原生复制联机开发（监听服务器起步）的工程套路与坑：SavedMove 自定义压缩位传移动意图、PlayerState 玩家数据归属（OwnerOnly 镜像+分片上行）、服务端 rewind 命中校验、WorldSubsystem 引导、RPC 载荷限制、PIE 环境假象、双进程冒烟取证、相位化权威施法通道与法术 actor 复制套路。联机玩法改造、同步排查时使用。
---

# UE5 原生复制联机开发套路（FPSGAME 联机线沉淀，2026-10-02 成熟方案重构版）

工程背景：563 cpp 纯单机 C++ 工程改造为监听服务器多人。全案见 `Docs/MultiplayerStrategyAndPlan20260930.md`（计划）与 `Docs/MultiplayerWorkLog.md`（活日志/断点续接）。2026-10-02 按 Lyra/ShooterGame(nbertoa) 口径完成架构重构，旧「ChannelComponent 挂 PlayerController + 84KB 心跳」路线已退役至 `trash/mp-channel-into-playerstate/`。

## 〇、当前架构地图（重构后，先看这张表）

| 职责 | 载体 | 位置 |
|---|---|---|
| 移动意图（冲刺/ADS/滑铲） | `FSavedMove_FPSCharacter` 压缩位 FLAG_Custom_0/1/2，随移动包同帧 | `Source/FPSGAME/Movement/FPSCharacterMovementComponent.{h,cpp}` |
| 闪避位移 | `FRootMotionSource_FPSDodge` 进 SavedMove 的 SavedRootMotion（原生通道） | `Movement/FPSDodgeMovement.cpp`、`FPSDodgeRootMotionSource.h` |
| 玩家持久数据/档案 | `AColdSteelPlayerState`：PublicInfo 全员复制 + MirrorBlob `COND_OwnerOnly` + 分片上行 + 服务端影子档案 | `Source/FPSGAME/Multiplayer/ColdSteelPlayerState.{h,cpp}` |
| MP 引导（与地图 GameMode 解耦） | `UColdSteelNetWorldSubsystem` 挂 `FGameModeEvents::PostLogin/Logout` | `Source/FPSGAME/Multiplayer/ColdSteelNetWorldSubsystem.{h,cpp}` |
| 命中权威 | 客户端报几何+时间戳+语义 flag → 服务端 ValidateHitReport（令牌桶/武器匹配/时间窗/rewind 几何）→ 影子档案复算 Shot → ApplySkillWeaponHit → ClientConfirmHit 回执 | `ColdSteelPlayerState.cpp`、`ForwardHit` |
| 滞延回放缓冲 | `UFPSCombatHealthComponent` 服务端 25Hz 位姿环形历史（24 帧≈0.96s），`GetLagPose` 按服务端时钟插值 | `Monsters/FPSCombatHealthComponent.{h,cpp}` |
| 远端形象 | 服务端 `SampleRemoteAuthorityState` 采远端 pawn 写 `ReplicatedState`；`ApplyColdSteelProfile` 后 `CaptureEquipment` 填 `ReplicatedWeapons/Outfit` | `Characters/FPSPlayerBody*.cpp` |
| 连接预热 | `UColdSteelNetConnectSubsystem`（-MPConnect 焐图） | 插件 `ColdSteelNet` |

## 一、移动同步：状态进 SavedMove，不走旁路 RPC

1. **所有影响 MaxSpeed/摩擦的布尔一律压 `FSavedMove_Character::CompressedFlags` 的 FLAG_Custom_N**，随预测包同帧到服务端：`UpdateFromCompressedFlags` 解包→同帧回写 MaxWalkSpeed（不等角色 Tick，消一档之差的 rubber-band 窗口）。影响连续状态的离散动作（滑铲）也走 flag：权威端 flag 触发完整 `StartSlide`（含初速），回放路径（PrepMoveFor）只还原状态位+摩擦，**不能再注入初速**（该帧速度由 move 重算）。
2. `CanCombineWith` 必须在任一自定义位变化时拒合并——否则服务端以错误的档执行合并 move。
3. **位移型技能走 `FRootMotionSource`**（闪避已示范）：RootMotionSource 自动随 SavedMove 的 SavedRootMotion 上服务端，服务端副本无本地 ID，按 `InstanceName` 扫描 `CurrentRootMotion`/`Character->SavedRootMotion` 判定激活（见 `IsDodging()`）。单机门禁 `GetNetMode()==NM_Standalone` 会把功能在联机下整个关掉——排查"联机里某功能消失"先查这类门禁。
4. 服务端副本的速度档、滑铲物理、闪避位移全部由 move 驱动，**两端跑的是同一段代码**——不要在服务端写平行实现。
5. 历史教训：曾用 `ServerSetSprinting` reliable RPC 传冲刺——可靠 RPC 与移动包时序不绑定，`bX||bServerX` 的 OR 语义让卡住的 true 永不自动退。**凡"按住/松开"类状态都不许走独立 RPC**。

## 二、玩家数据：挂 PlayerState，不挂 PC 组件/全局心跳

6. **持久玩家状态放 `AColdSteelPlayerState`**：全员可见字段普通复制；私有档案镜像 `DOREPLIFETIME_CONDITION(..., COND_OwnerOnly)`。PlayerState 生命周期跨换 pawn，天然是玩家身份锚点。
7. **大载荷 reliable RPC 会被静默丢弃**（整块 83KB 单发=消失，无日志；8KB×11 连发灌爆 reliable 窗口）。上行=**首传 512B 分片 + ≤2 片/tick + UploadId 防串包 + CRC 变更检测**；下行走复制属性让引擎自己分包。周期全量心跳已删——闲时上行=0。
8. **服务端为每个远端玩家建影子档案**（`UColdSteelStatusModel::CreateShadowModel`，注意 `NewObject` 的 Outer 必须传宿主 GameInstance），挂到远端 pawn 的 `NetShadowProfile`；**服务端读玩家数值一律 `GetNetShadowProfile()` 优先、GI 单例兜底**——直接读 `GameInstanceSubsystem` 在服务端拿到的是主机档案（曾致客人伤害/防御/月影/闪避奖励全部记错人）。
9. GameInstance 单例子系统被每 pawn 各调一次=N 倍速 tick——`TickRuntime` 类入口必须 `IsLocallyControlled()` 门禁。角色 Tick 的纯表现族（相机/视模等 11 项）同理全端门禁。

## 三、命中权威：客户端只报几何+时间戳，服务端复算

10. `FColdSteelNetHitReport` 只携带 Target/瞄准原点/命中点/法线/骨名/方向/武器定义/**服务端时钟域时间戳**/语义 flag/汇聚弹数。伤害、暴击、穿甲、经验**一律由服务端用影子档案 `ColdSteelSkills::Snapshot` 复算**；`ClaimedDamage` 只作包络钳位。
11. 校验链（ValidateHitReport）：影子档案存在→射手存活→武器定义匹配影子装备→射速令牌桶（按 `EffectiveFireInterval` 充能）→原点漂移/射程上限→**时间戳新鲜度**（-0.1s~0.9s 窗）→**rewind 几何**（目标胶囊轴插值回 ClientFireTime，弹道线段与胶囊轴最近距 ≤ 半径+60cm 容差）。
12. 时间戳口径：客户端发 `GameState->GetServerWorldTimeSeconds()`（估计的服务端时钟），不是本地 `GetTimeSeconds()`——两端时钟域不同。
13. rewind 缓冲在可命中目标身上（`UFPSCombatHealthComponent`）：authority+联机才开 Tick，25Hz×24 帧环形。只录位姿不搬 actor（数学重算，不 SetActorLocation——安全不扰动世界）。
14. `bFiredRound` 语义 flag 防客户端伪报"没消耗弹药"；汇聚弹数客户端申报、倍率服务端同参数复算后纳入包络。

## 四、GameMode 分层：引导不依赖被选中的 GameMode

15. **MP 初始化挂 `UColdSteelNetWorldSubsystem` + `FGameModeEvents::PostLogin/Logout`**——地图 WorldSettings 写死的 GameMode（如 `ATemperateHillsGameMode`）会覆盖 `?game=` 以外的默认 GameMode；NetGameMode 与地图 GameMode 平级时通道会整个缺席。
16. `PlayerStateClass` 在单机 GameMode 基类（`AFPSGAMEGameMode`）构造统一设置，所有地图继承链自动生效。
17. 插件 GameMode（`AFPSNetGameMode`）只保留默认 spawn 等 NetGameMode 语义，不再承担 MP 通道开关职责。

## 五、传输层红线（UHT/网络栈硬限制）

18. **TMap 不能进 RPC 参数/复制属性**（UHT 直接报错）。含 Map 的档案结构传输用**序列化字节块**：`UColdSteelProfileSave` + `FObjectAndNameAsStringProxyArchive(ArNoDelta=true)`，与 `SaveGameToSlot` 同口径——传输格式即存档格式。
19. 变更检测 + 字节级去重：CRC32 相同直接跳过上行。

## 六、客户端加入链与杂项坑

20. 客户端连 IP 先加载 GameDefaultMap 占位世界——冒烟时指轻量图。
21. 重资产地图网络旅行 LoadPackage 会 1.3s 静默失败——绕法=`-MPConnect=<addr> -MPConnectDelay=<秒>` 焐热资产再进程内 open。
22. 单机过场遮罩在联网客户端永不完成——Tick 顶部 net-client 旁路直接撕。
23. 监听服重登入出生点：会话占用表 + 无 PlayerStart 兜底 `RestartPlayerAtTransform(原点+250)`。
24. 模拟代理移动更新断流会按最后速度自走出图——OnRep_ReplicatedMovement 时间戳 + 0.5s 断流冻结。
25. 窗口失焦僵尸键用 Win32 `GetAsyncKeyState` 物理键态轮询单向清零（测试钩子合成输入要豁免）。

## 七、法术施法通道：相位化权威施法（2026-10-03 全法术收官）

30. **协议**：`FColdSteelNetCastRequest{SkillId,Phase,AimPoint,AimNormal,AimAxis,Variant,Target,Charge}` 走 `AColdSteelPlayerState::ServerCastSpell`（reliable）。Phase：0=凝聚 1=释放 2=凝聚取消（退蓝）3=弃置悬停体。`ExecuteCastRequest` 按 SkillId 分派：Phase0 影子档 `BeginXxxCast` 扣账（悬停类同时生成权威体挂 `PendingCastOrb`）；Phase1 调组件 `NetCommit*`/`NetRelease` 服务端入口；Phase2/3 通用退款/收尾。
31. **组件模板**：删 `NM_Client` 早退门——客人本地跑手势/凝聚/瞄准预览（本地 `BeginXxxCast` 预扣账立刻见反馈），意图上行；服务端影子档权威执行伤害/治疗/掉落并生成**复制 actor** 回流各端；客人本地收尾只 `FinishXxxCast(空Rewards)` 清预留。取消统一 Phase2。
32. **权威模型陷阱**：组件 `Model()`（GI 子系统）在服务端拿到的是**主机档案**——客人施法走 `NetCast::AuthorityModel(Pawn,GI)`：服务端→`GetNetShadowProfile()`，本地/单机→GI 档。所有 Apply/Finish 结算侧都走它。`ApplyXxxHit` 内部本就带 `Shooter->HasAuthority()` 门，客户端重复跑 hit 循环天然短路。
33. **法术 actor 复制套路**：`bReplicates=true` + 复制最小口径（`NetCaster/NetCast/NetPoint/NetState`）+ 远端 `NetInit()` 自载素材（**资产路径表提成共享静态表**，组件预热与远端自载共用一张清单）→ `InitializeX` 重演表现壳；伤害/结算段 `HasAuthority()` 门。短生命周期 actor 用 `SetLifeSpan` 收尾，远端靠 OnRep 对齐状态。
34. **门禁翻牌规则**：`!=NM_Standalone`（拦截）→`==NM_Client`；`==NM_Standalone`（准入）→`!=NM_Client`。监听服主机的 NetMode 是 `NM_ListenServer`——旧门禁把主机也关了（35 处/33 文件翻牌记录见 worklog §3.20）。存档写盘等明确单机语义的门保留。
35. **怪物离散动画**：怪类 `State` 枚举默认不复制——客人侧 `IsControlled/IsDead` 全判 false，攻击前摇/硬直/死亡动画整层缺失。修法：`State` 加 `ReplicatedUsing=OnRep_State`，OnRep 重放各怪 `SetState/EnterState`（表现内聚函数客户端重放安全）；受击镜像=复制 `HitReactions` 计数+硬直时长，客户端 OnRep 起手同款 `StartHitPresentation`，本地时钟走同一套 `UpdateReactionPresentation/FinishReaction`。

## 八、构建与取证

26. Live Coding 锁是引擎级全局；worktree 提交纪律=只显式路径 add，`Plugins/` 被 .gitignore 需 `git add -f`；日志硬件名只作线索，结论认实测。
27. 未打包 -game 姿态=`UnrealEditor.exe <proj> <map>?… -game`；双进程日志 `-log=A.log/-log=B.log` 分名。
28. 取证三板斧：**双端坐标探针**（服务端 2s 记 name/x/y/tick/mode/vel）、**RPC 对账打点**（send/_Implementation 配对）、**A/B 开关**（-MPNoHeartbeat 类）。自动化移动用 `-MPClientWalk`（必须走 AddMovementInput 真实通路+豁免物理键护栏）。
29. **PIE 多窗口不可作移动验收场地**（失焦节流→move-ack 断流）；正式验收=双 `-game` 进程或双机 LAN。

## 相关

- 计划与断点：`Docs/MultiplayerStrategyAndPlan20260930.md`、`Docs/MultiplayerWorkLog.md`（§3.13 重构总表）
- 新代码：`Source/FPSGAME/Multiplayer/`（PlayerState+WorldSubsystem）、`Movement/FPSCharacterMovementComponent`
- 插件：`FPSGAME-mp/Plugins/ColdSteelNet/`（NetGameMode/Connect/WorldSubsystem 桥接）
- 退役件：`trash/mp-channel-into-playerstate/`（旧 ChannelComponent，散列已记）
- 证据归档：`trash/movement-forensics-20261001/`
