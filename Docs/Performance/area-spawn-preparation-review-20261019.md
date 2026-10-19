# 区域提前刷怪：收尾与联机源码复核（2026-10-19）

用户要求检查上一批完成情况、遗漏及 bug，特别是联机。本轮范围是区域提前准备、锁门入队、延迟实例激活和回收；不扩展到全部怪物技能或整个联网系统。未启动 UE、PIE、游戏进程或双端测试，未修改画质、数量及战斗规则。

## 本轮发现并修正

1. **预算未知被误判为压力。** `MaintainPreparation` 用 `!HasPreparationHeadroom(0)` 决定回收；该函数在 GPU 采样未知或超过 2 秒时也返回 false。渲染卡顿延迟预算回执后，原逻辑会销毁已有准备实例，恢复后又重新分配。新增 `HasRecentRenderMemoryPressure`，只有有效新样本证明确实不足时才按显存压力回收；未知/过期只暂停新分配。系统物理内存与提交余量不足仍可触发回收。
2. **压力回收按插入顺序。** 原循环在 `bPressure` 时直接选中第一个实例，可能先回收当前区域，留下远处或未来波次。现在先回收失效槽位，再选择最不相关的优先级；准入仍优先当前区域，正常刷怪不被可选准备阻塞。
3. **已完成区域的准备定时器未退出。** 上一批为了保留首领死亡后的普通波次继续每 200 ms 刷新区域。现在只有“区域目标完成且所有房间波次完成”才清理准备定时器；未清普通怪、未释放增援不会提前停止，闸门自身 Tick 仍完成抬升。
4. **专用服仍先读取了一次网格渲染数据。** `EstimatePreparationBytes` 的专用服/无渲染分支移到网格查询之前；不再为 CPU 对象准备访问渲染数据。原有 GPU 预热和预算跳过规则保留。

## 路径覆盖矩阵（源码核对）

| 路径 | 核对内容与结论 | 运行证明 |
| --- | --- | --- |
| 单机 | 通道准备两厅；16 个/256 MiB 估算上限；逐帧分摊；临时 LOD/可见性在激活恢复 | 本轮未运行 |
| 监听服务器 | `BindCompletedDungeon` 只在非客户端创建遭遇；准备器再次检查 Authority 和 NetMode；按区域请求而非每玩家独立刷怪 | 本轮未运行双端 |
| 专用服务器 | 仍由服务器创建对象、控制闸门和波次；跳过 GPU 预算、捕获和渲染大小查询 | 未构建/运行独立 Server 目标 |
| 普通客户端 | 不建立准备池；真实怪物从服务器复制；客户端通过 NetworkRunId/Seed 生成选中布局并异步准备类、软依赖和 PSO | 本轮未运行双端 |
| 多人分路 | 区域遍历服务器的所有存活玩家；单个区域请求去重，世界共享总预算；玩家分路不会为同一槽位复制多份池 | 本轮未运行分路 |
| 迟到/重连 | 沿用生成器当前 NetworkRunId/Seed 与真实 Actor 初始复制；共享进度拒绝旧 RunId/Revision，客户端完成布局后再应用当前状态 | 本轮未运行迟到/重连 |
| 锁门/队友入场 | 使用服务器逻辑锁门事件提交全区房间；原角色全胶囊过门与只进不出的闸门规则保留，客户端只做门姿态及本地移动例外 | 本轮未运行挤门/丢包 |
| 准备期间 | 关闭 Actor 复制、碰撞、受伤和原生组件自动激活；不完成构造/BeginPlay；无 Enemy/奖励槽标签 | 引擎生命周期源码核对 |
| 正式激活 | 恢复原复制/组件自动激活/标签；原时间消费放置随机流；FinishSpawning 后正常初始化、AI 与复制 | 引擎生命周期源码核对 |
| 回收/换局 | 预留未绑定击杀委托；换局先销毁遭遇再清 RunId；遭遇 EndPlay 和子系统 Deinitialize 释放预留；队列为弱引用并复查运行状态 | 本轮未运行换图 |
| 迎宾增援 | 普通首波击杀严格超过一半才释放；精英不进入阈值，精英换种类时淘汰不匹配预留 | 源码保留 |
| 货运增援 | 保留 20 秒、8 个名额、门口条件和稳定 RewardSlot；首领死亡只取消待刷槽，不算击杀 | 源码保留 |
| 焚化地下层 | `IsSlotReleased` 同时约束提前准备与激活，仍需实际进入 B1 | 源码保留 |
| 六主题及最终区 | 共用区域注册/入队；各 Configure/FindInitialSpawn/特殊波次规则不改 | 源码逐分支核对 |

## 联机初始化核对依据

本机 UE 5.8 的 `s.DelayOnActorSpawnedUntilFinishedSpawning` 默认 true，当前项目 Config 未覆盖此项。`UWorld::OnActorFinishedSpawning` 在 FinishSpawning 后把 Actor 加入网络列表。准备阶段 `SetReplicates(false)`，激活恢复原标志后才 FinishSpawning，当前路径未发现“准备实例提前复制”或“恢复标志但漏加入网络列表”的问题。

`AActor::InitializeComponents` 会为已注册、恢复 bAutoActivate 且尚未 Active 的组件执行 Activate；`APawn::PostInitializeComponents` 才创建默认 AI 控制器。职员延迟注册在 NurseZombie::OnConstruction 恢复，实际等级、奖励标签和最终变换在这之前设置；准备阶段不提前启动怪物战斗计时。

这属于源码结论，不是断言所有联机场景已经测试通过。未检查本批以外每一种怪物的攻击/技能复制，也没有新增或修改 RPC/存档格式。

## 尚未完成的范围

- 特殊怪物的完整构造/附属构件 GPU 预热仍未实现，当前提前做原生对象分配。
- 客户端每实例的蒙皮/形变输出缓冲仍随真实复制 Actor 初始化；客户端已有资源/PSO 准备不等于实例缓冲已准备。
- 该批分摊初始化，未据此证明持续 GPU 高耗时或旧 400 倍缓冲差异已经修复。
- 双玩家分路、迟到入场、换图、丢包及性能改善尚无本轮运行证据。

## 构建与落盘（续编已完成）

四处修正已编入 Editor DLL 和 Game EXE。续编前后的四个复核源码文件 SHA-256 一致。

| 目标 | 本次最终结果 | 构建时间 | 日志 |
| --- | --- | --- | --- |
| FPSGAMEEditor Win64 Development | Succeeded，DLL 链接完成 | 16.99 秒 | Saved/AreaSpawnPreparationReview20261019/build-editor-final.log |
| FPSGAME Win64 Development | Succeeded，EXE 链接完成 | 651.31 秒 | Saved/AreaSpawnPreparationReview20261019/build-game-final.log |

续编时遇到 `Building/AlchemyWorldView.cpp:117` 的 C4456：内层 Anchor 隐藏外层同名变量。只把内层变量及其一次引用改为 ClavicleMidpoint，计算值与姿态逻辑不变，保留其它并行修改。编译器仍有非阻断的旧 API 警告，本批未扩大到全工程警告清理。

历史记录：首次 Game 构建触发 369 项任务，期间物理内存约 554 MiB、提交余量约 321 MiB，因此本任务主动停止自己的编译，退出码 1。随后导入和其它构建占用释放、内存恢复后，以最多两个编译任务续编，Game 完成剩余 363 项任务。本次成功结果取代上次“源码已保存、构建未完成”的交付状态；原中断记录保存在 delivery.json.previous_attempt。

构建命令沿用 E:/Program Files (x86)/UE_5.8/Engine/Build/BatchFiles/Build.bat，Project=D:/FPS3D/FPSGAME/FPSGAME.uproject，-NoHotReloadFromIDE -MaxParallelActions=2。没有关闭其它 UE/导入进程，没有启动编辑器、游戏、性能测试或联机测试。完整回执：Saved/AreaSpawnPreparationReview20261019/delivery.json。上述未完成的 GPU 开发和运行证据范围保持不变。
