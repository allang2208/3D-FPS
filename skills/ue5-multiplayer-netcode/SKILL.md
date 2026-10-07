---
name: ue5-multiplayer-netcode
description: UE5 原生复制联机开发（监听服务器起步）的工程套路与坑：SavedMove 压缩位传移动意图（含架枪）、PlayerState 玩家数据归属、服务端 rewind 命中校验与效果标志重建、WorldSubsystem 引导、RPC 载荷限制、远端身体表现上行消毒、玩家死亡复制与死亡相机、怪物序号+服务器钟一次性表现与音频门禁、门族服务器权威交互（FColdSteelDoorNetState+pawn 组件 RPC 枢纽）、相位化施法通道、PIE 假象与双进程取证。联机玩法改造、同步排查时使用。
---

# UE5 多人联机：架构地图、踩坑清单与常用套路

（FPSGAME 联机线沉淀：2026-10-02 成熟方案重构版；2026-10-06 同步表现上行/玩家死亡/门族/怪物音频/命中元数据）

## 〇、当前架构地图（改代码前先对上这张表）

| 职责 | 载体 | 位置 |
|------|------|------|
| 移动意图（冲刺/ADS/滑铲/架枪） | `FSavedMove_FPSCharacter` 压缩位 FLAG_Custom_0..3，与移动包同帧压缩→按序回放 | `FPSGAME/Movement/FPSCharacterMovementComponent` |
| 闪避位移（出招时数据未定，事后补） | `FRootMotionSource_FPSDodge` 重载 PostSave/PrepareForReplay | 同上（`ApplyDodgeDisplacement`） |
| 玩家持久数据/档案（服务端独有） | `AColdSteelPlayerState`（PlayerController 自带 Authority→Client RPC 通道） | `FPSGAME/Multiplayer/ColdSteelPlayerState` |
| MP 引导（PostLogin/Logout 挂钩、JSON 注册表） | `UColdSteelNetWorldSubsystem`（World 级挂点） | `Multiplayer/ColdSteelNetWorldSubsystem` |
| 命中权威（自报→校验→复算→执行→确认） | `ServerReportHit`→`ValidateHitReport`→`ComputeServerDamage`(影子档案复算+效果标志服务端重建)→`ForwardHit`→`ClientShotResult`；同挥目标组 `GuardAttackSerial` | `ColdSteelPlayerState.cpp`、`UFPSCombatHealthComponent::ForwardHit` |
| 滞延回放缓冲（客户端"在对方过去时间开枪"） | 怪物：`HitPoseHistory` 25Hz；玩家：`UFPSCombatHealthComponent::LagHistory` | `Monsters/HitPoseHistory.h` |
| 远端玩家身体（双向） | 上行：客户端 `ServerBodyTransition/Snapshot`→服务端 `AcceptBodyPresentation` 逐字段消毒→`ReportedPresentation`；下行：服务端 `SampleRemoteAuthorityState`(权威事实+<0.6s 表现叠加)→`ReplicatedState`+`ReplicatedWeapons/Outfit/Appearance/Reactions` | `Characters/FPSPlayerBody{Component,Network,Actions}.cpp` |
| 玩家死亡与死亡相机 | `UFPSCombatHealthComponent` 复制 `DeathStartedAt`(服务器钟)+`bDeathFromCrouch`；`ApplyPlayerDeath` 权威/OnRep 各端同跑；倒地轨 `FPSPlayerDeathMotion::State`；本机相机 `FPSPlayerBodyReactionCamera.cpp` | `Monsters/FPSCombatHealthComponent`、`Characters/FPSPlayerBody*` |
| 门族服务器权威交互 | `UFPSDoorPushComponent`（挂玩家 pawn 当 RPC 枢纽）+`FColdSteelDoorNetState`(一次权威过渡：From/To/Speed/StartedAt)；门/窗/滑门/旋转门/接触门/钥匙门/拖拽门/钥匙拾取 | `Movement/FPSDoorPushComponent`、`Building/ColdSteel*Door*` |
| 怪物离散表现与音频 | `State` 枚举 `ReplicatedUsing`+OnRep 重放表现函数；一次性提示=复制序号/服务器钟沿（不走 multicast）；循环声=本地组件由复制态驱动；专服跳过 | `Monsters/`（M07/M08/M09/M10/M14/M25/M27 铺开） |
| 连接预热（注册界面→进游戏早连服务器、GPU 焐图） | `UColdSteelNetConnectSubsystem`，`UColdSteelNetGameInstanceSubsystem` 常驻连接句柄 + `-MPConnect` 命令行 | `Plugins/ColdSteelNet/`（在库内；`Plugins/` 被 .gitignore，提交需 `git add -f`） |

## 一、移动同步（全部绕着 SavedMove 压缩位解决）

1. **自定义移动意图压缩进 `FSavedMove` 的 CompressedFlags**，不要走独立 RPC。当前位分配：`FLAG_Custom_0`=冲刺、`FLAG_Custom_1`=ADS、`FLAG_Custom_2`=滑铲、`FLAG_Custom_3`=架枪（`bWantsToMount`，阻挡移动语义）。`UpdateFromCompressedFlags`/`FSavedMove_FPSCharacter::SetMoveFor` 同一帧打包/解包，冲刺/ADS/滑铲/架枪各自回写 `MaxWalkSpeed` 与状态切换；滑铲的"释放"是"起停 flag 翻转"而非"位移量"。这些位也是服务端读远端"按键意图"的唯一可信口——`UFPSDoorPushComponent::ServerCanInteract` 的冲刺门就读远端 `Move->bWantsToSprint`。
2. **`CanCombineWith` 对所有自定义 flag 变化都说"不可合并"**——否则 flag 翻转会被压成一条 move，服务端看到的冲刺状态会错一拍。同理：方向键持续变化也不要让 `CanCombineWith` 拒绝合并，否则动作回来之前 W/A/S/D 在动画层里全部"卡住"。
3. **RootMotionSource 是 UE5"客户端位移补权"官方管道**（`FRootMotionSource_FPSDodge` 的 `PostSave`/`PrepareForReplay`/`Matches`/`UpdateStateFrom`/`SetTime/GetTime` 都是稳定 API——不要用 `Duration` 那种被 `ENGINE_FINAL` 焊死的私有字段）。闪避跑在预测窗口内，flag 与位移数据天然分离，`UpdateStateFrom` 是"事后把真实位移灌回客户端回放路径"的入口。
4. **同一段代码四端都能跑**（standalone、listen host、客户端、专用服务器），不要手写"if (host) / if (remote)"。判断入口是 `GetOwnerRole() == ROLE_Authority`（逻辑权威）+ `IsLocallyControlled()`（本机玩家），不是 `netmode == x`；`FLAG_JustPressed`/`FLAG_Pressed` 语义比 `IsSprinting()` 值对值准——CMC 重放里同一帧可能多次 evaluate，只判断"当前值"会漏按-释。
5. **"持续按住/松开"类意图不走 `Server` RPC**（比如切走枪、左右移、滚镜）：每帧 `UNPACK` 一份 CompressedFlags 的 snapshot 就够了，加一条 RPC 反而冗余。主角色的第三人称冲刺攻击动画也走本地检测+服务器镜像字段，远端看的是复制组件态。

## 二、玩家数据与持久档案

6. **玩家持久数据不放 GameInstance，不放 GameState，放 `AColdSteelPlayerState`**：它在 PlayerController 生命周期内出生、是复制 actor、天然有服务端 RPC；GameInstance 是"本地家底"，GameState 是"每人都可见"。M1 断点走 SkillColumn 占位 + SaveGameJson；M3 用 `ColdSteel` JsonPathRegistry。
7. **`UColdSteelSkillModel` 纯 UProperty 复制**：只带字段不带方法；`bAuthoritativeSchema`/`ShardHashes`/`PendingSends` 是同步层字段不是存档字段，存档写盘前由 `StripSyncFields` 剥离。分片上行：`ApplyLocalShot` 算出变化的 4KB shard → `SendProfileShard` 一条条 `ServerApplyProfileShard` → 服务端 `ServerApplyProfile` 重建 + `Snapshot` 广播给所有端。
8. **影子档案**（`bNetShadow=true` 的 `UColdSteelSkillModel`）：PlayerState 构造一份副本挂着 `ShadowModel`——服务端代码里 `Snapshot(..., GetNetShadowProfile())`/`BuildAttackContext`/`AmmoDamageMultiplier`/`EvaluateEnchantChance`/`MasteryEffect` 一律走影子；命中确认回执里客户端用 `DeltaXp` 回放同样增量到本地档案保持增长可见。影子档案还会经 `ApplyColdSteelProfile`→`Configure` 灌进服务端 pawn 上的 `CreateDefaultSubobject` 附魔/挂件组件（Zhenmo/Jingang/Dealer 等——`UFPSXxxComponent` 是跟随 Pawn 的子对象，不是只在本端）；组件反查 pawn 走 `UJingangRuneComponent::From(StatusModel)` 的 `RuntimePawn`。
9. **Tick 里的施法栏检查、投射物生成、命中表演**统一挂 `GetNetMode() == NM_Standalone`（只有 standalone 是"纯本机"）。M3 施法走相位化权威协议（见 §十）。

## 三、命中权威（MPTEST hit_path 八步排查法）

10. **客户端只报告几何**（`FColdSteelNetHitReport::AimOrigin/ImpactPoint/ImpactNormal/BoneName`）+ 武器 `InstanceId`/`Definition` + 客户端本地 `ClientShotMs`；**伤害、暴击、cap、弹药、目标落点全部由服务端影子档案重算**。token bucket (`TokenBudget=12`) 防突突；`ValidateHitReport` 八道门：非本玩家 PC→item 非持握或类型不配→几何 NaN→时间窗 250ms→目标脱 relevancy→不在历史缓冲→名义头节点排除（软腋保护）→rewind 几何校验。
11. **客户端申报的效果标志一律在服务端重建，不允许直接采信**：`bRisingDragonFinisher` 按*服务端物品* `ColdSteelModularSword::UsesRisingDragonFinisher` 算；`ToughnessDamageMultiplier` 由 `ColdSteelMelee::Evaluate(Declared,ShadowModel)` 复算（重击 `HeavyToughness`/连段终段 `ComboThirdToughness`）；`Dealer`/`Zhenmo` 附魔按服务端 `InstanceId` 查；`GuardAttackSerial`（同一挥击的目标分组号）+ `GuardSourceInstance`/`DealerSourceInstance`/`ZhenmoSourceInstance` 由服务端回填，客户端不传数值。
12. **AttackMeta 申报语义位**（`Report.AttackMeta`）：`&0x0F`=连段数、`0x10`=重击、`0x14`=上挑（独立等级走 `UppercutMultiplier`，双手剑射程上限 `ColdSteelMelee::UppercutReachCM`）、`0x20`=旋风技能面板、`0x40`=裂斩附魔缩放（`riftSlashDamageScale` 服务端同参）、`0x80`=快速近战面板；`0x20|0x80` 不吃韧性倍率；空手 `UnarmedPunch::AttackMeta`+空 Definition 走独立支路。枪：面板 × 汇聚（弹匣容量 clamp）× 服务端距离衰减（`WeaponDamageFalloff`）；弓：面板 × 拉弦比 clamp[0,1] × `AmmoDamageMultiplier`。
13. **时间戳不绝对同步没关系，统一用 `GetGameState()->GetServerWorldTimeSeconds()`**（不是 `GetWorld()->GetTimeSeconds()`，也不是 `GetServerWorldTimeSeconds()` 直接落本地时钟）。`ClientShotMs - Now ≤ 500ms` 这一道是最后兜底（杜绝"很久以前"一枪）。远端表现的身体组件、门、怪、死动画也都用同一个钟（`UFPSPlayerBodyComponent::ServerClock()`）——**复制"服务器钟起点+速率"，各端本地推进**，不复制连续量。
14. **回放缓冲**：玩家 `LagHistory`（25Hz，同 HitPoseHistory 套路）—— `bOnlyRelevantToOwner` 会切断远端玩家命中校验（属性刷新不到攻击者），治疗型 Buff 不能用它做传播手段。
15. **`bFiredRound` 端端分开**——枪械是"一发子弹一发 RPC"，投射物是"一工程一命中报告"。`Report.Rounds` 本身不可信：汇聚倍率由服务端按影子装备弹匣容量上界 clamp。
16. **`ClientShotResult` 确认**只在真实命中且扣血后才广播，里面塞 `DeltaXp`/`DeltaStamina`/`ShadowSnapshot`——Delta* 只是表现增量，真正的结算在服务端影子档案里。

## 四、GameMode 分层（不要在 GameMode 里写出生逻辑）

17. 项目有两个 GameMode：`AFPSGAMEGameMode`（本机/听服务器——单人、监听主机、PIE 的本机塔）+ `UColdSteelNetGameMode`（`AOnlineGameMode` 子类，MPTEST `-game` 走这条：MainMenu→Loading→MPTEST map 主入口）。**MP 出生点在 `AMultiplayerStart`**（替换默认 PlayerStart，跟单人出生点隔离）。听服务器虽然能开 MPTEST，但 PlayerState/影子档案仍需要 `AOnlineGameMode` 在；专用服务器直接走 OnlineGameMode。
18. `UColdSteelNetWorldSubsystem`（挂在 World 上，监听 `GameMode::OnPostLogin`/`OnLogout`/`OnGameModeInitialized`）做 MP 专属 PlayerState 注入（`ShadowModel`、`JsonPathRegistry` 注册表加载、`-MPTEST` 字符串识别）。**同一逻辑不可放 GameMode 里，也不可放 PlayerController**——GameMode 每 world 一份但只在服务端生成，WorldSubsystem 四端都有实例但只跑服务端逻辑（`GetNetMode()==NM_Client` 早退）。用 `GetNetMode()` 前对照§十的"单机/监听/专服/客机"四端语意。
19. **PIE 多窗口必须同 NetMode**：一个 `Listen Server` 窗口 + N 个 `Client` 窗口，不要"PIE standalone 两组"（本机独立 world 互相看不到对方 Pawn 投影，"能看到" 其实是 `UWorld::IsGameWorld()` 对单例的假阳性，§六把它写成旧坑不复述）。

## 五、传输层

20. **`bNetLoadOnClient=false`**：注册界面/主菜单界面不加载联网玩家 actor（防开场还没注册表就白屏）；**只在进入 MP 地图前 `bNetLoadOnClient=true`**。
21. **RPC 载荷不推整 Json**：`MirrorBlob`（64KB 软上限）改成 `bAuthoritativeSchema` 3 表（`TermId/Hash/Value`）分 shard 上行/下行——见 §二。任何"塞个大 TMap 到 RPC"的需求都改成"分块+hash 对账"。

## 六、远端玩家形象（双向通道 + 消毒）

22. **上行通道**：本地客户端 `SampleLocalState`→动作沿 `ServerBodyTransition`（reliable）+80ms `ServerBodySnapshot`（unreliable）上行到自家 pawn 的 `UFPSPlayerBodyComponent`（pawn 属本客户端，组件能发 Server RPC）。服务端 `AcceptBodyPresentation` **逐字段消毒**：枚举越界拒、NaN/Inf 拒、时长 >60s 钳、时间戳夹到 `[Now-60,Now]`、单位区间钳、支点离 pawn >500cm 拒、序列号单调递增防乱序。
23. **下行组装**：服务端 10Hz `SampleRemoteAuthorityState` 只采表现字段（`Contacts/Action/Variant/ActionStartedAt/Duration/弓态/手部进度/AimYaw/WhirlwindTurns`），**武器/族/瞄准/位移标志与一切玩法值不采**；客户端报的表现字段 0.6s 不新鲜即回落纯权威采样；结果写 `ReplicatedState`→三端 `OnRep_BodyState`→`AdvanceBodyPresentation` 用服务器钟本地推进。远端看到的"喝药/上弓/手位"全走这条。
24. **服务器钟是唯一时域**：`UFPSPlayerBodyComponent::ServerClock()=GameState->GetServerWorldTimeSeconds()`（无 GameState 回落世界钟）。身体表现、死亡（`DeathStartedAt`）、门（`NetSwing.StartedAt`）、怪（`AttackStartedAt`/`PouncePhaseStartedAt`/`ThreatSerial`）、`LastValidatedShotAt` 全在同一域——远端可 `ServerClock()-StartedAt` 推"已播多久"。`FFPSBodyState.ActionStartedAt/Duration` 与 `FFPSRemoteBodyAnim.WhirlwindTurns` 都用这个钟。
25. **消耗品/技能仍走本地通道 + 表现上行**：`UFPSPotionUseComponent::TryBegin` 只在 `IsLocallyControlled` 本机触发（结算走档案分片上行→服务端影子收敛，同 M2 口径）；远端玩家看到你喝药全靠 `EFPSBodyAction::Consume` 上行（`ActionStartedAt=ServerClock()-Age` 回填已进行时间）。武器交接给消耗品、强制双手这类"临时表现"同理——`HandleConsumableUse`/`ForceWeaponTransition` 改的是本地 `DisplayState`，上行时把 Action/Hands 一并汇报。
26. **`AColdSteelPlayerState::ServerReportBodyAction`→`Body->ServerRecordAction`** 是 PlayerState 上已接线的备用离散动作端点（当前无调用方）；离散动作由表现上行覆盖。

## 七、玩家死亡与死亡相机

27. **`UFPSCombatHealthComponent` 复制 `DeathStartedAt`（服务器钟）+ `bDeathFromCrouch`（并滑铲/站立倒地轨分支）**，判死 `ForceNetUpdate`；`ApplyPlayerDeath()` 在权威端与 `OnRep_Health` 各端统一跑：`InterruptActionsForPriority`（不重新灌档案快照——陈旧快照不许复活已确认的死亡）→`DisableInput`→停走+`DisableMovement`→`SetActorTickEnabled(false)`。**Pawn 停 tick 但 body/mesh/相机组件独立 tick**，倒地表现继续。重生计时 `FPSPlayerDeathMotion::RespawnSeconds`。
28. **远端身体**：`FPSPlayerDeathMotion::State` 把 `Action=Dead`/`Variant(Crouched|Standing)`/`StartedAt/Duration` 写进复制体，各端按同一条倒地轨演算（`DeathMotion`**不**当普通"另一段动画"—它是独立时域轨道）。
29. **死亡相机（仅 `IsLocallyControlled` 本机）**：`ApplyDeathCameraView` 按 `death_presentation` JSON 关键帧轨道插值 + `SetManualCameraFade` 黑场 + 相机碰撞 sweep/落地夹高；`ReleaseDeathCamera` 只归还本次 fade——`PlayerCameraManager` 跨 pawn 存活，旧 pawn 销毁不能把新 pawn 弄黑。相机配置走 `FPSPlayerDeathConfig`。退出世界把视角放 `FPSPlayerBodyComponent` 的 `Reaction` 字段，不写相机管理器全局态。

## 八、怪物复制模板（对一切"离散表现"统一套路）

30. **State 枚举复制 + OnRep 重放表现**：`ReplicatedUsing=OnRep_State` 复制 `EMonsterState`；OnRep 里跑原 `SetState` 同一个表现内聚函数（动画/材质/光照三件套），客户端不重写一遍。受击镜像=复制 `HitReactions` 计数（`FMonsterHitReaction{IsInterrupt,AttackType,ReactDuration}`）——对远端只播"硬直了多久、下鞭子打断谁"，不写逻辑。
31. **一次性提示标准件=复制序号/服务器钟沿，不走 multicast**：服务端在 SetState/出招同一调用点放表现（监听服主机靠这条拿到本端演出），客户端靠 OnRep/序号沿重放。案例：`AttackSequence+AttackStartedAt`（M27，OnRep `SetCombatTime(ServerClock()-StartedAt)` 中途进招也对时）、`ThreatSerial`（M10）、`AudioAttackKind`/`AudioMagicReleased`（M07 凝聚/释放路由）、`PouncePhase+StartedAt`（M27 扑击）、`bCloaked`+`ForceNetUpdate`（M27）、组件级复制结构 `FM25BiteState`/`CastState`（`UFPSM25BiteComponent::SetIsReplicatedByDefault(true)`+组件自己 `GetLifetimeReplicatedProps`）。
32. **音频分两类**：循环声=每端本地 `UAudioComponent`（`bAutoActivate=false`+自写 `AttenuationSettings`/`bAllowSpatialization`/`bOverrideAttenuation`)由复制态驱动（`UpdateLoopAudio` 读 `State`/速度/`Dead`）；单发=`UGameplayStatics::PlaySoundAtLocation`+临时 `USoundAttenuation`。循环声不是"服务端播给所有人听"——是"各端各自听自己世界里的同一状态"。
33. **奖励与影射归属走服务端影子档案**，不要用"本地 controller 存在与否"做门禁（M25 客机不吐撕咬奖励即此坑）。**`NM_DedicatedServer` 是所有音频/表现的总闸**（专服无声卡/无渲染），与 `NM_Client`/`NM_Standalone` 门禁并列记；怪物 `AttackCooldowns`/`CloakUntil`/`AttackStartedAt` 全部用服务器钟。

## 九、世界交互：门族权威（第一个"非玩家 Pawn"的复制交互对象）

34. **`FColdSteelDoorNetState{bOpen,From,To,Direction,Speed,StartedAt}`**：服务端 `PublishSwing` 一次权威开合（写钟+速度），OnRep 由 `Now-StartedAt` 按 `Speed` 重算 `CurrentAngle`——连续过渡零逐帧复制、迟到加入自动补齐；`NetSurface/NetScale/NetLeaf`（OnRep_Setup）带运行时材质/尺寸/门扇配置。单门/双开窗/滑动门/旋转门共用同一结构（滑动门 `From/To` 存偏移 cm、旋转门转 120°）。
35. **门 actor 是服务端的，客户端对它没有 RPC 权**——上行通道挂在自家 pawn 的 `UFPSDoorPushComponent`：E 键 `ServerToggleDoor`（拖拽门松手→`ServerReleaseDoor` 当前角冻结）、冲刺撞门 `ServerBeginPush|ContactPush|CancelPush` 三段（`AttackSequence` 复用每推次）+`ClientPushResult(seq,false)` 回执让客户端撤本地起手+`MulticastPushImpact`（撞门声/动作归组播，服务端落 `S`+1）。`ServerCanInteract` 服务端全链复验：同世界/未脱筹/`IsNativeDoor`/玩家存活/动作占用/`LOS 首挡=目标门`/朝向阈值/**冲刺意图=远端 `Move->bWantsToSprint`**；0.15-0.2s 请求节流 + 序号对账。排查：`fps.DoorPush.Debug` cvar 沿闸门链逐步输出拒绝原因；**尝试/拒绝类日志不走 cvar**（触发起手/BeginPush 失败/服务端拒绝含 `[谓词分解]`/节流/接触复核/开门失败/回执取消/E 两端拒绝全无条件打——2026-10-07 实测整轮零日志才改，cvar 不跨会话持久）。`左手施法占用[...]` 后缀带 `AFPSGAMECharacter::DescribeLeftHandBusy` 逐项分解，用于指认"客户端 CanStart 过、服务端复核拒"的两端分歧。**已踩过的自拒坑**：三个左手术语（`IsLeftHandBusyForCast`/`IsCastBlockingLeftHandAction`/`IsSpellGestureBlocking`）首项都是 `IsDoorPushActive()`——本机/主机同实例上 `BeginPush` 先置 `bActive` 再发 RPC，服务端复核读到自己刚起的这次推就恒拒（毫秒级零时延回执是特征）；门推门禁统一传 `bIgnoreDoorPush=true` 跳过该自指项，并发由 `bActive` 早退+`ServerDoor` 节流分管（2026-10-07 实测 `[DoorPush]` 分解指认后修复）。**撞门 `LastDoor` 锁存是冷却式而非永久**：触发点先武装 `SameDoorRetryAt=now+.55s`（兜底 `BeginPush` 姿态捕获失败），服务端拒收（占用/LOS）经 `ClientPushResult→Cancel` 在回执时刻再武装一次（必须大于服务端 .2s 节流窗）——冷却内同门探测跳过、过后自动重试。旧写法一次拒绝就把该门锁死到松开 Shift 为止，2026-10-07 修复。**客机 `TraceTarget` 白名单直接复用 `IsNativeDoor`**（旧写法只认 `AColdSteelDoor`/`AColdSteelWindow`，滑动门/旋转门在客机 E 失效，2026-10-07 修复）——新增门子类只需登记 `IsNativeDoor` 一处。
36. **子类语义**：`ContactDoor` 服务端 overlap 只对玩家（怪物不撞门）；`KeyDoor` `bUnlocked` 复制 + 会话级 `DoorKeys` TSet 只在权威端发放（`AColdSteelKeyPickup` overlap 只挂权威→`Destroy()` 复制消失）；`DragDoor` 按住摆、松开重发 `NetSwing` 冻结；`RevolvingDoor` 服务端触发盒旋转；`SlidingDoor` 用 `NetSwing` 存滑动偏移。统一口径：**两侧摆动空间皆堵→拒绝开门（不穿墙）**，`OpenDoorFrom` 返回 `false` 让 `ClientPushResult` 撤表现。**`IsSwingBlocked` 的豁免集是假阻塞高发区**：门板容身壳（门板平面方向放宽 ~10cm 的贴合构件——门套/侧梃/过梁/嵌着门板的墙壳分段；厚度方向不放宽，正面障碍物仍算）+ 门族门板互免（双开门子叶铰链各在外缘，互不死锁）。门洞只比门板宽几厘米，铰链侧角尖摆扫会擦进侧梃凸包——2026-10-07 实测 PowerTheme 整屋壳的侧梃 UCX 距门板铰链边仅 ~3cm，旧版"任一重叠即挡"让门永远拒开。阻挡者会写日志（`摆动被挡：方向/进度/阻挡=Actor:Component`），滑动门 `IsSlideBlocked` 同口径输出。
37. **`DoorKeys` 是 `AFPSGAMECharacter` 首个复制成员**（`DOREPLIFETIME_CONDITION`+`COND_OwnerOnly`，`GetLifetimeReplicatedProps` 落 `FPSGAMECharacterProfile.cpp`）：服务端 `GrantDoorKey` 写权威集合，持有者客机镜像后交互提示"有钥匙"分支才读得到——此前客机恒显"需要钥匙"（功能正常仅文案偏差，2026-10-06 修复）。教训：会话态放角色上的字段若客户端要读，记得给复制位；`COND_OwnerOnly` 意味着**其他端看不到别人的钥匙环**，别拿它做跨玩家机制。

## 十、法术施法通道（施法/弓/技能型武器）

38. **`AColdSteelPlayerState` 是唯一的施法仲裁者**，协议 = `ClientRequestCast`→服务端四道门（牢笼沉默/法力/冷却/材料）→`ServerCastBegin`（权威施法者=玩家 Pawn 上 `UFPSPotionUseComponent`/`UFPSCombatHealthComponent` 之外的 `Cooldowns`/`SpellPower`/`Status` 三组件，Pawn 自身只带表现）→`ServerCastRelease`→`ClientCastAck`/`ClientCastFail` 客户端回执。M3 实装的法术列表/技能树/箭矢三态/投射物都由这套接管。
39. 施法组件模板：玩家侧 `UFPSPotionUseComponent`、`UFPSCombatHealthComponent`；怪物侧 `UFPSCombatHealthComponent`；**法术的 Stat/资源消耗统一 `UColdSteelStatusModel`**（不是 `SkillModel`——冷却/法力是"状态"不是"成长"）；**`AuthorityModel` 桥接**：`UColdSteelStatusModel::AuthorityModel` 指向服务端真相，本地 Model 只是视图副本。
40. **法术 actor 复制**：`AColdSteelSpell`（`bReplicates=true`，`ReplicatedUsing`+`SCENEreplicatedmovement`）挂 `UMagicEffectComponent`——`OnFire/OnHit` 全用 `DispatchableEvents`/`ParamClamps`；复制字段 `CasterPawn`/`ProjectileMovement`/`SphereCollision`/`Activated`(OnRep)/`SpellInstance`。**`ReplicatedMovement` 的精确度砍到 `REPMOVE_WholeRound`**（省带宽）。
41. **`GetNetMode` 门禁统一翻成四端语义**：`NM_Standalone`（纯本地）/`NM_ListenServer`（host 伪客户端）/`NM_DedicatedServer`/`NM_Client`。M3 把旧代码里所有 `GetNetMode()!=NM_Standalone` 一刀切改成按功能区分：本机表现（摄像机动画/武器 pose/手部 VFX）→`NM_Client`；施法拦截提示（法力不足本地 UI）→`NM_Client`；服务端只在权威端跑的逻辑→`NM_Standalone`/`NM_ListenServer` 或 `GetOwnerRole()==ROLE_Authority`；**音频/视觉表现→`NM_DedicatedServer` 早退**。投石问路：新逻辑先想"这件事谁说了算"。
42. 新法术/新通道法术三件套：`SkillId` 注册 + `ExecuteCastRequest` 分支 + 影子侧 `BeginXxxCast`；**字段型约束两侧都要查**（如 `bRequiresStaff` 在本地 `ServiceQueue` 预检与服务端 `G->IsStaff(Item->Definition)` 分支都要有，否则主机/客机不对称）。

## 十一、客户端加入链与杂项坑

43. **占位图与真实玩家 actor 两套**：`AOnlineGameMode` 看到 net pawn 先给 `AClippyPlaceholderPawn`（无 Pawn 时先给"纸片人"），再接 `UColdSteelNetWorldSubsystem` 的 `HandlePostLogin` 切换真体。**PIE 编辑器那个出生点不是 net pawn**，选人界面才走 placeholder（M1 过的坑）。
44. **焐图/预热**：`UColdSteelNetConnectSubsystem` 的 `OnMapLoad` 在主菜单加载完之前把 GPU 资源焐一遍（M2 过的坑）；从 `Plugins/ColdSteelNet`（在库内）加载而非 `FPSGAME-mp` worktree。
45. **单机过场遮罩在联网客户端永不完成**：`EOnFadeDone` 的 `OnLoadingScreenComplete` 只在 standalone 有；联网端过场由 `UFPSGameInstanceSubsystem::OnPreLoadMap` 接续（M2 过的坑）。同理 `WIP` 死亡画面、HUD 蓝图：`WBP_DeathScreen` 只在 standalone 起 widget，`Client` 端从 `OnRep_Health` 本地起；HUD 要自己认 `NM_Client` 画跨客机 UI。
46. **重新登录回出生点**：`AColdSteelPlayerState::ReceivedPlayerController`（在服务端 PlayerState 拿 PlayerController→`PC->SetPawn`）比 `HandleStartingNewPlayer` 干净——后者对"断线重连"每来一次重选一次出生点（M1 过的坑）。
47. **客户端"断流冻结"不是网络丢包**：`FRepMovement` 的 `SimulatedVelocity` 只驱动动画不驱动物理（`bReplicateMovement` 关掉模拟位移）。远端角色停止 = 服务端把 Pawn `bOnlyRelevantToOwner` 收权后 net update 停止=收"无中生有"的末次状态（M1 过的坑）。
48. **鼠标焦点外僵尸按键**：PIE 里点窗口外再点回来，WASD 会"卡住"——编辑器窗口失焦时 `FSlateApplication` 没发 `OnKeyUp`（M1 过的坑）；`FLAG_Pressed`/`FLAG_JustPressed` 里插 `StuckKeys` 清理，别拿 `PresssedKeys` 列表当真值。
49. **服务端需要感知的"客户端在做什么"只能从三处推断**：SavedMove 压缩位、PlayerState/组件上行 RPC、复制属性——客户端组件的本地成员（`bActive`、计时器、表现句柄）服务端看不到。新动作先想清楚走哪条，别让"本地起效"被误当"已同步"。

## 十二、构建与取证

50. **Live Coding 编译没过的原因是 debug**（`DebugGame Editor` 编译需要 `bDebugBuildsActuallyUseDebugCRT=false`），不是代码问题；`bUseUnityBuild=true`、`bLegacyPublicIncludePaths=false` 是老的、已不需要。
51. **未打包 `-game` 测试姿势**：`UnrealEditor.exe <uproject> <map>?Listen -game -log`；不要 `CmdKey keyevent=112`（它对虚拟键盘码过敏，实际的是 `113`）。运行时单实例 console 执行 `open 127.0.0.1`；`WaitForPendingNotifications` 在 `LoadingScreen` 还没被引擎生成就 return 0（不是 bug 是时序）。
52. **取证三板斧**：`MPTEST` 打点家族（`shot_*`/`cast_*`/`door_*`/`hit_*`/`login_*`）+ `fps.DoorPush.Debug` cvar（门闸门链拒绝原因）+ `-LogCmds="LogNetPlayerMovement Verbose LogNetTraffic Verbose"`（`Packet loss/AddedPackets/Retransmit` 全在这条）。`MPTEST_DEBUG_WEAPON` 类 cvar 走 GEngine 字符串；**双进程日志务必按 `HH.MM.SS` 切**（`grep` 冒号会被看作模式，时区差会被当"少 8 小时"）。查找 `bNetShadow`/`InstanceId`/`WeaponLoot` 的归属：`GetMangledName`+`GetUniqueID` 是稳定键（`WeaponInstanceId` 是短例，`WeaponLoot` 找残件回记）。
53. **PIE 多窗口必须同 NetMode**：`PIE` 的 `Listen Server` + `Client` 组合（不是"两组 standalone"）；**`PIE_SetWorld` 里改 `WorldOrigin`**（否则双世界 Actor 坐标撞车）；`NumPlayers=2`/`NetMode=ListenServer`/`bRunDedicatedServer` 只在编辑器 ini 里配，运行时别动。

## 十三、近战附魔增益与表现同步（苍龙案例，2026-10-07）

54. **符文剑执行器在 `NM_Client` 上整体不 Tick**（`URuneSwordComponent::BeginPlay` 既有限制）：联机时目前只有主机能用剑技。该剑组件上的远端表现不能指望它自己的 Tick，要由**身体组件**（`UFPSPlayerBodyComponent`，所有机器都在跑）在远端分支里调用；在客户端开放剑技、改为服务端裁决，需要单独立项。
55. **客户端临时增益要申报，数值由服务端复原**：服务端按影子档案重算近战伤害，看不到客户端独有的激活窗口（例如苍龙 30 秒）。做法：`ForwardHit` 用 `FColdSteelNetHitReport.Flags` 的空闲位（苍龙用 bit7）申报；`ServerReportHit` 核对申报的物品确实带该附魔后，用**服务端的附魔数值和影子属性**重建 `Shot` 字段（物理倍率、追加魔法），之后照常走 `ApplySkillWeaponHit`。只信任“是否处于激活”这一位，不信任任何数值。
56. **转发的命中在本地返回 0**：`ColdSteelSkills::ApplyHit` 在非权威端直接转发并返回 0，凡是依赖本地 `Applied>0` 的副作用（蓄能、计数）在远端客户端永远不会发生。改为挂在 `ClientConfirmHit` 回执上（本地 → 服务端裁决 → 回执里的 Applied／bKilled），每次攻击只计一次的去重放在接收端。
57. **长距离近战判定的 `TraceStart`**：`ValidateHitReport` 对非投射物命中要求 `|AimOrigin − 射手位置| ≤ 600 cm`，而 `ForwardHit` 用 `Hit.TraceStart` 作为 AimOrigin。沿一条长线分段扫掠时，远段的起点离玩家十几米，会被判为“起点漂移”拒收。这类命中要把 `TraceStart` 改写为视点（`TraceEnd` 改为命中点），LOS 与回溯检查照常。专用技能的距离上限（例如上挑 ×1.25）需要按附魔放宽时，同样只按服务端看到的物品放宽。
58. **纯表现状态搭身体同步**：在 `FFPSBodyState` 上加 `UPROPERTY()` 表现字段，拥有端在 `SampleLocalState` 里采样（**不要放在“持剑”分支里**，否则收剑或死亡后的消散传不出去）；`IsTransition` 比较标志位，变化时立即作为边沿上报；`AcceptBodyPresentation` 做范围清洗；`SampleRemoteAuthorityState` 在租期内复制。时间用源动作秒数（动作长度 × `ActionProgress`）和服务端时钟传，远端在自己的时钟上重建。远端副本对本机可见、被几何体正常遮挡，镜头震动和 HUD 只给拥有者。

## 相关

- 联机计划与断点：`Docs/MultiplayerStrategyAndPlan20260930.md`、`Docs/MultiplayerWorkLog.md`（活日志，§3.x 是逐节里程碑，§3.21 截至 2026-10-03 收口；门族/死亡/表现上行等工作在日志之后，以本文为准）。
- 新代码：`Source/FPSGAME/Multiplayer/`（`ColdSteelPlayerState`/`ColdSteelNetWorldSubsystem`）、`Characters/FPSPlayerBody{Component,Network,Actions,Death,ReactionCamera}.cpp`、`Movement/FPSDoorPushComponent`、`Building/ColdSteel*Door*`+`ColdSteelKeyPickup`、`Monsters/`（M07/M08/M09/M10/M14/M25/M27 的 State/序列号/音频组件）。
- 联机插件：`Plugins/ColdSteelNet/`（NetGameMode/ConnectSubsystem/WorldSubsystem 桥接；**`Plugins/` 被 .gitignore——改动要显式 `git add -f`**）。已退役：`FPSGAME-mp` worktree、`FPSGAMEEditor.Target.cs` 中对 MPTEST 单独源码组的旧引用、`EngineMovement` 中 FLAG_Custom_0 的写旧写法。
- 证据归档：`Docs/MultiplayerWorkLog.md` §4 的双进程冒险命令模板；任何新问题先跑一遍 `-MPTEST` + `MPTEST cast_*` + `MPTEST door_*` 打点确认服务端权威到底落没落。
