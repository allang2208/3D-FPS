# 丘陵怪物网络加载修复（2026-11-18）

本轮原始检查输出已归档到 `trash/hills-village-lifecycle-20261118/` 的同相对路径；小型回执与恢复清单见 [整理发布记录](../Publication/HillsVillageLifecycle20261118/README.md)。历史证据路径保留原貌，复查仍暂停。

后续 GC、玩家加入、入场和退出崩溃的修复及复测见 [丘陵生命周期联机记录](hills-lifecycle-network-20261118.md)。下面保留 `rendered05` 的原始基线，退出崩溃等结论属于该轮历史结果。

## 原始基线状态（rendered05）

怪物资源预加载与客户端就绪确认已完成 Editor / Game Development 构建。
真实 UDP 首次刷怪和新客户端加入已有怪物的功能检查通过；带渲染客户端退出仍崩溃，
因此整轮 `passed=false`、`functional_passed=true`，不能作为全程无错误验收。
所有测试保存到隔离副本，正式主存档、夜袭进度及村庄关卡 SHA-256 均未改变。

## 基线联机结果

证据：`Saved/HillsNetLoad20261118/rendered05/`，核心文件为 `performance-summary.json`、
`hitch-attribution.json`、`competition-summary.json`、`summary.json` 和 `protected-files-after.json`。

- 两个构建目标退出码均为 0。
- 真实 listen server / client，60ms 延迟、2% 丢包；测试世界种子 `1518277816`。
- 原生夜袭生成 2 个护士怪和 1 个胖怪；首次客户端及新加入客户端均确认模型、眩晕、击倒、两种起身动作引用完整，并各观察 30 秒。
- 三端网络同步加载回执均为 0；测试序列化阈值降至 1ms 后告警仍为 0；目标 NetGUID / 包解析错误为 0。
- 后加入端 16:33:43.667 资源就绪，16:33:43.773 主机收到确认，16:33:43.853 起收到怪物；三个生成事件均记录反应动作已载入。
- 后加入端输入解锁时三只怪物已经完整收到，没有把加载画面解除后的等待冒充正常加入。

| 原生生成帧 | 主机 NullRHI | 首个客户端 D3D12 |
| --- | ---: | ---: |
| 第一个护士怪 | 44.078ms | 23.778ms |
| 第二个护士怪 | 31.115ms | 30.235ms |
| 胖怪 | 23.739ms | 21.344ms |

后加入端两只怪物在同一帧到达（46.391ms），第三只在另一帧到达（35.576ms）。
抽查主机首怪、首个客户端首怪、后加入首批怪物的 CPU Trace，均无 `LoadPackageInternal`。
首次客户端三怪就绪后的 30 秒：P95 25.062ms、最大 39.304ms、超过 50ms 为 0。
后加入端输入解锁后的 30 秒：P95 41.201ms、最大 171.125ms、超过 100ms 为 1。

### 基线中存在的卡顿和退出错误

以下是实际捕获的其他路径，尚未在本次怪物资源修复中修改：

| 实际帧 | Trace 归因 |
| --- | --- |
| 主机 597.7ms、首次客户端 713.3ms（首波生成前） | `ConditionalCollectGarbage` 约 564.6 / 693.0ms，包含 Python 插件 GC；这是 Editor-Cmd 运行环境数据，不能直接等同打包游戏 |
| 主机新玩家进入 337.8ms | `FPSGAMECharacter` BeginPlay 约 263.1ms，含 27 个包加载 scope；不是护士怪反序列化 |
| 后加入客户端 171.1ms | `VoxelBuilder` 约 92.9ms（含同步加载），`VillagePlantingDisplay` 约 55.6ms |
| 两个 D3D12 客户端退出码 3 | 观察完成后正常 RequestExit，再在 RenderThread 蒙皮场景清理中空地址异常；主机退出码 0 |

弱网载入期间另有一条 `ServerMove: TimeStamp expired`，没有将它计作 NetGUID 错误，也没有隐藏日志。
没有为消除退出异常改为强杀进程或关闭渲染功能。

### 测量与交付范围

这是 3 怪受控复查，不是最大夜袭数量、长时间游玩或公网性能验收。
两端分别为 NullRHI 主机和 1280×720 D3D12 离屏客户端，上限 45 FPS，记录真实 EndFrame 间隔。
保留正常画质、光照与场景；未自动打开正式编辑器。

本轮每 3 秒采样进程，16:32:21–16:33:09 发现两段外部编译活动，覆盖首次刷怪观察的一部分；
后加入段未采到外部 UE / 编译进程。未把整轮称作完全无资源竞争的基准，也未把帧间隔变化全部归功于本补丁。
精确的网络加载回执、资源先后关系和调用栈是本次修复的主要证据。

测试 DLL 固定在 `rendered05/Host/Binaries/Win64`，散列为
`877C161F6733F74B8AC02FA941F030C974F3E37EB92B2DFD170D3263030C6A59`。
共享工作区随后还有其他构建，当前 DLL 散列不同；其中仍能检出本次就绪 RPC 和共用动作清单符号，
见 `module-delivery.json`。未以旧的测试 DLL 覆盖并行工作的更新产物；本报告运行数据对应固定测试版本。

正式主存档 SHA-256：`453DE4A7E0B84E2C419F11BE81AF8B3B2A265CA93374132C2E03B717F9F0E848`。
保留用户退出时写入的夜袭进度，SHA-256：`0EC89C466BBEACD3EE836C4381268A551C398669EB97705351DC2DFA8815D79B`。
WorldId：`DD5554E24E2BF263C186319F8C752D2E`。没有新建种子、重建地图或新增正式修复任务。

## 原因

原始证据：`Saved/HillsContinuity20261118/udp08/rejoin.log:5028–5033`。
重连客户端在首次解析 `Default__BP_NurseZombie_C` 时触发
`FlushAsyncLoading`，同一帧加载骨骼资源，随后报告 `240.958603ms`。
当时骨骼编译的内存估计为 4608 MiB，可用预算约 2102 MiB。

UE 5.8 的 `UPackageMapClient::SerializeObject` 这里计时的是接收端
`InternalLoadObject` 和对象解析，不是存档写入，也不是复制数据大小。
原来的夜袭资源准备在 `NM_Client` 分支之前直接返回，客户端没有对应预加载。

## 修改

- `HillsNightAssets.cpp`：在丘陵 World BeginPlay 启动双方共用的异步请求，覆盖护士怪蓝图、胖怪原生依赖、受击动作和传送门；保留成功句柄至离开丘陵，轮询骨骼编译就绪，不 Flush 或强制完成编译。
- `HillsNightRaidSubsystem`：资源准备放到客户端/服务端玩法分支之前。服务端仍独占夜袭预算、刷怪、存档和恢复；既有夜袭存档格式不变。
- 仅对丘陵世界的 NetGUID cache 启用异步网络加载。服务端发送 MustBeMapped 依赖，客户端在包未就绪时等待对应 actor bunch；解决已有怪物时加入的加载竞态。离开世界恢复先前策略，不改全局 CVar。
- `TemperateHillsStreamingPreparation.cpp`：资源未就绪时保留加载状态；真正缺失的资产经过有限重试后报告失败。

## 已完成检查

证据目录：`Saved/HillsNetLoad20261118/fixed02/`。

- Editor、Game Development 构建退出码均为 0。
- 真实双进程 UDP listen host/client，双方读取到 60ms 延迟、2% 丢包。
- 白天加入后，通过原生夜袭生成 2 个护士怪和 1 个胖怪；客户端收到三个有模型、无 authority 的复制实例，继续观察 30 秒。
- 首个客户端正常退出，新进程在三只怪物仍存在时加入，完整收到三个复制实例，并观察 30 秒。
- 主机、首个客户端、后加入客户端均正常退出，退出码 0。
- 三端 `net.ReportSyncLoads` 记录均为空；将测试告警阈值降至 1ms 后，`Long net serialize` 为 0。相关 NetGUID/网络对象解析错误为 0。
- 正式 `TemperateHills_World.sav` 和村庄关卡文件前后 SHA-256 一致；所有测试世界种子为 `1518277816`，WorldId 为 `DD5554E24E2BF263C186319F8C752D2E`。

## 帧耗时及边界

本轮是 NullRHI 的 CPU/网络检查，不能作为渲染帧率结论。
记录的是单调时钟的实际 EndFrame 间隔，测试帧率上限为 45；不是函数独占耗时。

| 原生生成帧 | 主机帧间隔 | 首个客户端帧间隔 |
| --- | ---: | ---: |
| 第一个护士怪 | 89.110ms | 43.624ms |
| 第二个护士怪 | 33.695ms | 28.732ms |
| 胖怪 | 56.512ms | 38.303ms |

以上生成发生于 15:09:19–15:09:24。网络解析中的 241ms 同步加载没有复现，
但主机第一次生成帧仍高于 50ms，不能宣称已经完全消除卡顿。

15:09:38，正式项目的另一个 `UnrealEditor.exe` 进程启动。
首个客户端后半段出现最高 288.905ms 的帧间隔，后加入客户端最高 224.076ms；
这些数据处于额外编辑器并发期间，不能直接归因于怪物或解释为独立性能基准。
载入期间也仍有较长帧间隔，原始记录全部保留在 `performance-summary.json` 和 `Evidence/*-result.json`。

## 用户关闭编辑器后的带渲染复查

`rendered02`、`rendered03`、`rendered04` 均使用私有工程和隔离存档。
主机为 NullRHI，客户端为 D3D12、1280×720、RenderOffscreen，45 FPS 上限，
保留项目画质与光照。每次通过原生夜袭生成 2 个护士怪和 1 个胖怪，再以新进程加入已有怪物的世界。
这里的帧间隔不是渲染 pass 耗时，也不是完整夜袭人数压力测试。

追踪发现初版清单还缺少组件在 BeginPlay 中软加载的动作：击倒、仰卧起身、俯卧起身、眩晕。
`rendered02` 主机第一只护士怪生成帧为 107.189ms，其中四次同步动作加载分别为
14.737、12.730、11.898、13.074ms。现已复用 `DefaultAnimationPaths`，
并抽出运行与预加载共用的 `DefaultStunAnimationPath`，覆盖护士怪和胖怪的八个资源。

该补丁的 Editor / Game 构建均成功，结果在 `rendered04/Build`。
`rendered04` 首次生成帧如下；这些生成事件发生时动作默认资源均已载入：

| 原生生成帧 | 主机 NullRHI | 首个客户端 D3D12 |
| --- | ---: | ---: |
| 第一个护士怪 | 47.235ms | 42.364ms |
| 第二个护士怪 | 38.529ms | 21.237ms |
| 胖怪 | 22.351ms | 28.317ms |

首次客户端三怪就绪后的 30 秒，P95 24.444ms，最大 66.310ms，超过 100ms 为 0。
后加入客户端输入解锁后的 P95 48.794ms，最大 207.306ms，不能称加入过程完全不卡顿。

### 后加入时发现的剩余竞态

`rendered04` 的 `Long net serialize > 1ms` 为 0，但后加入端仍记录到一次
护士怪蓝图包的网络同步加载。三只怪物在加载阶段同一帧到达，当时前两个实例的反应动作尚未就绪。
该帧共 3332.762ms，其中还有玩家控制器和角色的 BeginPlay；不能把整帧时间算给怪物。
追踪中网络读取包含约 286.6ms 的包加载。UE 的 GUID cache 对已存在但尚未 FullyLoaded、
又不带 AsyncLoading 标志的包仍有阻塞分支，因此只有异步 cache 开关还不充分。

已补写 `HillsNightReplicationGate`：每个连接拥有一个临时、仅向该 owner 复制的就绪确认 Actor；
客户端完整载入丘陵夜袭资源后以可靠 RPC 确认，服务端才允许 `HillsNightRaider` 对该连接相关。
服务端 AI、刷怪和预算不等待客户端，其他玩家同步不受影响；确认不入存档，重连重新确认。
组件继续沿用既有初始化路径；最终 `rendered05` 构建、复制时序与资源引用检查结果见本文开头。

### 其他已定位问题

- `rendered03` 主机新玩家进入时 377.3ms 帧，追踪指向 `FPSGAMECharacter` 初始化与同步动作加载。
- 同轮主机一个 402.9ms 帧指向野生动物加载；后加入端输入解锁附近的 205.4ms 帧主要在植被关系生成。
- 所有带渲染客户端完成观察后，正常退出仍发生 RenderThread 空地址异常，退出码 3。
  `rendered02` 追踪定位在 `FSkinningSceneExtension::FUpdater::PreSceneUpdate / Skinning::FreeBufferSpace`；
  Renderer RVA `0x14442df` 是批次骨架信息读取中的间接调用。没有把退出异常归因于网络序列化，也没有通过强制退出隐藏它。

`rendered03`、`rendered04` 均为功能断言通过、进程退出失败，汇总 `passed=false`。
所有原始日志、逐帧样本、调用栈、退出回执与 Trace 均在各批目录内。

### 存档保护与测量边界

用户关闭正式编辑器时新增的 `HillsNight_DD5554E24E2BF263C186319F8C752D2E.sav` 已保留。
`rendered04` 对正式主存档、该夜袭进度及村庄关卡前后散列检查全部相同。
测试使用 `fixed02/OriginalSaveBackup` 的隔离比较快照，不覆盖正式的新夜袭进度。
种子仍为 `1518277816`，世界身份仍为 `DD5554E24E2BF263C186319F8C752D2E`。

`rendered04` 每 3 秒采样进程：启动载入期存在其他编译进程，首次刷怪和后加入观察阶段未采到外部 UE/编译进程；
最后一条退出采样出现下一项构建。采样只能界定可见的并发进程，不能等同完全无外部负载的性能基准。
工具仅在私有工程与显式 `-HillsNetLoadAudit` 标记下运行。没有新增正式修复任务或降低画质。
