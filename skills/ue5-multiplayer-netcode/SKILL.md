---
name: ue5-multiplayer-netcode
description: UE5 原生复制联机开发（监听服务器起步）的工程套路与坑：RPC 载荷限制、子系统实例化、模拟代理自走、客户端网络旅行、PIE 环境假象、隔离开发与取证方法论。联机玩法改造、双进程冒烟、移动同步排查时使用。
---

# UE5 原生复制联机开发套路（FPSGAME 联机线沉淀，2026-10-01）

工程背景：563 cpp 纯单机 C++ 工程改造为监听服务器多人。全案见 `Docs/MultiplayerStrategyAndPlan20260930.md`（计划）与 `Docs/MultiplayerWorkLog.md`（活日志/断点续接）。个人技能为维护源，本目录为工程镜像。

## 一、传输层红线（UHT/网络栈硬限制）

1. **TMap 不能进 RPC 参数/复制属性**（UHT 直接报错）。含 Map 的档案结构传输用**序列化字节块**：`UColdSteelProfileSave` + `FObjectAndNameAsStringProxyArchive(ArNoDelta=true)`，与 `SaveGameToSlot` 同口径——传输格式即存档格式，一套序列化两用。
2. **大载荷 reliable RPC 会被静默丢弃**（整块 83KB 单发=消失，无任何日志）。8KB×11 连发也会灌爆 reliable 窗口（8 在途上限）被丢。正解=**1KB 分片 + 每 tick ≤2 片限速 + UploadId 防串包 + 服务端按序攒包**；下行复制属性（MirrorBlob）同样有大载荷风险，用到时同样分片。
3. 变更检测 + 字节级去重：闲时上行=0；服务端收到相同快照直接跳过应用。

## 二、实例化与生命周期坑

4. **子系统类 NewObject 的 Outer 必须是宿主**（`ClassWithin=UGameInstance` 断言 `UObjectGlobals.cpp:3480` 崩进程）——影子档案用 `NewObject<UColdSteelStatusModel>(GetGameInstance())`。
5. **GameInstance 单例子系统被每 pawn 各调一次=N 倍速 tick**（体力/回血 N 人局 N 倍速）。`TickRuntime` 类入口必须 `IsLocallyControlled()` 门禁。
6. 角色 Tick 的纯表现族（相机/视模/瞄准镜/表现 11 项）在每台机器每个副本全跑=服务器被拖垮。全部 `IsLocallyControlled()` 门禁；保留全端的只有玩法与喂身体采样的函数。

## 三、移动同步

7. **冲刺/开镜类本地输入改 MaxWalkSpeed 必须上报意图**：`ServerSetSprinting`（Server/Reliable，拥有连接天然限权）+ 服务端 `bEffectiveSprinting=bIsSprinting||bServerSprinting`。否则服务器按走路速度模拟冲刺客户端→位置分叉→修正把人拉到观战者视野外。
8. **模拟代理 SimulatedTick 的 SimulateMovement 会用最后速度持续前推**（引擎源码 CharacterMovementComponent.cpp:2030 附近）：移动更新断流时观战本地角色自走出图永不回来（脚印/特效留在真实位置=典型诊断特征）。正解=**断流冻结**：OnRep_ReplicatedMovement 记时间戳+解冻，Tick 里 >0.5s 无更新 SetComponentTickEnabled(false)。关 NetworkSmoothingMode 只治 Mesh 平滑层，治不了胶囊体自走。
9. **窗口失焦僵尸键**：失焦收不到 KeyUp（PIE 多窗口/Alt+Tab），按住的 W/Shift 变僵尸。`IsInputKeyDown` 读同一份事件流同样瞎——用 **Win32 GetAsyncKeyState 物理键态轮询单向清零**（不覆盖正常按下路径；测试钩子的合成输入要豁免）。
10. **PIE 单机多窗口不可作移动手感验收场地**：唯一能解释"同会话一客平滑一客断流"不对称的假设=编辑器"后台使用较少 CPU"对失焦视口节流（待用户验证）；-game 双进程（真实输入通路自动驾驶）已证全链路一致。正式验收=双机 LAN。

## 四、客户端加入链

11. **客户端连 IP 时引擎先加载 GameDefaultMap 占位世界**——客户端重量由它决定；冒烟时把 GameDefaultMap 指轻量图。
12. **重资产地图网络旅行 LoadPackage 会 1.3s 静默失败**（直开同图正常，DayNight/丘陵均复现；根因未根治）。绕法=`UColdSteelNetConnectSubsystem`：`-MPConnect=<addr> -MPConnectDelay=<秒>` 先本地直开焐热资产再进程内 open（GameInstance 定时器轮询，不依赖世界/GameMode）。
13. **单机过场遮罩在联网客户端永不完成**：完成旗标是单机流程；且 `AfterMap` 的 `World->GetGameInstance()!=GetGameInstance()` 守卫在 PIE 多实例/网络旅行下不清 `bMapLoading`→Tick 提前返回→遮罩冻结。正解=Tick 顶部 net-client 旁路：直接 `RestoreGameplayInput()+RemoveOverlay()+View.Reset()` 当场撕掉。
14. 监听服重登入的出生点：会话占用表（重生复用原点/断线释放/满员轮转）+ 无 PlayerStart 兜底 `RestartPlayerAtTransform(原点+250)`。

## 五、构建与工程环境

15. **Live Coding 锁是引擎级全局**：任一 UE 编辑器开着（哪怕别的工程）挡住全机 UBT 构建；连直接调 UBT.dll 也挡。解法=编辑器 Ctrl+Alt+F11 或关闭；引擎自带 dotnet 在 `Engine/Binaries/ThirdParty/DotNet/<ver>/win-x64/dotnet.exe`。
16. **并行开发隔离模式**（主线 763 WIP 不触碰时）：`git worktree` 拉分支 + junction 共享重资产（Content/DDC/被 ignore 的插件/预编译库）+ **文件级覆盖同步**（本仓库 git status 不可信——报 7 实差 527；工具 `FPSGAME-mp/Tools/mp_overlay_sync.py`）。worktree 提交纪律：只显式路径 add 自己文件，`Plugins/` 被 .gitignore 需 `git add -f`。
17. **日志里的硬件名可能是用户改的**（GTX 750 Ti 实为 3080 Ti）；磁盘"慢"测法假象（Get-ChildItem 枚举混进读计时；精确分离后 348MB/198ms）。**环境结论只认精确实测，日志设备字符串只作线索。**
18. 未打包 -game 的正确姿态=`UnrealEditor.exe <proj> <map>?… -game`（裸 exe 需 cooked）；测试窗口一律 `-RenderOffscreen`（弹用户桌面会被关）；双进程日志 `-log=A.log/-log=B.log` 分名；`-game` 无头探测用 `?game=` URL 覆盖 GameMode 不改配置。

## 六、取证方法论（本轮最值钱的沉淀）

- **双端坐标探针**：GameMode Tick 每 2s 记所有 pawn `name/local/x/y/tick/mode/vel`——一眼分辨"服务器真跑 vs 观察者幽灵 vs 输入没到"。
- **RPC 对账打点**：客户端 send 一行、服务端 _Implementation 一行，时序配对=传输层无罪证明。
- **A/B 对照开关**（`-MPNoHeartbeat` 这类）先证伪/证实机制假设，再谈修复。
- **自动化真实移动**：`-MPClientWalk` 合成输入必须走 `AddMovementInput` 真实通路（只写 MoveInput 记账变量 CMC 收不到加速度），且要豁免物理键护栏。
- 日志时间戳是 `HH.MM:SS` 点分隔；`-game` 双进程用探针轮询 grep 驱动断言，不盯屏。

## 相关

- 计划与断点：`Docs/MultiplayerStrategyAndPlan20260930.md`、`Docs/MultiplayerWorkLog.md`
- 插件源码：`FPSGAME-mp/Plugins/ColdSteelNet/`（NetGameMode/Channel/Connect 三件套）
- 证据归档：`trash/movement-forensics-20261001/`
