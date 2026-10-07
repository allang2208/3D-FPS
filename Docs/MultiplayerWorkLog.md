# 联机开发工作日志（断点续接指南）

> 本文件是联机系统开发的**活文档**：任何人接手，从「当前状态」读起，按「下一步」继续。
> 策略与总体计划见 [MultiplayerStrategyAndPlan20260930.md](MultiplayerStrategyAndPlan20260930.md)（M0-M6 里程碑、审计证据、架构决策）。
> 规则：每完成一个动作就更新本文件；记录"做了什么/证据在哪/下一个动作"，宁细勿略。

---

## 0. 环境坐标（接手前先读）

| 项 | 值 |
|---|---|
| 主仓 | `D:\FPS3D\FPSGAME`（git，main 分支，主线并行会话在飞，**不要动**） |
| 联机 worktree | `D:\FPS3D\FPSGAME-mp`（分支 `feature/multiplayer`，基点 main@da91c6d6） |
| 引擎 | `E:\Program Files (x86)\UE_5.8`（EngineAssociation=5.8） |
| 构建命令 | `& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development "-Project=<worktree>/FPSGAME.uproject"` |
| 构建前置 | **必须**先查 UBT/cl.exe 进程（错峰三条，见主仓 WORKFLOW.md「构建串行化」节）；引擎级单实例互斥 |
| 冒烟测试 | 双 `-game -Windowed` 进程（**禁用 -RenderOffscreen**，2026-09-18 起约 15s 崩溃）；日志用 `-log=MPHost.log` / `-log=MPClient.log` 区分，位置 `<worktree>/Saved/Logs/` |
| Git Bash 坑 | URL 里 `/Game/...` 要 `MSYS_NO_PATHCONV=1` 前缀，否则前导斜杠被转义 |
| worktree 拆除坑 | 先 `rmdir` 断 junction（DDC 等）再 `git worktree remove`（既有教训） |

## 1. 当前状态（最后更新：2026-10-02 午后，**联机已接入主仓**，见 §3.16）

- **架构态**：四条结构问题全部按成熟方案落地——SavedMove 压缩位传 sprint/ADS/滑铲、PlayerState 数据归属（OwnerOnly 镜像+两级判脏分片上行+影子档案）、服务端复算命中+rewind 几何校验、WorldSubsystem 引导与地图 GameMode 解耦、闪避经 SavedRootMotion 上联机可用。旧 ChannelComponent 退役至 `trash/mp-channel-into-playerstate/`。
- **冒烟实测结论**（§3.14）：move-flag/影子档案/命中复算/回执/血量 OnRep/上传瘦身全部在 -game 双进程下实证通过；客人移动撞墙停是地图几何非回归。**人工项未覆盖**：ADS/滑铲/闪避手感、远端形象可视确认、双人互打（rewind 对移动目标的实测）、丘陵图 GameMode 覆盖场景。
- **⏳ 待办**：①用户人工验收上述未覆盖项；②验证毒蛆毒液崩溃修复后重跑 90s+ 会话确认稳定；③branch 首个提交（显式路径 add，见 §worktree 纪律）。
- 硬件误判教训：日志 GPU 名（GTX 750 Ti）是用户改的设备名（实际 3080 Ti）；磁盘"慢"也为测法假象（枚举混入计时，精确测 348MB/198ms）。**环境结论只认实测**。
- M1-M3 自动化全绿；主仓闪退修复在并行会话 WIP 文件内随其发布；分支 22 提交待合并（接入窗口=主线 WIP 落盘静默期）。

### ⚠️ worktree 特殊构造（接手必读）### ⚠️ worktree 特殊构造（接手必读）### ⚠️ worktree 特殊构造（接手必读）### ⚠️ worktree 特殊构造（接手必读）### ⚠️ worktree 特殊构造（接手必读）### ⚠️ worktree 特殊构造（接手必读）

主仓 `.gitignore:83` 排除了整个 `/Content/*`（81GB 重资产不在 git 里，只 44 个 JSON 强跟踪）。因此 worktree 采用**混合构造**：
- `Source/ Config/ Docs/` 等 = HEAD 检出 + **主仓工作区覆盖层**（`Tools/mp_overlay_sync.py` 同步，原因见 §5 坑#3）；
- `Content/`、`DerivedDataCache/`、`Plugins/AutoFootstep/`、`Plugins/VoxelFree/`、`Source/ThirdParty/Blast/Lib/` = **junction 指回主仓**（资产/预编译件共享，并发安全）；
- **git 纪律**：在 worktree 提交时**严禁 `git add -A`**（会把 junction 造成的"已删除"和主仓 WIP 覆盖层一起提交）；只 `git add Plugins/ColdSteelNet Tools/mp_overlay_sync.py Config/DefaultGame.ini Docs/` 等自己名下的显式路径；
- 拆除 worktree 前先 `rmdir` 掉全部 junction 再 `git worktree remove`。

### 分支提交状态
- `feature/multiplayer`（基点 main@da91c6d6）**尚未做任何提交**——所有产物还在工作区。建议冒烟通过后做首个提交（只含 Plugins/ColdSteelNet + Tools/mp_overlay_sync.py + Config/DefaultGame.ini 的 shader 覆盖 + Docs 三件）。

## 2. 时间线

### 2026-09-30（M1 启动：隔离环境 + 插件骨架 + 基线冒烟）

- [x] 计划+审计定稿（三路审计结论全部带 file:line 进计划文档附录）
- [x] worktree 建立：`git worktree add D:/FPS3D/FPSGAME-mp -b feature/multiplayer main`（基点 da91c6d6）+ Content/DDC junction（原因见上 ⚠️）
- [x] ColdSteelNet 插件骨架：
  - `Plugins/ColdSteelNet/ColdSteelNet.uplugin`（Runtime 模块，依赖 FPSGAME 主模块）
  - `AFPSNetGameMode : AGameMode`——出生点会话占用表（重生复用原点/断线释放/满员轮转错开）、PostLogin/Logout 的 MPTEST 日志行（冒烟断言锚点）、`bUseSeamlessTravel=true`（M4 前置）、MaxPlayers=4
  - 启用方式=URL 覆盖：`?game=/Script/ColdSteelNet.FPSNetGameMode`（**不改任何 ini**，主线零接触）
  - 有意不做的：传送门安装/天气补种（AFPSGAMEGameMode 的单机向逻辑，M4 再多人化）
- [x] Game 目标编译 **Succeeded**（16:41，352MB）。排障链：缺插件(junction AutoFootstep/VoxelFree)→缺 FPSBlast 预编译库(junction Blast/Lib)→HEAD 不可编(§5 坑#2/#3，覆盖层同步 529 文件+清 Intermediate)→插件自身三处编译错(APlayerStart 前置声明/ChoosePlayerStart_Implementation/公共包含路径)→过。
- [x] 冒烟第一轮失败→根因链两连：引擎 `BaseGame.ini:116 bShareMaterialShaderCode=True`（09-08 遗留）+ 全机无 `Engine/GlobalShaderCache-PCD3D_SM6.bin` ⇒ **裸 FPSGAME.exe 未打包形态在本机根本跑不起来**（=主线"-game 15 秒崩"悬案的解剖，§5 坑#5/#6/#7）。worktree 已加项目级 False 覆盖。
- [ ] FPSGAMEEditor 目标编译（进行中，双进程冒烟的前置）
- [ ] 双进程基线冒烟 + 证据采集（改用 UnrealEditor.exe -game 形态，§4）

### 基线冒烟的预期结果判读（先写好再跑，防止误读）

- **应当通**：客户端加入成功、两端 pawn 互见（ACharacter 移动引擎自带）、客人能看到主机的第三身身体/装备（主机是 locally controlled→身体组件在服务端采样写复制字段）。
- **预期不通（正是后续 M1/M2 要修的，出现=符合预期不是事故）**：
  - 主机看不到客人的身体/装备（复制字段只有本地采样路径，服务端喂料 `SetAuthoritativeState` 是 M1 下一步）；
  - 客人侧 hub 图无天气（FPSWeatherManager 服务端 spawn 不复制）；
  - 若客人进程崩在角色 BeginPlay（`FPSGAMECharacter.cpp:349-360` 对 Controller 直写输入模式、`:339` AttachPawn 抢档案）→ 属已知坑，本地门禁修复项。
- 日志锚点：`grep -E "MPTEST|Join succeeded|Possess" Saved/Logs/MPHost.log MPClient.log`。

## 3.19 主界面 + 联机终端菜单（2026-10-02 傍晚，FPSGAMEEditor 编译通过）

**设计来源**：原项目 `E:\无尽轮回\...\game-dev` 的 `menu-layer.js` 主界面（接入终端式玻璃面板：eyebrow/大标题/副题/版本/主键/次级双格/状态行/info 卡），规划文档 `Docs/UI/main-menu-plan-20261002.md`（UI-WORKFLOW 流程：先规划后实现）。

**实现**：`TransitLoadingSubsystem` 的启动弹层原地扩成五页菜单（`FStartupLoadingView` 加 `Page` 页码状态，`SWidgetSwitcher` 切换，`SStartupMenuRoot` 吃 Esc=返回主页）：
- 主页：无尽轮回标题 + [开始游戏 浅色主键] + [多人游戏] + [设置] + [操作说明|退出游戏] 双格 + 状态行 + 快捷操作 info 卡
- 进入方式：原"快速测试/完整预加载"两档原样保留（`RequestedMode`→`ChooseLoadingMode` 链路不动）
- 联机终端：昵称输入 + [创建房间（主机）`OpenLevel(当前图,"listen?Name=…")`] + 地址框 + [连接 `OpenLevel(ip,"Name=…")`] + 最近连接（config，点击即连，上限4）+ 状态行
- 操作说明：真实键位表（DefaultInput.ini 扒的）；设置：预加载档位显示+占位
- 退出：KismetSystemLibrary::QuitGame
- 视觉按原版+冷钢规则落地：原版 `assets/ui/start-screen-background.png`（2048×1536）落到 `Content/UI/MainMenu/`，`FSlateDynamicImageBrush` 直读散文件（与 TransitLoading 同机制）；overlay 分层=#080d18 底 + `SScaleBox ScaleToFill`（对齐 center bottom，对应原 CSS `background-size:cover;position:center bottom`）+ rgba(4,8,18,.30) 暗化层；**主页按原版无面板**——eyebrow/标题/版本 + 300px 居中按钮列 + 状态行 + info 卡直接压图上；子页面（进入方式/联机终端/键位/设置）统一玻璃面板+ScrollBox 包裹。全部字体走 `TextFont`/`NumberFont`（Noto Sans SC / JetBrains Mono），颜色全 token。

**数据口径**：昵称→`?Name=` URL option（引擎 InitPlayerState/InitNewPlayer 落 PlayerState→`BuildGuestSlotName` 槽位，兼做档案 key）；`FPSGAME.Menu.Nick/RecentHosts` 存 GGameUserSettingsIni；P2P 直连形态=监听服 `?listen` 重载当前图，预留 Steam/OSS 会话层扩展位。

**验证**：`Build.bat FPSGAMEEditor` Succeeded（UnrealEditor-FPSGAME.dll 重链）。运行时联调点（未测，留用户）：开房后 bStartupChosen 分支不再弹菜单、加入方 travel 到主机图、昵称落槽、Esc 子页返回主页。

## 3.20 联机完善批次：失败回退 / 本机IP / 门禁翻牌 / 怪物动画复制（2026-10-02，编译通过，未实测）

**1. 连接失败回退主菜单**：`GEngine->OnNetworkFailure()/OnTravelFailure()` 绑定（lambda→`OnNetFailure`，World 归 GameInstance 过滤）→ `bStartupChosen=false` + `PendingMenuStatus` 存原因；`Tick` 里新增兜底轮询（`!bStartupChosen&&!StartupOverlay&&NM_Standalone`→重弹菜单）；`ShowStartupMenu` 把 pending 状态播种到状态行。此前客人 `open ip` 失败后回默认图就再无菜单入口。

**2. 联机页本机地址**：`Sockets` 模块入依赖，`GetLocalAdapterAddresses` 过滤 IPv4 非 loopback/链路本地地址，联机页在"创建房间"下显示 `本机地址：x.x.x.x:7777`（房主报地址给好友用）。`Content/UI/MainMenu/...` 同时加进 `RuntimeDependencies`（散 PNG 打包清单，同 TransitLoading 条款）。

**3. `NM_Standalone` 门禁大翻牌（35 处/33 文件）**：核心洞察——监听服下 `GetNetMode()==NM_ListenServer`≠Standalone，旧门禁**把主机也关了**：主机开不了出征传送门、用不了仓库/锻造/采集/交互/位移技能。翻牌规则：`!=NM_Standalone`（拦截）→`==NM_Client`；`==NM_Standalone`（准入）→`!=NM_Client`。主机（服务端权威）全面放开，客人照旧被拦（客人本地 NetMode=Client；服务端上客人 pawn 副本无输入事件天然安全）。**刻意保留**：`VoxelBuildWorldSave`（存档写盘仍单机-only）、已联机感知路径（PlayerBody/CombatHealth/TemperateHills NetEdits/Net 子系统/火球通道/菜单自身门槛）。涉及：出征/传送门/场景容器/树生长/仓库×2/世界交互/生产×2/开发调优/地牢生成×3/锻造/枪械组装/体素×3/翻越推门突进闪避格挡×5/符文系×4/冰火电圣光法术×6/SkillModel 体力预留。

**4. 怪物离散动画+受击复制（大缺口）**：排查发现各怪类 `State` 枚举**从不复制**——客人侧 `IsControlled/IsBusy/Dead` 全判 false，攻击前摇/硬直/死亡等一切离散动画在客人端整层缺失（只有 locomotion 靠 CMC 速度驱动）。两层修复：
- `NurseZombie`/`WolfMonster`/`FleshHandMonster`/`HandBrainMonster`/`PoisonMaggotMonster`/`HundredEyedSlagMonster` 的 `State` 加 `ReplicatedUsing=OnRep_State`，OnRep 重放各自 `SetState/EnterState`（这些函数本就表现内聚，客户端重放安全）。NurseZombie 基类覆盖 Witch/Spitter/FatZombie/Mutant3/BlindSupplicant 全家。
- `MonsterCombatComponent` 开 `SetIsReplicatedByDefault`：复制 `HitReactions`（OnRep 计数器）+`ReactionDuration`+`bStunned`+`NetStunSeconds`；客户端 OnRep 镜像 `BeginHumanoidStun`+各类 `StartHitPresentation` 起手，`bNetReacting` 旗标驱动本地 Tick 走同款 `UpdateReactionPresentation`，计时到点复用 `FinishReaction` 收尾（类内 State 写入是本地美容值，服务端权威覆盖）。`UpdateHumanoidStun` 的 `Nurse->State!=Stagger` 门放宽 `||bNetReacting` 兜底复制延迟窗口。

**剩余已知缺口**：击倒/布娃娃链路（`HumanoidKnockdownComponent` 的 Phase/物理 sim 不复制，客人看不到倒地起身）；冰锥齐射等其余法术服务端化（`AFPSIceSpikeVolley` 群组比单 orb 重）；主机施法特效在客人侧的可见性取决于各法术投射物是否复制（火球已复制，其余未做）。

**验证**：`Build.bat FPSGAMEEditor` Succeeded（含全部翻牌+复制改动；中途一次失败是 `ColdSteelWarehouseWidget` 的 UHT 过期产物——删 gen 文件重建即过，系另一会话未提交改动的中间态）。运行时验证点（留用户）：主机在联机中可出征/交互/施法；客人能看到怪物攻击前摇、硬直、死亡动画；断线回菜单带错误提示。

## 3.21 全法术服务端化收官（2026-10-03，编译通过，未实测）

继火球打样后，把其余 9 个法术全部迁到同一相位化权威通道。**击倒/布娃娃按用户要求本轮不做。**

**协议扩展**：`FColdSteelNetCastRequest` 加 `AimNormal`（放置朝向/坡面法线/弹道方向）、`AimAxis`（暴雪区椭圆长轴）、`Variant`（冰墙高低/圣光自疗位）、`Target`（锁定类法术的目标 actor）。`ExecuteCastRequest` 重构为按 `SkillId` 分派：Phase0 逐技能影子档 `BeginXxxCast` 扣账（fireball/iceSpike 同时生成权威悬停体挂 `PendingCastOrb`）；Phase1 分派到各组件的 `NetCommit*`/`NetRelease` 服务端入口；Phase2/3 通用退款/弃置收尾按技能路由对应 `Finish/Refund`。`Skills/NetCastUtils.h` 新增共享助手：`Send`（意图上行）、`StateFor`、`AuthorityModel`（服务端远程施法取影子档、本地/单机回落 GI 档）、`NetWorldViewPoint`（远端 pawn 的相机参数回退）。

**统一模式**：各法术组件去掉 `NM_Client` 早退门——客人本地跑手势/瞄准预览/凝聚表现（本地预扣账 `BeginXxxCast` 立刻见冷却与蓝耗），Phase0/1 意图上行，服务端用影子档权威执行伤害/治疗/掉落，生成复制 actor 回流各端；客人本地收尾只做 `FinishXxxCast(空Rewards)` 清预留。取消路径统一 `Phase2` 上报退预留。

**各法术落点**：

| 法术 | 客户端流 | 服务端权威 | 远端表现 |
|---|---|---|---|
| 冰锥 | 本地凝聚+瞄准预览；release 发瞄准点 | `SpawnVolleyForCast` 生成齐射体；命中/碎裂/Finish 全在权威端 | `AFPSIceSpikeVolley` 复制 `{NetShooter,NetSource,bNetFlying,NetCount,NetPos[],NetDir[],NetAlive}`，远端 `NetPresent` 摆同款壳（组件自载冰锥素材） |
| 冰墙 | 本地种子+放置预览；release 发落点+法线+形态位 | `NetCommitWall`：服务端独立 `IceWallPlacement::Build` 重验→生成终态墙（无种子段） | `AFPSIceWall` 复制 `{NetTuning,NetPlan,NetState,NetHealth}`，远端 NetInit 自建网格/屏障/冷气，OnRep_State 重演升落碎 |
| 暴雪 | 本地凝聚云+落点预览；release 发落点/法线/长轴 | `NetCommitZone`：range/法线重验→`InitializeZone`+`ActivateZone`；DamageTick 锁权威端 | `AFPSBlizzardZone` 复制 `{NetCaster,NetCast,NetCenter,NetNormal,NetAxis,NetCloudHeight,bNetActivated}`，远端自载 15 件素材重演风暴壳 |
| 圣光 | 本地选目标+凝聚；release 发目标 actor+自疗位 | `NetRelease`：IsTarget/range/LOS 重验（服务端视角位）→权威治疗/伤害 | `AFPSHolyLightEffect` 复制 `{NetTarget,NetSpell}`，远端自建光柱 |
| 闪电 | 本地选首目标+凝聚；release 发首目标 | `NetRelease`：首目标重验→`RunChain`（释放段抽出共享）服务端跑链/感电/过载 | `AFPSLightningArc` 复制 `{NetKind,NetStart,NetEnd,NetSpell,NetWidth,NetBrightness,NetContactLight,NetChargeRatio}`，远端自载 NS_LightningChain 重演 |
| 陨石 | 本地落点选择；release 发落点+法线 | `NetRelease`：range/遮挡重验→权威陨星 | `AFPSMeteorStrike` 复制 `{NetCaster,NetCast,NetDestination,NetNormal}`，远端 InitializeStrike 自载重演；DamageArea 锁权威端 |
| 焰甲 | 本地 StartArmor（火环/武器火） | 服务端组件 `TickArmor` 走影子档案灼烧 tick | `bNetArmor`+`NetArmorCast` 复制，远端 OnRep 播同款火环 |
| 雷云域 | 本地凝聚；release 上报 | 服务端组件权威域：周期 Strike 选链/伤害/感电全在权威端 | `bNetDomain`+`NetDomainCast` 复制远端演云；落雷经 AFPSLightningArc 复制 |
| 雷枪 | 本地充能圈+音效；release 发充能量+眼位+方向 | `NetRelease`：Eye/Dir/ChargeRatio 重算命中链（`FireLanceBody` 抽出共享） | 雷枪柱经 AFPSLightningArc kind=1 复制 |

**架构要点**：组件 `Model()` 在服务端拿到的是 GI 档案（主机档），客人施法时伤害/扣账若落 GI 档会记错人——所有结算侧统一换 `NetCast::AuthorityModel(Pawn,GI)`（服务端→影子档，本地/单机→GI 档）。`ApplyFireMagicHit`/`ApplyIceSpikeHit` 等内部本就带 `Shooter->HasAuthority()` 门，客户端重复跑 hit 循环天然短路，无需额外包装。刃弧（武器附魔特效）与冰墙种子段仍按本地特效处理不复制——它们只在操作者屏上有意义。

**验证**：`Build.bat FPSGAMEEditor` Succeeded（两轮修正：`NetCast::Send` 参数放宽到 `AActor*` 收组件 GetOwner；组件无 `HasAuthority()/GetGameInstance()` 便捷函数改 `GetOwner()->`/`GetWorld()->` 取；`FPSMagicPreview::AimPoint` 收 `const APawn*`）。运行时验证点（留用户）：每个法术在客户端凝聚→释放→远端见到对应表现；命中伤害只算一次；取消/弃置退蓝正确；雷云域的周期性落雷远端可见。

## 3.22 节后增量收口：表现上行/玩家死亡/门族/怪物音频/命中元数据（2026-10-06，skill 已同步，未实测）

节后联机面又长出六块模式，本节补记，细节以 `skills/ue5-multiplayer-netcode/SKILL.md`（同日重排为 13 节 53 条）为准。

**远端形象双向通道**：客户端 `SampleLocalState`→`ServerBodyTransition`（动作沿 reliable）/`ServerBodySnapshot`（80ms unreliable）上行自家 pawn；服务端 `AcceptBodyPresentation` 逐字段消毒（枚举界/NaN/时长≤60s/时戳窗/支点≤500cm/序号单调）存 `ReportedPresentation`；10Hz `SampleRemoteAuthorityState` 只合并表现字段（武器/族/瞄准/位移与玩法值不采），0.6s 不新鲜回落纯权威采样→`ReplicatedState` 下发。消耗品借 `EFPSBodyAction::Consume` 走同一条（`ActionStartedAt=ServerClock()-Age` 回填）。

**玩家死亡**：`UFPSCombatHealthComponent` 复制 `DeathStartedAt`（服务器钟）+`bDeathFromCrouch`，判死 `ForceNetUpdate`；`ApplyPlayerDeath` 权威/OnRep 各端同跑（中断优先动作→禁输入→停走→pawn 停 tick，body/相机组件独立 tick 续播倒地轨）；本机死亡相机 `death_presentation` JSON 轨+`SetManualCameraFade`，`ReleaseDeathCamera` 只归还本次 fade（CameraManager 跨 pawn 存活）。

**门族权威**（首个非玩家 Pawn 复制交互对象）：`FColdSteelDoorNetState{From,To,Speed,StartedAt}` 一次权威过渡，OnRep 按服务器钟重算 CurrentAngle（迟到加入自动补齐）；门 actor 属服务端，上行通道挂自家 pawn 的 `UFPSDoorPushComponent`：`ServerToggleDoor`/`ServerReleaseDoor`/撞门三段+`ClientPushResult` 撤本地起手；`ServerCanInteract` 全链复验（LOS 首挡=目标门/朝向/冲刺意图=远端 `bWantsToSprint`）；子类 Contact/Key/Drag/Sliding/Revolving 共享同结构；`fps.DoorPush.Debug` 沿闸门链输出拒绝原因。

**怪物离散表现/音频**：一次性提示统一"复制序号+服务器钟沿"不走 multicast（`AttackSequence+AttackStartedAt`/`ThreatSerial`/`PouncePhase`/`bCloaked`，M27 OnRep `SetCombatTime(ServerClock()-StartedAt)` 中途进招也对时）；循环声=各端本地 `UAudioComponent` 由复制态驱动；`NM_DedicatedServer` 是音频/表现总闸；奖励归属走服务端影子档不用"本地 controller"做门禁（M25 客机不吐撕咬奖励修复）。

**命中元数据服务端重建**：`GuardAttackSerial`（同挥目标组）+`GuardSourceInstance`/`DealerSourceInstance`/`ZhenmoSourceInstance` 由服务端按*服务端物品*回填；`bRisingDragonFinisher`/`ToughnessDamageMultiplier` 经 `ColdSteelMelee::Evaluate(Declared,ShadowModel)` 复算，客户端申报效果标志一律不采；AttackMeta 编码 0x0F 连段/0x10 重/0x14 上挑/0x20 旋风/0x40 裂斩/0x80 快攻（0x20|0x80 不吃韧性倍率）。

**杂项**：`FLAG_Custom_3`=架枪意图位（SavedMove 压缩位也是服务端读远端按键意图的唯一可信口）；影子档案经 `ApplyColdSteelProfile→Configure` 灌进服务端 pawn 附魔组件（Zhenmo/Jingang/Dealer 是 CreateDefaultSubobject）；`Plugins/ColdSteelNet` 在库内但 `Plugins/` 被 .gitignore（提交 `git add -f`）；`ServerReportBodyAction` PlayerState 端点已接线无调用方（离散动作由表现上行覆盖）。

**本节修复**：门钥匙环 `AFPSGAMECharacter::DoorKeys` 原只在服务端写入且未复制——客机交互提示"有钥匙"分支读本机 pawn 恒为空、键门恒显"需要钥匙"（开锁功能正常仅文案偏差）。已把 `DoorKeys` 转 `UPROPERTY(Replicated)` + `DOREPLIFETIME_CONDITION(COND_OwnerOnly)`（FPSGAMECharacter 首个复制成员，`GetLifetimeReplicatedProps` 落 `FPSGAMECharacterProfile.cpp`），持有者客机镜像自己的钥匙环，提示恢复正确。

**门打不开修复（2026-10-07）**：日志 `两侧摆动空间均被阻挡，拒绝开门` 定位到 10-04 新加的"两侧皆堵拒开"判定误伤——门洞只比门板宽几厘米，门板摆扫时铰链侧角尖擦进紧贴的门梃/过梁凸包（PowerTheme 整屋壳 UCX 距门板铰链边仅 ~3cm）。`IsSwingBlocked`（门/窗同口径）新增两类豁免：**门板容身壳**（门板平面方向放宽 ~10cm 收集的贴合构件——门套/侧梃/过梁/嵌着门板的墙壳分段；厚度方向不放宽，正面顶住门板的箱子仍算阻挡）+ **门族门板互免**（双开门两叶子铰链各在外缘互不死锁）。阻挡者现在写日志（`摆动被挡：方向/进度/阻挡=Actor:Component`），滑动门 `IsSlideBlocked` 同步输出阻挡者名。另修客机 `TraceTarget` 白名单：旧写法只认 `AColdSteelDoor`/`AColdSteelWindow`，滑动门/旋转门在客机 E 交互失效——改为复用 `UFPSDoorPushComponent::IsNativeDoor` 单一口径。

**撞门重试锁存修复（2026-10-07 续）**：实测日志显示客机探测命中闭门后触发起手→服务端复核拒收（`左手施法占用`）→`ClientPushResult(false)` 撤本地动作，之后 `LastDoor` 把同一扇门永久锁存（直到松开 Shift/视线离开），一次瞬态拒绝=这扇门该次冲刺内永远免疫。修法：触发点武装 `SameDoorRetryAt=now+.55s`（兜底 `BeginPush` 姿态捕获早期失败——它不走 `Cancel`），`Cancel` 失败/中止时在回执时刻再武装一次（>服务端 .2s 节流窗），`Advance` 的同门跳过改为"冷却内才跳过"——0.55s 后继续冲刺对着同门自动重试，由服务端占用门收敛终态。另给 `左手施法占用` 加逐项分解：`AFPSGAMECharacter::DescribeLeftHandBusy()` 按 `IsLeftHandBusyForCast` 同序输出激活谓词（法杖 NotReady 时附 busy/视模可见性细目），客户端 `CanStart` 与服务端 `ServerCanInteract` 共用该字符串——下次出现"客户端过、服务端拒"的两端分歧时日志直接点名卡在哪个字段（服务端副本的视图模型可见性/`WeaponState`/副本忙位是已知疑似点）。

**失败日志去 cvar 化（同日晚）**：复测发现整轮 PIE 零门日志——`fps.DoorPush.Debug` 不跨会话持久，用户没重新开就完全静默。把链上所有**稀有失败/尝试节点**改为无条件输出：触发起手、`BeginPush` 失败、服务端复核拒绝（含 `[谓词分解]`）、节流拒绝、接触时刻复核拒绝、开门失败、客户端失败回执、E 键客户端请求被拒、E 键服务端拒绝。每帧探测类（`探测：首个遮挡`/`未触发`/`朝向拒绝`/`冲刺中但CanStart拒绝`）仍留在 cvar 后防刷屏。此后"撞不开门"的报告不再需要先教用户开开关。

**左手占用自拒根因修复（同日晚，实测定位）**：去 cvar 化后日志立刻指认——`服务器起手拒绝：原因=左手施法占用[DoorPush]`，且起手与拒绝同毫秒（同进程内评估）。根因：`IsLeftHandBusyForCast`/`IsCastBlockingLeftHandAction`/`IsSpellGestureBlocking` 三谓词首项都是 `IsDoorPushActive()`（读组件 `bActive`）；本机/主机/PIE 上发起端与权威端是同一实例，`BeginPush` 先置 `bActive=true` 再发 `ServerBeginPush`，复核时读到"正在推的门推就是这次推"，恒自拒。远端客机服务端副本 `bActive` 恒假所以不误伤，但这是语义巧合不是设计。修法：三谓词加 `bIgnoreDoorPush` 参数（默认 false 不影响施法/其他调用方），门推组件 `CanStart`/`ServerCanInteract` 两处门禁统一传 `true`——并发语义不损：客户端侧 `bActive` 期间 `Advance` 提前 return 根本到不了探测，服务端侧 `ServerDoor`+`LastServerRequest` 节流挡并发请求。

**未做/遗留**：运行时双进程验收未跑（用户规则）；`ServerReportBodyAction` 备用端点待后续离散动作需求再启用或清理。

## 3.17 通用施法通道 + 火球服务端化打样（2026-10-02，代码自查过，编译因 Live Coding 占用未跑）

**架构（A 模式打样）**：`FColdSteelNetCastRequest{SkillId,Phase,AimPoint}` + `PlayerState.ServerCastSpell`（Server Reliable）+ `ClientCastResult` 回执（Client Reliable）。Phase：0=凝聚 1=发射 2=凝聚期取消(退蓝清CD) 3=弃置悬停体(只清占用)。服务端 `ExecuteCastRequest` 按 SkillId 分派（当前仅 `fireball`），影子档案校验 pawn/死亡/冷却/法耗并 `BeginFireballCast` 扣账，orb 由服务端生成（`bReplicates`+`SetReplicateMovement`），各端靠 actor 复制看表现。**新法术接入=SkillId 注册+ExecuteCastRequest 加分支+组件侧 SendNetCast 调用**，不加新 RPC。

**关键文件**：
- `ColdSteelPlayerState.h/.cpp`：请求结构/RPC/pending 状态（PendingCastSkill/Orb/At/PaidMana）+ Tick 里影子档 `AttachPawn`+`TickRuntime`（冷却/回蓝服务端时钟驱动）+ 看门狗（球外部消亡→退款清占用）。
- `FPSFireballComponent.h/.cpp`：NM_Client 分支不本地生球——本地照旧跑手势/扣本地蓝（表现），`SendNetCast(0)` 上报；`bNetExpectOrb` 覆盖"已凝聚、副本在途"窗口；副本到达经 `AdoptNetOrb` 认领为 Active；2.5s 超时本地退款收尾；`LaunchAtContact` 发 Phase1+AimPoint；`Cancel`/`InterruptForPriority` 走 `ReleaseOrb`（Phase2/3）；`NetCastRejected/NetCastCancelled` 收拒绝与取消回执。
- `FPSFireballProjectile.h/.cpp`：`bReplicates`+ReplicateMovement；`Shooter`/`NetXxx`（Hover/Gravity/Range/Radius）/爆炸事件字段（NetExplodePoint/Normal/bNetSurfaceHit）+`bFlying`/`bFinished(ReplicatedUsing)` 复制；服务端跑权威弹道+`ApplyFireballExplosion`（影子档优先解析），远端副本只演 FX；`OnRep_Finished` 播同款爆炸表现；`SetLifeSpan(1.2)` 保证最后一批复制字段先出网再销毁。

**口径**：客人本地蓝/冷却是表现性预扣（服务端回执可对账退款），权威账在影子档；主机玩家走原 standalone 路径不动。`PendingCastOrb` 每 PlayerState 独立，双客同施互不干扰。

**验证**：代码自查（声明/定义/RPC 签名/生命周期分支全部核过）；**编译未跑**——编辑器开着 Live Coding 占构建锁，Ctrl+Alt+F11 或关编辑器后 `Build.bat FPSGAMEEditor` 生效。**运行时未验**：火球进服→生球→发射→爆炸→回执全链、双人同施、取消/超时退款均待 -game 双进程实测。
## 3.18 PIE 多开"恒有一窗卡死"修复（2026-10-02，编译未跑）

**症状**：PIE 玩家数=N 时恒有 1 个窗口冻结在 TransitLoading 遮罩（0%/已等待0秒/不吃输入），其余正常。

**根因——进程级全局委托跨实例串扰**：`FCoreUObjectDelegates::PreLoadMap` 是全进程广播，PIE 单进程多实例（服务器+N 客户端，各 GameInstance 各有 TransitLoadingSubsystem）都会收到任一世界的"开始载入"。`AfterMap` 有 `World->GetGameInstance()!=GetGameInstance()` 过滤但 `BeforeMap` 没有 → 每次客户端开始旅行都会给**服务器窗口**也 `BeginTransition` 挂遮罩并锁 `bMapLoading=true`；客户端加载完的 `AfterMap` 在服务器侧被 GI 过滤 → 服务器窗口遮罩永不消除 + `SetIgnoreInput(true)` 吞输入 = 永久卡死。每局恰卡一窗（服务器窗），N-1 正常，与观察吻合。

**修复**：
- `TransitLoadingSubsystem`：`PreLoadMap` → `PreLoadMapWithContext`，`BeforeMap` 加 `Context.OwningGameInstance!=GetGameInstance()` 过滤；解绑同步改。
- `ColdSteelNetWorldSubsystem`：同型串扰——`FGameModeEvents` 也是全局广播，客户端子系统会误对服务器登录事件跑 `InitializeGuest`/`SaveShadowToHostDisk`；`OnPostLogin`/`OnLogout` 补 `GameMode->GetWorld()!=World` 过滤。

**遗留同类排查口径**：以后凡是绑 `FCoreUObjectDelegates`/`FGameModeEvents`/`FWorldDelegates` 等全局委托的子系统，回调第一行都应先做归属过滤。

**验证**：代码自查；编译未跑（编辑器 Live Coding 占用）；PIE 双人实测待用户回归。
## 3.16 联机接入主仓（2026-10-02 午后，主仓 FPSGAMEEditor 编译通过）

**方式**：不走 git merge（主仓 HEAD 已过 merge-base 且挂着 ~770 文件的其他会话 WIP）；按"worktree 有、主仓缺"的差异集做文件级移植——纯新增整拷、纯增量整拷（删除行逐一核过只属联机改动）、混合文件手工摘 MP 块贴到主仓新代码上。

**整拷（与 worktree 现完全一致）**：`Source/FPSGAME/Multiplayer/` 全目录（PlayerState+WorldSubsystem）、`Plugins/ColdSteelNet` 全部源文件与 uplugin、Body 组件四件套、`FPSCombatHealthComponent`(.cpp/.h rewind 缓冲)、`PoisonMaggotVenomFX`（%0 崩溃修复）、`FPSGAMECharacterProfile.cpp`（PossessedBy/OnRep_Controller/TryAttachLocalProfile/OnRep_ReplicatedMovement）、`FPSGAMEGameMode.cpp`（PlayerStateClass）、`FPSCharacterMovementComponent`(.cpp/.h SavedMove 位+断流看门狗)、`FPSPlayerDodge.cpp`/`FPSDodgeMovement.cpp`（联机闪避）、skill 文档与本日志。

**手工移植（保留主仓他人 WIP 不动）**：
- `FPSGAMECharacter.h/.cpp`：MP 成员+SavedMove 意图写法+断流冻结/僵尸键闸+开火戳+Tick 10 个表现调用 `IsLocallyControlled()` 包门（远端副本不跑第一人称表现）。
- `ColdSteelSkillRules.cpp`：NetHitForward 转发器+AwardKillByOwner+影子档案优先（`Snapshot`/`ApplyHit`），含 FPSGAMECharacter.h include。
- `TemperateHillsWorld.h/.cpp`：bReplicates+Seed/WorldId/NetEdits 复制+`StartWorldPipeline`/`ConvertNetEdits`/`SyncNetEdits`/`OnRep_NetEdits`+Tick 客户端重建入口；**矿石空间加权签名（他人新工作）未动**。
- `ColdSteelStatusModel.h`+`ColdSteelProfileRuntime.cpp`：`CreateShadowModel`/`AdoptNetMirror`（主仓版补齐 IceWall/Meteor/FlameArmor/Blizzard/StormDomain/ThunderLance 全技能字段——比 worktree 版多 6 个，修掉影子档案缺技能定义的潜在 bug）+ `PersistState` 专用服门禁。
- `TransitLoadingSubsystem.cpp`（NM_Client 过场放行）、`FPSPotionUseComponent.cpp`、`FPSLightningComponent.cpp`（去掉 NM_Standalone 门禁；主仓 `HasOtherPreparedSpell` 等新逻辑保留）。
- `Config/DefaultGame.ini`：`bShareMaterialShaderCode=False`（-game 必需）；`Config/DefaultEngine.ini`：连接超时 180s（editor 客户端联调）。

**故意不搬**：`GlobalDefaultGameMode=FPSNetGameMode` 全局默认（主仓保留 FPSGAMEGameMode；WorldSubsystem 对任意 GameMode 兜底，联机会话才激活）、worktree 的 GameDefaultMap 测试图覆盖、`DisabledPlugins=Python`/`Engine.Python.IsEnabledByDefault=0`（-game 崩溃规避，主仓编辑器依赖 Python 管线，需要时单开 issue）、`FPSGAMEPlayerController.cpp/.h`（主仓有他人 SpawnHubTestChest 等新工作，无联机改动）。

**验证**：`FPSGAMEEditor Win64 Development` Result=Succeeded，`UnrealEditor-FPSGAME.dll`+`UnrealEditor-ColdSteelNet.dll` 均新产出。**未跑双进程冒烟**（接入后的 -game 联调与人工验收项沿用 §1 待办）。

## 3.15 战术冲刺"停不下"修复（2026-10-02 午后，编译通过 + -game 回归冒烟）

**用户报告**：战术冲刺后 A 停止，B 视窗里 A 仍径直冲刺不停。

**根因排查**：`M4TacticalSprintComponent` 只是第一人称视模动画层（不驱动位移），flag 链路本身已验证连续到达（上一轮 `b=0/1` 交替）。真凶是两条独立失速路径，都不经 SavedMove 语义：

1. **服务端陈旧 move 沿用**：远端 pawn 在服务端跑 `SimulatedTick`，引擎默认沿用**最后一个已处理 move 的 `Acceleration`+压缩标志**——客户端窗口失焦被节流/丢包/卡死时 move 断流 >0.4s，服务端就按旧冲刺加速度永续模拟 → B 看到"径直冲刺"。实测证实：双 `-game` 后台失焦窗口 move 断流 0.40-0.83s 每场稳定出现 5+ 次。
2. **僵尸轴输入**：失焦窗口的 axis 绑定以最后键值逐帧重发（KeyUp 未到达），Tick 里的 `MoveInput` 清理挡不住回调内 `AddMovementInput` 的逐帧注入 → A 自己其实还在走。

**落码**：
- `UFPSCharacterMovementComponent::TickComponent` 服务端看门狗：`HasAuthority()&&!IsLocallyControlled()` 且距上个 move >0.4s → `Acceleration` 清零 + `bWantsTo*` 复位 + 滑铲摩擦恢复（move 恢复下一帧自愈）。打点 `MPTEST stale-move watchdog`。
- `MoveForward`/`MoveRight` 回调内物理键闸（WASD+方向键，`GetAsyncKeyState`）：轴值与物理按下不一致即归零——失焦僵尸轴从源头不再注入。
- 断流冻结时同步清零 `Velocity`（身体动画读 `GetVelocity`，旧值会呈原地跑步）。

**冒烟回归**（MPHost4/MPClient4.log）：看门狗按预期在真实断流窗触发 5 次（0.40-0.83s），期间 `_1` 停在 x=102 vel=0 无漂移；sprint flag 继续正常交替；~80s 无 Fatal。**用户场景的"A 停 B 看 A 还在冲"窗口已被看门狗在服务端侧钳死**；僵尸轴路径未被自动化覆盖（合成输入豁免物理键闸），人工验收即可直接验证。

## 3.14 重构收尾+双进程实测（2026-10-02 午，编译通过 + -game 冒烟实测）

**新增落码**（接 §3.13，把收尾四项做完）：
- **滑铲入 SavedMove**：`FLAG_Custom_2` 镜像 `bIsSliding`；权威端 flag 触发完整 `StartSlide`（含入铲初速），回放路径 `ApplyNetSlideFlag(...,false)` 只还原状态位+摩擦（速度由 move 重算）。`CanCombineWith` 加滑铲位比较。
- **闪避联机修复**：`StartDodge` 的 `NM_Standalone` 门禁曾让联机下闪避**整个不生效**；改 `IsLocallyControlled()||HasAuthority()`。服务端副本上闪避经 SavedMove 的 SavedRootMotion 到达（无本地 ID），`IsDodging()` 加按 `InstanceName=="PlayerDodge"` 扫描 `CurrentRootMotion`/`SavedRootMotion` 的服务端路径（无敌帧依赖）。`TryDodge`/闪避奖励改影子档案。
- **真 rewind**：`UFPSCombatHealthComponent` 服务端 25Hz 位姿环形缓冲（24 帧≈0.96s，录胶囊中心+头顶/head 骨）；`ClientFireTime` 改客户端估计的服务端钟（`GetServerWorldTimeSeconds`）；`ValidateHitReport` 加时间戳新鲜度（-0.1~0.9s）+ **线段-胶囊轴重算**：弹道与 rewind 位姿最近距 >半径+60cm 即拒。不落 actor 位移，纯数学回放。
- **档案上传两级判脏**：HP/法力/体力/全套冷却/TreeGrowthDay/Infection/DungeonRun 归一比对（NormalizeProfileForCompare）——结构变更立即上行，否则 30s vital-flush 兜底。修掉了"Snapshot 每 2s 都变、去重失效、84KB 心跳事实上仍在跑"的退化。
- **顺手修**：`PoisonMaggotVenomFX::AddImpact` 的 `%MarkCount` 除零/`Marks` 空池崩溃（冒烟实测撞出来的既有 bug，非本次重构引入）。

**双进程冒烟实测**（L_PoisonMaggot + `-game`，客人 `-MPClientWalk -MPClientShot`）：
- ✅ `guest initialized via world subsystem` + `PlayerState=ColdSteelPlayerState_1`（含不带 `?game=` 轮，GlobalDefaultGameMode=FPSNetGameMode 本来就生效，WorldSubsystem 作为地图覆盖场景的兜底已就位）
- ✅ sprint 意图经 move 包到达：`sprint move-flag server: FPSGAMECharacter_1 b=0/1` 交替
- ✅ 客人移动链路：主机探针 700→102（撞墙停，与历史取证一致），无 ClientAdjustPosition/frozen
- ✅ 命中闭环：`synthetic hit sent`→服务端 `hit applied dmg=13.0`（自报 25 被影子档案复算包络钳制）→`hit confirmed on client` 回执
- ✅ 血量复制：`Health replicated` 双向（主机被蛆咬 165↔166、客人回血 199.9→200）
- ✅ 上传瘦身生效：115s 会话仅 5 次上行（首传 structural×2 + vital-flush×3）；旧口径同窗口会发 ~57 次 84KB
- ✅ 毒蛆毒液池崩溃修复后复跑：~2min 会话 0 Fatal error（修复前 55s 即崩）
- ⚠️ 单发 `sim frozen 0.8s` 瞬态（move-ack 抖动，自愈）；首登无存档走新建 fallback（正常）

## 3.13 成熟方案重构（2026-10-02，四大结构问题一次性落地，编译通过，未双进程验收）

**触发**：用户拍板"先按成熟方案重构，删掉旧冲突代码"。四条对齐对象：Lyra（SavedMove 自定义标志/ASC-in-PlayerState 思路）、ShooterGame/nbertoa（服务端命中复算）、GASDocumentation（PlayerState 数据归属）、通用 GameMode 分层实践。

**改动总表**（全部在 `FPSGAME-mp`，主仓零接触）：

| 层 | 旧形态 | 新形态 | 文件 |
|---|---|---|---|
| 移动状态 | `ServerSetSprinting` reliable RPC，与移动包时序解耦 | `FSavedMove_FPSCharacter` 派生，`CompressedFlags` 占 FLAG_Custom_0(sprint)/FLAG_Custom_1(ADS)，`CanCombineWith` 状态变化时拒合并；`UpdateFromCompressedFlags` 同帧回写 MaxWalkSpeed | `Source/FPSGAME/Movement/FPSCharacterMovementComponent.{h,cpp}`、`FPSGAMECharacter.{h,cpp}`（删 RPC） |
| 玩家数据 | `UColdSteelNetChannelComponent`（挂 PC）+ 84KB 全量快照 2s reliable 心跳 | `AColdSteelPlayerState`：`PublicInfo` 全员复制、`MirrorBlob` 走 `COND_OwnerOnly`、上传=首传 512B 分片(≤2 片/tick)+CRC 变更检测（**无周期全量**）、下行权威镜像 OwnerAck 流控 | `Source/FPSGAME/Multiplayer/ColdSteelPlayerState.{h,cpp}`（新） |
| 服务端影子 | 通道组件持有 | PlayerState 持有 `UColdSteelStatusModel::CreateShadowModel` 影子档案，`Pawn` 绑定+`ShadowPawn` 重试链喂 `ApplyColdSteelProfile`+`NetShadowProfile`；**只挂远端玩家，主机走本地单例** | 同上 |
| 命中权威 | 客户端报伤害/爆头/穿甲/经验全收 | `FColdSteelNetHitReport` 改为瞄准点/命中点/骨名/方向+ShotTimeSeconds+语义标志+汇聚弹数；服务端 `ColdSteelSkills::Snapshot(Shooter, ShadowModel->Equipped(), bFiredRound)` 复算，`ClaimedDamage` 仅作包络钳位（过渡态）；`bFiredRound` 防客户端伪报消耗标志；时间窗校验 vs GameState 时钟 | `ColdSteelPlayerState.cpp`、`FPSGAMECharacter.cpp`（`LastShotConvergenceRounds`）、`ColdSteelSkillTypes.h`、`ColdSteelSkillRules.cpp` |
| 远端形象 | `SetAuthoritativeState/Equipment` 零调用 | `SampleRemoteAuthorityState` 服务端采远端 pawn 实态写 `ReplicatedState`（sprint/aim/滑铲/蹲/开火/换弹）；`ApplyColdSteelProfile` 后服务端 `CaptureEquipment` 填 `ReplicatedWeapons/Outfit`（outfit 源改影子档案优先）；`ServerRecordAction` 替 `ServerReportBodyAction` | `FPSPlayerBodyActions/Component/Equipment.{h,cpp}` |
| GameMode 分层 | `AFPSNetGameMode`（AGameMode 直生）依赖被选中 | `UColdSteelNetWorldSubsystem` 挂 `FGameModeEvents::PostLogin/Logout`，**任意地图 GameMode 下 MP 通道都激活**；`AFPSGAMEGameMode` 构造统一设 `PlayerStateClass`；NetGameMode 只留默认 spawn | `Source/FPSGAME/Multiplayer/ColdSteelNetWorldSubsystem.{h,cpp}`（新）、`FPSGAMEGameMode.cpp`、插件 `FPSNetGameMode/ColdSteelNet.cpp` |
| 血量/战斗宿主污染 | `OnDamage` 月影/续命读主机单例；Health 无 OnRep 收敛 | `FPSCombatHealthComponent` 全伤害路径影子档案感知（`GetNetShadowProfile` 优先）；`OnRep_Health` 客户端死亡收敛 | `FPSCombatHealthComponent.cpp` |
| 旧通道 | — | **退役**：`ColdSteelNetChannelComponent.{h,cpp}` → `trash/mp-channel-into-playerstate/`（SHA256 记录在 trash 旁）；插件 Intermediate 陈旧 UHT 已清 | 插件 |

**编译**：`Build.bat FPSGAMEEditor Win64 Development -project=FPSGAME-Online.uproject` → **Succeeded**（两轮：先修 `Multiplayer/` 内同目录 include 与 `../` 相对路径问题）。

**未做/遗留**：
- **运行时双进程验收未跑**（用户规则：验收由用户做）；
- 真 rewind（历史位置环形缓冲+时间戳回放碰撞查询）**只落了时间戳上报/校验骨架**（`ServerReportShotStamp`），历史缓冲本体未实现——`ClaimedDamage` 钳位是过渡妥协，下一步立历史缓冲后可删；
- 客户端体姿仍走 `bIsSprinting||bServerSprinting` 式 OR 语义的旁枝已随 RPC 删除自然关闭，但滑铲/闪避/越野仍未入 SavedMove（同法可扩 FLAG_Custom_2..）；
- skill 文档 `ue5-multiplayer-netcode` 的"通道组件"章节已过时，待重写（见下一步）。

## 3.12 移动同步取证结论（2026-10-01 深夜，全探针版）

**已证事实（全带日志证据）**：
1. **-game 双进程形态：客户端移动→服务器模拟→复制回传全链路一致**（MPRep4 轮：客人 pawn 700→417(vel450)→102 两端探针逐步一致，走到墙停）；
2. PIE 多窗口形态：服务器坐标探针跟踪活跃输入（15:31 轮 Character_2 全程平滑），但存在**移动确认间歇断流**（CreateSavedMove 96 上限告警 7-11 次/会话；活跃客人出现 3s 跳 500 单位的爆发式追赶+16s 冻结窗），**另一客人同窗平滑**——断流与该连接的确认处理相关而非全局；
3. 五层加固全部生效且保留价值：冲刺 RPC（PIE 12 发 12 收对账）、僵尸键物理护栏、网格平滑禁用、断流冻结（11 次触发）、Tick 表现门禁（远端副本只跑玩法）。
**判定**：移动同步架构正确；PIE 单机多窗口（3 世界共进程共 GPU 于 750 Ti）的帧饥饿造成的确认断流不可作为移动手感验收环境。**正式验收场地=双机 LAN 实测**（用户最初问的形态）或 -game 自动驾驶压力代理。
**测试基建沉淀**：-MPClientWalk 客户端自动驾驶（真实 AddMovementInput 通路，注意会被物理键护栏清零——已加 bMPAutoInputActive 豁免）、-MPConnect 预热连线、服务器 2s 坐标探针（tick/mode/vel）、冲刺双端打点、sim frozen 告警。
**遗留给 M5/M6**：移动确认断流的连接级根因（NetUpdateFrequency/通道优先级调优）、ADS 同类、档案 2s 全量重传差分化。

## 3.11 冲刺失控五层洋葱·终局修复（2026-10-01 晚，FPSGAMECharacter.cpp，未入分支提交）

**用户实测症状链**：冲刺后对方模型跑出场/消失、停不回来 → 模型跑走但脚印烟尘留在真实位置 → 双方看到的模型位置和动作不一致。
**五层剥洋葱（每层都真实存在，逐层修复后最终收敛在根因）**：
1. 冲刺意图不上报（服务器按走路速度模拟）→ ServerSetSprinting RPC（§3.10）；
2. 僵尸键（失焦无 KeyUp）→ 物理键态护栏 GetAsyncKeyState（§3.10b，IsInputKeyDown 与僵尸键同事件流，v1 无效）；
3. Mesh 网格平滑外推失控 → NetworkSmoothingMode=Disabled（用户观察"脚印留原地模型跑走"定位）；
4. **N 倍速档案 tick**：Profile->TickRuntime 被每个 pawn 各调一次，N 人局单例档案每帧 tick N 遍（体力/回血 N 倍速）→ IsLocallyControlled 门禁；
5. **Tick 表现门禁（根因主刀）**：角色 Tick 的 11 个纯表现函数（相机/视模/瞄准镜/越野表现/支架表现/枪械反馈/跳姿/涡轮/鼓坠/折叠瞄具）在每台机器的每个 pawn 副本上全跑——服务器为 3 个角色跑全套第一人称表现拖出秒级卡顿 → 移动确认断流（96 saved moves ×11 次/会话）→ 预测与权威永久分叉=用户看到的全部症状。门禁后远端副本只跑玩法与移动。保留全端：ServiceHeldFire/UpdateActionPose（喂身体状态采样）/武器状态机/换弹服务。
**取证工具留存**：NetGameMode 每 2s 的 MPTEST pos 探针 + 冲刺双端打点（下一步复现对照用）。

## 3.10 移动状态复制·冲刺同步（2026-10-01，FPSGAMECharacter.h/.cpp + Profile.cpp，未入分支提交）

**症状**（用户实测定位）：战术冲刺持续奔跑后对方模型消失，停止后也不同步。
**根因**：`MaxWalkSpeed` 由 `bIsSprinting`（本地输入派生）直接设置（FPSGAMECharacter.cpp:1579），自定义 CMC 无 FSavedMove 预测通道——远端玩家的服务器副本上 `bIsSprinting` 恒 false → 服务器按走路速度模拟冲刺客户端 → 位置分叉 → 修正把服务器侧位置拉到观战者视野外。
**修复**：`bServerSprinting`（服务端侧意图）+ `ServerSetSprinting`（Server/Reliable RPC，拥有连接天然限权）；速度行改用 `bEffectiveSprinting = bIsSprinting || bServerSprinting`（本地预测照旧 + 服务器同速）。
**同类已知未修**：`bMovementAiming`（ADSWalkSpeed）同路径轻微微分叉，下轮处理；slide 的速度倍率同理。

**3.10b 僵尸输入护栏（同日追加，Tick 顶部）**：窗口失焦时输入绑定收不到 KeyUp（PIE 多窗口/Alt+Tab），Shift/W 变僵尸键→弃管玩家永续冲刺跑出场（冲刺同步修好后此现象显形——同步前表现为"服务器分叉消失"）。护栏=本地每帧轮询物理键态（IsInputKeyDown）单向清零 bSprintHeld/MoveInput 的残留分量，不覆盖正常按下路径。5.8 无 bReleaseKeysOnFocusLoss 开关（引擎头文件核实），故用轮询方案；对真实玩家 Alt+Tab 同样有效。

## 3.9 PIE/联机客户端视口修复（2026-10-01，TransitLoadingSubsystem.cpp，未入分支提交）

**症状**：PIE 双人（Listen Server）或联机客户端视口卡在过场加载进度条（纹丝不动）；服务器侧登录/档案链全绿。
**根因链**：①过场遮罩 View 的完成条件是单机流程旗标（bDestinationLoaded 等），联网客户端世界永远凑不齐；②BeforeMap 置位的 `bMapLoading` 在 AfterMap 里被 `World->GetGameInstance()!=GetGameInstance()` 守卫挡住不清理（PIE 多实例/网络旅行下判定不等），后续 Tick 全部在 `if(!View||bMapLoading)return` 提前退出，遮罩淡出/移除代码永远不跑——进度条冻结在"准备完成"。
**修复**（`Tick` 顶部，注入在 StartupView 检查之前）：
```cpp
if(View&&FinishedAt==0&&GetWorld()&&GetWorld()->GetNetMode()==NM_Client
    &&UGameplayStatics::GetPlayerPawn(GetWorld(),0))
{
    UE_LOG(... net-client bypass ...);
    bStartupChosen=true;bDestinationLoaded=true;bCompletePreload=true;
    bMapLoading=false;bPreparationFailed=false;
    RestoreGameplayInput();
    if(View.IsValid()){RemoveOverlay();View.Reset();FinishedAt=0;} // 当场撕遮罩，不走依赖旗标的淡出路径
    return;
}
```
**坑**：Build.bat/UBT 的 Live Coding 检查在引擎层全局生效——主仓编辑器开着会挡住 worktree 构建（连直接调 UBT dll 也挡）；需主编辑器 Ctrl+Alt+F11 或关闭。引擎自带 dotnet 在 `Engine/Binaries/ThirdParty/DotNet/10.0/win-x64/dotnet.exe`。

## 3.8 M3 战斗权威化改动清单（2026-10-01，未入分支提交，重放即生效）

> 游戏模块侧；插件侧（通道命中上报/回执/分块上传/合成射击钩/模块注册）已提交分支。

**① `Skills/ColdSteelSkillRules.h/.cpp`**：命名空间内新增
- `using FColdSteelNetHitForward = bool(*)(AActor*, const FHitResult&, float, const FVector&, const FColdSteelSkillShot&)` + `NetHitForward()`（函数指针存取）；
- `AwardKillByOwner(UGameInstance*, AController* Instigator, AActor* Victim, int64 XP)`：按射手归属选档案（远端玩家 pawn 的 `GetNetShadowProfile()` 优先，回退单例）；
- `ApplyHit` 顶部一行：`if(Shooter&&!Shooter->HasAuthority()&&NetHitForward()&&NetHitForward()(Shooter,Hit,Damage,Direction,Shot))return 0.f;`

**② `Monsters/FPSCombatHealthComponent.h/.cpp`**：Health 改 `ReplicatedUsing=OnRep_Health`、MaxHealth 加 `Replicated`；`GetLifetimeReplicatedProps`(DOREPLIFETIME×2)+`OnRep_Health`（测试期 Warning 日志）；BeginPlay `SetIsReplicated(true)`；cpp 加 `Net/UnrealNetwork.h`。

**③ 六处击杀奖励**（HandBrain/FleshHand/HundredEyedSlag/PoisonMaggot/NurseZombie/Wolf 各 .cpp）：`PC->IsLocalController()&&GetGameInstance())...GetSubsystem...AwardKill` → `GetGameInstance())ColdSteelSkills::AwardKillByOwner(GetGameInstance(),PC,this,ExperienceReward)`；五文件头部加 `#include "../Skills/ColdSteelSkillRules.h"`。

**④ 坑**：5.8 的 FHitResult 用 `FActorInstanceHandle HitObjectHandle`（不是 FHitObjectHandle），赋值 `Hit.HitObjectHandle=FActorInstanceHandle(Target)`；模块类继承 `IModuleInterface`（FDefaultModuleInterface 不存在）；怪物 cpp 原先不含 SkillRules 头。

## 3.7 M2 档案权威化改动清单（2026-09-30，游戏模块 6 处，未入分支提交，重放即生效）

> 与 §3.6 同规则：文件=主仓 WIP 覆盖层+以下改动；插件侧（通道组件+GameMode 装配）已提交分支。

**① `Source/FPSGAME/FPSGAMECharacter.h`**（RearGripAttachment 声明后加）：
```cpp
    /** M2 联机：远端玩家在服务端的影子档案（ColdSteelNet 通道组件注入；主机自己的 pawn 不用，走单例）。 */
    UPROPERTY(Transient) TObjectPtr<class UColdSteelStatusModel> NetShadowProfile;
    class UColdSteelStatusModel* GetNetShadowProfile() const { return NetShadowProfile; }
```

**② `Source/FPSGAME/UI/ColdSteelStatusModel.h`**（`Snapshot()` 声明后加）：
```cpp
    UColdSteelStatusModel* CreateShadowModel(const FColdSteelProfile& GuestProfile);
    void AdoptNetMirror(const FColdSteelProfile& External);
```

**③b `Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp`（2026-10-01 追加）**：`CreateShadowModel` 里 `NewObject<UColdSteelStatusModel>` 的 Outer 必须传 `GetGameInstance()`（子系统类 ClassWithin=UGameInstance，传 TransientPackage 撞 UObjectGlobals:3480 断言崩进程）。

**③ `Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp`**：
- `Publish` 定义后新增 `CreateShadowModel`（NewObject 影子；复制 Definitions/WeaponAmmoGroups/AmmoTypes/StaminaTuning/全部技能定义成员；`Publish(GuestProfile)`；`bPersistenceBlocked=true`）与 `AdoptNetMirror`（=Publish）；
- `PersistState` 闸门改判：`bPersistenceBlocked||NetMode==NM_DedicatedServer` 才拒（放开监听服/客户端写各自磁盘副本）。

**④ `Source/FPSGAME/Monsters/FPSCombatHealthComponent.cpp`**（DamageAfterArmor 模型查找）：
```cpp
    else if(auto* NetCharacter=Cast<AFPSGAMECharacter>(GetOwner()))Model=NetCharacter->GetNetShadowProfile(); // M2: 远端玩家防御走影子档案
```

**⑤ `Source/FPSGAME/Items/FPSPotionUseComponent.cpp`**：TryBegin 判据去掉 `||GetNetMode()!=NM_Standalone`。

**⑥ `Source/FPSGAME/Skills/FPSLightningComponent.cpp`**：Trigger 判据去掉 `||GetWorld()->GetNetMode()!=NM_Standalone`。

**架构注记**：防循环依赖（插件依赖 FPSGAME，游戏模块不能反过来依赖插件）的关键=角色上的 `NetShadowProfile` 指针作为两侧交接面；上行心跳固定 0.8s 全量快照（LAN 无压力，WAN 增量化记入 perf 台账）；建造存档闸（VoxelBuildWorldSave）按计划留 M5（其初始化闸本就阻止联机形态启用，M2 拆了也无功能面）。

## 3.6 M1 门禁/喂料改动清单（未入分支提交，重放即生效）

> 基线=主仓 WIP 覆盖层同步后的 worktree 文件；以下为叠加在其上的全部改动，逐处可粘。

**① `Source/FPSGAME/FPSGAMECharacter.h`**（EndPlay 声明后加）：
```cpp
    /** M1 联机分叉：档案（GameInstance 单例）只允许挂到本机玩家的 pawn 上。 */
    virtual void PossessedBy(AController* NewController) override;
    virtual void OnRep_Controller() override;
private:
    /** 幂等的本地档案挂载：非本机控制的 pawn 一律不挂（防止监听服上远端 pawn 抢走主机档案）。 */
    void TryAttachLocalProfile();
    bool bLocalProfileAttached = false;
public:
```

**② `Source/FPSGAME/FPSGAMECharacter.cpp` BeginPlay（原 `Profile->AttachPawn(this)` 行替换）**：
```cpp
    // M1 联机分叉：单机维持原时序；联网形态下 BeginPlay 时 Controller 常未就绪，
    // 真正挂载点挪到 PossessedBy（服务端）与 OnRep_Controller（客户端自主 pawn）。
    if (GetNetMode() != NM_ListenServer && GetNetMode() != NM_DedicatedServer) TryAttachLocalProfile();
```

**③ `Source/FPSGAME/FPSGAMECharacterProfile.cpp`（EndPlay 实现后追加三个函数）**：
```cpp
void AFPSGAMECharacter::PossessedBy(AController* NewController)
{
    Super::PossessedBy(NewController);
    TryAttachLocalProfile();
}
void AFPSGAMECharacter::OnRep_Controller()
{
    Super::OnRep_Controller();
    TryAttachLocalProfile();
}
void AFPSGAMECharacter::TryAttachLocalProfile()
{
    if(bLocalProfileAttached)return;
    if(!IsLocallyControlled())return;
    bLocalProfileAttached=true;
    if(GetGameInstance())if(auto* Profile=GetGameInstance()->GetSubsystem<UColdSteelStatusModel>())Profile->AttachPawn(this);
}
```

**④ `Source/FPSGAME/Characters/FPSPlayerBodyComponent.cpp` TickComponent（`else DisplayState=ReplicatedState;` 前插服务端分支）**：
```cpp
    else if(GetOwner()->HasAuthority())
    {
        // M1 联机：监听服上的远端玩家 pawn——服务端按权威运动状态采样并发布，
        // 客户端 OnRep 消费。装备数据源要等 M2 档案权威化，这里只发布身体状态。
        DisplayState=SampleLocalState();
        ReplicatedState=DisplayState;
    }
```

## 3. 下一步队列（按序执行，改动前先读计划文档对应节）

### 3.0 闭合 M1 末跳（最近的动作，前置=机器空闲窗口）
直接用 §4 的现成命令重跑一轮（带登录插桩的 NetGameMode 已在分支里）。判读法：
- 主机 `MPTEST Login enter` 之后 5 秒内没有 `Login exit` → Login 内部卡（SpawnPlayerController 链），看卡前最后一条日志定位；
- `Login exit` 有 PC 但没有 `PostLogin`（远端玩家）→ 连接在 PostLogin 前被关，查客户端 LoadMap 是否又失败；
- 客户端 `Welcomed by server` 后 `Failed to load package` → 客户端 travel 地图加载中止（疑与连接被关互为因果，轻量图 GameDefaultMap 已改，观察是否复现）。
- **机器负载是当前最大变量**：用户在用机器时主机 240s 起不完；挑空闲窗口跑，或把客户端轮询拉到 15 分钟。
- 备选消歧实验：客户端先直开轻量图（probe 命令见坑#7 姿态），进世界后从进程内控制台 `open 127.0.0.1:7777`（绕开占位图路径）。

### 3.1 M1 续：玩家本地门禁
`FPSGAMECharacter::BeginPlay` 的 `Profile->AttachPawn`（`FPSGAMECharacter.cpp:339`）按本地拥有者分叉（监听服上远端玩家 pawn 会抢主机档案）。`FPSGAMECharacter.cpp:349-360` 的输入模式直写已有 Cast 判空保护（实证：客户端进程没崩在那）。
### 3.2 M1 续：身体组件服务端喂料
服务端 `ApplyColdSteelProfile` 后调 `SetAuthoritativeState/SetAuthoritativeEquipment`（`FPSPlayerBodyComponent.h:23-24`，全库零调用）。当前只有"客人看主机"方向通（复制字段仅 locally-controlled 时本地采样写入）。
### 3.3 M1 验收
双进程互见位置+身体；单机零回归冒烟。之后进 M2（三闸门+档案权威化，计划文档 §3）。

## 3.5 冒烟战况记录（2026-09-30 下午，按轮次）

| 轮次 | 形态 | 结果 | 关键发现/修复 |
|---|---|---|---|
| 1 | 裸 FPSGAME.exe 双进程 | 双双启动暴毙 | 引擎 `BaseGame.ini:116 bShareMaterialShaderCode=True`（09-08 遗留）+ 全机无 GlobalShaderCache-*.bin ⇒ **裸 exe 未打包形态在本机根本跑不起来**（=主线"-game 15秒崩"悬案解剖）；已加项目级 False 覆盖 |
| 2 | UnrealEditor.exe -game 窗口 ×2 | 主机 55s 后崩 | 崩在 PythonScriptPlugin（StateTreeToolset 的 init_unreal.py 在 -game 态空指针）；已禁 Python 插件 |
| 3 | 窗口 ×2 | 主机被关窗退出 | 测试窗口弹在用户桌面被手动关闭（ViewportClosed→Logout PC_0）；改离屏 |
| 4 | RenderOffscreen ×2 | 客户端 92s 扫描饿死握手+DDC 编译 OOM | 首轮必扫 81GB 资产注册表；握手 20s 超时被打死；后续主机 D3D12 GPU 崩溃（750 Ti 双进程） |
| 5 | nullrhi ×2 | 主机"近植物人" | nullrhi 监听服不泵网络包（零 accept），弃用 |
| 6 | offscreen+超时 180s | **客户端 Welcomed by server ✅** | 超时修复让握手熬过启动停顿；主机收到 Login request；末跳（Login→PostLogin#2）仍未闭合，客户端 travel 地图加载失败（"Failed to load package"，直开同图秒成功——网络 travel 上下文特有） |
| 7 | 轻量图 L_PoisonMaggot | 客户端仍 OOM | 发现客户端连 IP 时引擎先载 **GameDefaultMap=DayNight 当占位世界**（拖全武器目录）；已把 worktree GameDefaultMap 改指轻量测试图 |
| 8 | 同上+机器被用户重度占用 | 主机 240s 未起完 | 判定：抢资源必输，停止磨测试，落提交+文档收尾 |

## 4. 冒烟测试标准姿势（复制即用，2026-09-30 19:50 修订）

```bash
# 主机（worktree 根目录下执行；轻量图 + 离屏 + 免 Python；形态原因见 §5 坑#7）
MSYS_NO_PATHCONV=1 "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe" \
  D:/FPS3D/FPSGAME-mp/FPSGAME-Online.uproject \
  "/Game/Tests/PoisonMaggot/L_PoisonMaggot?listen?game=/Script/ColdSteelNet.FPSNetGameMode" \
  -game -log=MPHost.log -RenderOffscreen -ResX=640 -ResY=360 -nosound "-LogCmds=r.RayTracing 0" &
# 客人（主机 MPTEST NetGameMode active 出现后再启动；断言词是 Welcomed 不是 Join succeeded）
MSYS_NO_PATHCONV=1 "E:/Program Files (x86)/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe" \
  D:/FPS3D/FPSGAME-mp/FPSGAME-Online.uproject 127.0.0.1:7777 \
  -game -log=MPClient.log -RenderOffscreen -ResX=640 -ResY=360 -nosound "-LogCmds=r.RayTracing 0" &
# 断言（UE 日志时间戳是 HH.MM:SS 点分隔，grep 时别写冒号；taskkill 后 sleep 6 再读）
grep -a "MPTEST\|Login request" Saved/Logs/MPHost.log        # 期望出现第2个 PostLogin/NumPlayers=2
grep -a "Welcomed by server\|MPTEST\|Possess" Saved/Logs/MPClient.log
taskkill //IM UnrealEditor.exe //F
```

注意：双进程共用 Saved；档案槽 `?ColdSteelProfile=` 隔离；监听服形态下 PersistState 被 standalone 闸门拒写（M2 拆），不会写坏档案。

## 5. 已知坑与事实（踩过的都记这里，接手前通读一遍省半天）

1. **FAB 站内搜索**参数是 `q` 不是 `query`；fab.com 直抓 403 要走 IAB；FAB 详情页 goto 常超时但页面其实在加载（等 5s 再 snapshot）。
2. **主仓 git 视图不可信**：`git status` 报 Source 只有 7 个改动，实际全量 diff 有 **527 个文件**不同（与"git diff 展示会错序"旧案同源）。**任何"以主仓当前状态为准"的操作必须用文件级 diff/copy（`Tools/mp_overlay_sync.py`），不能用 git status。**
3. **HEAD 不可编**（老毛病"坏的是提交版"）：直接从 HEAD 检出的 Source 编不过（缺类/缺文件）。解法=坑#2 的覆盖层同步，同步后清掉 `Intermediate/` 再编（否则 UBT 的 SourceFileCache/TargetMetadata 缓存着 HEAD 版本的首包含信息，会报假 IWYU 错误"Expected X.h to be first header included"，文件明明是对的）。
4. **Bash 调 .bat 的三层坑**：直接执行引号路径失败；`cmd //c 'mklink ...'` 双引号内反斜杠被吞（要用单引号）；8.3 短路径（PROGRA~2）在 E 盘被禁用。**最终可用姿势：`powershell -NoProfile -Command "& 'E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat' FPSGAME Win64 Development -Project=D:/FPS3D/FPSGAME-mp/FPSGAME-Online.uproject"`**。
5. **引擎 `Engine/Config/BaseGame.ini:116` 有 `bShareMaterialShaderCode=True`**（2026-09-08 19:43 改的，疑似打包会话遗留）。后果：未打包游戏进程在 `FShaderCodeLibrary::InitForRuntime` 直接暴毙。已在 worktree `Config/DefaultGame.ini` 项目级覆盖 False。**主线修复建议同款**（这很可能就是主线"-game 15 秒崩溃"悬案的一半）。
6. **`Engine/GlobalShaderCache-PCD3D_SM6.bin` 全机不存在**：裸跑 `Binaries/Win64/FPSGAME.exe`（未打包、装版引擎）必死于"built to load COOKED content"。这是悬案的另一半。装版引擎的正确 -game 姿态见坑#7。
7. **-game 的正确姿态 = `UnrealEditor.exe <uproject> <map>?… -game`**（编辑器二进制游戏模式，按需编着色器），**不是**裸 FPSGAME.exe。这要求 worktree 编过 **FPSGAMEEditor 目标**（UnrealEditor-FPSGAME.dll 等）。UnrealEditor-Cmd 跑命令行同理。双进程冒烟全部用这个形态。
8. UE5.8 里 `AGameModeBase::ChoosePlayerStart` 是 BlueprintNativeEvent：C++ 侧重写 `ChoosePlayerStart_Implementation`。
9. 平铺布局模块（无 Public/Private 分层，如 FPSGAME 主模块）的头文件默认对外不可 include：外部插件 Build.cs 要 `PublicIncludePaths.Add("$(ProjectDir)/Source/FPSGAME")`。
10. 双进程共用 Saved：日志用 `-log=MPHost.log`/`-log=MPClient.log` 分名；玩家档案槽用 `?ColdSteelProfile=` 隔离；监听服形态下档案写入本来就被 standalone 闸门拒绝（M2 拆），不会写坏。
11. `taskkill //F` 强杀后日志缓冲可能未落盘，grep 前先 `sleep 5`。
12. **UE 日志时间戳是 `HH.MM:SS` 点分隔**（`[2026.09.30-10.57.13:255]`）——grep/awk 窗口匹配别写成冒号，连续踩了两次。
13. **`Plugins/` 整个被 .gitignore 忽略**（和 Content 同款）——提交新插件要 `git add -f Plugins/ColdSteelNet`，且插件内自建 `.gitignore`（Intermediate/Binaries/），否则构建产物进库。
14. **裸 `Binaries/Win64/FPSGAME.exe` 未打包跑不起来是机器现状**（引擎缺 GlobalShaderCache-*.bin + BaseGame.ini 的 bShareMaterialShaderCode=True）——这解释了主线"-game 15 秒崩"悬案。**-game 唯一可靠形态=UnrealEditor.exe**（坑#7）。
15. **客户端连 `IP:7777` 时引擎先加载 GameDefaultMap 当占位世界**——客户端的重量由 GameDefaultMap 决定，与主机地图无关。冒烟已把 worktree 的 GameDefaultMap 改指轻量测试图（`Config/DefaultEngine.ini:5`，主线无关）。
16. **握手超时与启动停顿的赛跑**：客户端首载 30-90s 停顿会打死默认 20s 初始连接超时。worktree 已配 `[/Script/Engine.GameNetworkManager] InitialConnectTimeout=180 ConnectionTimeout=180`（`Config/DefaultEngine.ini:174`）。正式玩家用裸 exe 无此问题，接入主线时回调。
17. **双 D3D12 离屏进程在 750 Ti 上会 GPU 崩溃**（D3D12Util.TerminateOnGPUCrash，约 4 分钟窗口）；nullrhi 的监听服不泵网络包（零 accept）。当前冒烟姿态=offscreen+`r.RayTracing 0`+轻量图，加入完成后尽快收尾。
18. **`?game=` URL 覆盖、地图直开、+覆盖直开** 三种形态都验证可用（probe A/B），排除该嫌疑。
19. 机器被用户重度占用时主机 240s 起不完——冒烟要挑空闲窗口，或接受失败重试。
20. （持续追加……）
