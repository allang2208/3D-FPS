# 丘陵 GC、加入、入场与退出修复（2026-11-18）

本轮原始检查输出已归档到 `trash/hills-village-lifecycle-20261118/` 的同相对路径；小型回执与恢复清单见 [整理发布记录](../Publication/HillsVillageLifecycle20261118/README.md)。历史证据路径保留原貌，复查仍暂停。

**当前状态：用户要求暂停复查，已停止 lifecycle07 的隔离测试主机和后加入客户端，保留证据；不继续启动测试。** 源码及 Editor / Game 构建已完成。lifecycle03–06 四轮完整联机与正常退出通过，但最新一批入场修正尚缺不受其他游戏影响的最终性能复查。不能宣称所有长帧已经消失。

本轮接续 `hills-monster-network-loading-20261118.md`，范围是用户明确要求的四类卡顿/崩溃及对应联机复查。正式主存档和夜袭进度不迁移、不覆盖，世界种子保持 `1518277816`，WorldId 保持 `DD5554E24E2BF263C186319F8C752D2E`。

## 修改与实际原因

- **新玩家加入**：默认角色初始化先选择默认枪械，随后存档装备替换它；默认资源失去引用后被 GC 回收，下位玩家加入时又同步载入。`FPSBodySpawnResources.cpp` 仅保留实际初始化角色和组件的直接资产引用，以及已经载入的 AKM 首选探测资源，由现有 GameInstance 预加载器持有。没有扫描或常驻全部武器目录，也没有跳过角色属性/装备初始化。
- **入场建造系统**：`VoxelBuildPreparation.cpp` 提前异步准备预览网格、调色板和它实际引用的材质。资源就绪后才走原有初始化；保留建造玩法及存档。
- **村庄植被**：`VillagePlantingDisplay` 将整村关系计算拆成 20m 地块，2m 条带生成，并在添加单个实例之间检查时间预算。候选 ID、种子、竞争邻域和密度规则保持原样；预算是软预算，单项引擎操作不能被中途抢占。
- **未烘焙游戏中的 GC**：CPU Trace 定位到 Python GC 和引用遍历。新的 `FPSStandaloneRuntime` 为 Editor 目标的 `UncookedOnly` 模块，仅在独立 Game 世界中关闭已经完成初始化的 Python 解释器。完整编辑器、PIE 和 commandlet 保留 Python；Game 打包目标不依赖此模块。未禁用 GC，也未延长 GC 周期。初版在 Python 首次延迟初始化之前移除了回调，`lifecycle03` 证明该分支没有生效；已修正为等待初始化完成。
- **铁匠 NPC 入场**：`lifecycle03` 发现居民头部的包反序列化约 182ms，随后三个部件的 `SetSkeletalMeshAsset` 同步等待编译约 211ms。丘陵准备阶段复用居民自己的资产清单，仅在铁匠铺已修复时预载并等待就绪。居民组装轮询编译完成，不再主动阻塞等待工作线程。未修改模型、外观、交易或修复条件。
- **退出崩溃**：UE 5.8 的 skin batch 移除过程仍需读取 MeshObject/骨架，但组件清理可以先将 MeshObject 排入延迟销毁。`FPSGameSceneLifecycle` 在 World BeginTearDown、MeshObject 尚存活时批量移除该场景的 instanced skin primitives，提交一次场景更新并等待渲染命令完成。之后沿用引擎正常注销和资源释放；没有强杀进程或关闭蒙皮、风动、光追来规避异常。

## 源码边界

没有修改超过 800 行的 `FPSGAMECharacterInitialization.cpp`。如后续需要调整其中武器初始化实现，先按默认握持资源、枪族配置、弹匣与外观装配拆分为独立源文件，再单独迁移调用；本轮从较小的 BeginPlay 入口及预加载器修复资源生命周期。

## 第一轮实测：lifecycle03

Editor / Game Development 构建成功。私有工程、隔离存档、真实 UDP，60ms 延迟、2% 丢包；主机 NullRHI，两个依次运行的客户端使用 D3D12 RenderOffscreen 1280×720，45 FPS 上限。原生夜袭生成两只护士怪和一只胖怪，首次客户端及后加入的新进程各观察 90 秒，覆盖自然 GC。

- 功能结果和正常退出全部通过，三个进程退出码均为 0。两个渲染客户端分别先排空 408、358 个 skin components；未出现之前的退出异常。
- 网络同步加载、`Long net serialize > 1ms`、目标 NetGUID/网络包解析错误均为 0。
- 后加入主机帧从前次 337.8ms 降为 91.8ms；其中角色 BeginPlay 为 55.1ms，原来的 27 次包加载不再出现。
- 后加入客户端入场后 90 秒 P95 38.8ms，最大 75.9ms，没有超过 100ms 的帧；前次最大 171.1ms。
- 首个客户端活动观察期最大 84.9ms，但入场附近仍有 513.5ms GC 帧，不能据此宣布 GC 已修复。该帧包括 Python GC 150.4ms、引用遍历 306.3ms；已按上面的初始化时序修正继续复测。
- 植被数量仍为 9,162 / 34 组；正式主存档、夜袭进度和村庄关卡前后 SHA-256 全部相同。
- 每 3 秒采样共 121 次，未采到其他 UE/编译进程。该事实不等于无任何系统负载，也不将 CPU 帧间隔当成 GPU pass 耗时。

证据：`Saved/HillsNetLoad20261118/lifecycle03/` 内 `summary.json`、`performance-summary.json`、`process-samples.json`、`protected-files-after.json`、逐端日志/退出回执/CPU Trace。

## 第二轮：lifecycle04

两目标构建、三端功能与正常退出均通过。三端网络同步加载、1ms 序列化告警和目标 NetGUID 错误仍为零；119 次进程采样未发现其他 UE/编译进程，正式文件散列全部保持一致。

- Python 关闭回调实际执行，GC Trace 中该开销已消失。
- 主机后加入帧 83.1ms；首个客户端入场后的前 10 秒最大 63.9ms，后加入端为 90.8ms。
- 首个和后加入客户端 90 秒活动观察最大分别 65.6ms / 90.8ms；活动 GC 分别 28.7ms / 27.8ms。
- 主机活动期的自然 GC 为 22.7–44.8ms，但首轮仍有 230.6ms GC（完整帧 265.8ms）。Trace 证明 224.6ms 在原生引用可达性分析，预回收回调只有 2.5ms；不再是 Python。

已将初始加载资源的整理纳入丘陵入场准备：以 `GEngine->ForceGarbageCollection(false)` 请求引擎在安全帧末处理，等待实际 `GetLastGCTime()` 变化后才解除加载状态。不在 actor tick 内同步 Flush 包，不更改正常回收间隔，不对已经就绪世界中的后加入玩家重复收集，也不向多个 PIE 世界发出进程级回收请求。

另外定位到 NullRHI 主机在 `PlayerSkillRenderPreparation` 中执行显示预热，`RequestCompile` 单次约 83ms，随后等待永远无法运行的 GPU 代表组件而超时。已在该纯渲染预热层跳过 NullRHI / DedicatedServer；资产加载与 gameplay consumer 绑定继续执行，有渲染的客户端保持原流程。

## 第三轮：lifecycle05

两目标构建、三端功能与正常退出均通过。114 次进程采样未发现其他 UE/编译进程；正式文件散列保持一致。网络同步加载、1ms 序列化告警和目标 NetGUID 错误均为零，村庄植被仍为 9,162 / 34 组。

初始整理确实发生在解除加载状态之前：主机 34.3ms、首个客户端 365.5ms、后加入端 27.8ms。初始原生 GC 的耗时仍然存在，不能把延后输入解锁解释为消除了 GC 工作；进入后的自然 GC 为主机 26.9–44.6ms、两个客户端 26.4ms / 25.2ms。

首个客户端和后加入客户端 90 秒活动期最大帧分别为 62.5ms / 86.1ms，没有超过 100ms 的帧；主机新玩家加入帧为 112.6ms。不过首个入场阶段仍发现主机最大 194.2ms、客户端最大 140.8ms，继续按 Trace 修复以下实际路径。

## 最后一批入场修正

- **导航任务批次**：主机入场长帧中，导航 Tick 分别占 136.9ms / 172.1ms，来自各代理配置集中提交的瓦片任务及主线程几何收集。丘陵导航系统将每个配置的同时生成任务限制为 2；保留全部导航代理、瓦片精度、调用器覆盖半径。
- **动物音效软引用**：首次鹿生成的 BeginPlay 约 92.3ms，分散在多个音效的同步 LoadObject。复用 `HillsWildlifeAudio` 的同一清单，世界初始化时异步准备有自然刷新权重的物种音效；服务端等该物种就绪才生成，接收客户端也提前申请。音效选择、播放和联机事件不变。
- **草地交互材质**：首个客户端的草地 Tick 约 108.8ms，其中两次 `DrawMaterialToRenderTarget` 强制等待编译约 63.9ms / 42.6ms。编辑器构建的独立游戏中，压草与窗口平移先检查实际材质资源编译状态，未就绪时保留有界队列，完成后执行原有绘制；没有禁用压草效果。

`lifecycle06` 的 Editor / Game 构建均成功。该轮首次客户端观察时发现另一游戏 `r5apex_dx12.exe`（18:38:26 启动）同时运行；18:43:35 的 `nvidia-smi` 显示 GPU 利用率 96%。首次客户端活动期最大帧 2,645.6ms，并出现一条 PlayerBody 1.078ms 序列化告警；这些数据完整保留，不计作无竞争性能复查结果，也不将 GPU 总利用率直接当成丘陵某个渲染 pass 的证据。

`lifecycle06` 三端功能均通过，三个正常退出码均为 0，正式文件散列保持一致。后加入端的 90 秒活动期最大 85.4ms，周期 GC 为 31.1ms；这段观察发生在该游戏关闭之后，但整轮仍保留为受干扰记录。

用户已关闭该游戏，18:44:42 再查询确认其进程不在。`lifecycle07` 复用 `lifecycle06` 的同一已编译 DLL 和同一隔离存档快照，经现有 UE 批次锁等待后于 19:00:24 启动主机。进程采样同时记录已发现的游戏进程及工作集超过 1GB 的其他进程，避免仅检查 UE/编译器而漏掉本次资源竞争。

## 暂停时的边界

`lifecycle07` 运行时又发现 `E:/SteamLibrary/steamapps/common/Age of Empires IV/RelicCardinal.exe`，进程于 18:57:27 启动。Windows GPU Engine 计数器对该 PID 的 3D 引擎采样约 80.5%；因此本轮也不作为无竞争帧耗时结论。该轮 DLL、DefaultEngine.ini、DefaultGame.ini 与 lifecycle06 相同。

结束后保存的 95 次进程采样全部包含该游戏；部分采样还记录到其他 UnrealInsights、Blender、Python 进程，不能把本轮当成独占机器的性能数据。暂停收尾时已确认本轮没有遗留 UE 测试进程；正式主存档、夜袭进度、村庄关卡的前后散列均保持一致。

用户随后明确要求“先暂停复查，向我汇报现在查出来的内容”。首个客户端已完成观察并正常退出，退出码 0；主机和后加入客户端按此请求停止。`paused.json` 和 `summary.json` 标记 `paused_by_user`，未完成项的 passed / clean_exits 为 null。脚本的“Process exited before late-result.json”来自主动暂停，不属于新出现的引擎退出崩溃，也不能计作正常退出通过。没有结束其他游戏或其他任务的进程。

待续范围仅为：在没有其他游戏竞争 GPU 的条件下完成最新构建的首次入场和后加入性能复查，并导出 Trace 确认导航批次、动物音效预载和草地绘制恢复的耗时。已有实测中的活动期原生 GC 约 23–45ms、新玩家加入主机帧约 83–113ms，仍不是零卡顿；初始加载阶段的原生 GC 仍可达数百毫秒。
