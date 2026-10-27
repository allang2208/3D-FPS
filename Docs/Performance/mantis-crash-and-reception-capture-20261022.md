# 螳螂死亡崩溃与首大厅 F6 采样分析（2026-10-22）

本轮读取用户已有崩溃、F6 JSON 和 UE trace，在后台修改死亡物理源码；未启动 UE、游戏、PIE 或新的采样。性能项为后续方案，未修改画质、怪物数量、战斗规则或引擎驻留策略。

## 1. 螳螂死亡崩溃

证据：`Saved/Crashes/UECC-Windows-9254CCF046A53FBAD9F3D784B424156C_0000/`，北京时间 23:28:52。调用链为子弹伤害 → `AMantisM27Monster::StartDeathPresentation` → `StartDeath` → `StartPhysics` → `TunePhysics`，旧源码第 357 行访问 `Body->BodySetup` 时异常。

直接缺陷是共用布娃娃代码使用了会销毁当前刚体的碰撞 setter：

- `HumanoidKnockdownComponent.cpp` 在遍历 `Mesh->Bodies` 时对辅助根骨调用 `FBodyInstance::SetCollisionEnabled(NoCollision)`。
- 本机 UE `BodyInstance.cpp:742–770`：物理启用状态改变时调用 `OwnerComponent->RecreateInstanceBody`。骨骼组件沿用 `PrimitiveComponent.cpp:1769` 的实现，重建整个物理状态，旧刚体数组和约束指针因此失效。`BodySetup.IsValid()` 不能保护已经失效的 `FBodyInstance*`。
- 更早的 `MonsterRagdollPhysics::AlignContainerRoot` 也调用该 setter，既可能触发重建，还会丢弃刚设置的根骨关节对齐。

已修改这两处：根骨对齐后只对辅助根骨各碰撞形状调用 `SetShapeCollisionEnabled(..., NoCollision, false)`，最后统一更新过滤数据；移除调参循环中的重复整刚体碰撞切换。保留辅助根骨、关节、质量、阻尼、CCD 和原布娃娃预算；未改螳螂模型、动作或伤害。这修复的是明确的刚体生命周期错误，运行效果仍由用户复测。

源码：

- `Source/FPSGAME/Monsters/HumanoidKnockdownComponent.cpp`
- `Source/FPSGAME/Monsters/MonsterRagdollPhysics.cpp`

## 2. 本次采样范围

- 数据目录：`Saved/PerformanceReports/gpu-F795AB4D41C153281746FAAEBF8876D6/`。
- UE trace：23:26:35.926–23:27:19.174，共 43.248 秒，约 137 MB；在崩溃前已正常关闭。
- 地图 `L_Dungeon_Randomized`，种子 `717709648`，PIE / D3D12，2552×1218，FOV 107.5。最后 10.052 秒 201 帧，无暂停或后台帧，F6 面板打开。
- 首波为 room 1 `FacilityReceptionHall`，同时激活 room 2 `FacilityTransit`；不能把整段成本只算到迎宾大厅的一类怪。
- `available_files_finalized=true`，但 `files_finalized=false`：`StartTraceW` 返回 Windows 错误 5，未生成 `wddm.etl`。UE 时间线与缓冲身份可用，逐资源物理驻留、迁移、缺页和系统 GPU 调度证据缺失。
- 第一波独立战斗窗口完整；第二波只录到触发后约 3.78 秒，未覆盖完整尾段。首波正式激活 35 只，第二波采样内激活 8 只；同时存活峰值因击杀低于总激活数。

离线解码按 GPU 队列的 trace serial 排序，排除不完整首尾帧。CPU 时间与采样单调时钟按 `$Trace.NewTrace` 和 manifest QPC 对齐，本次偏移 261.584474 秒。未使用旧采样的固定时间偏移。

## 3. 帧率与持续 GPU 成本

| 时间段 | 帧率 | 平均帧时 | Game 发布读数 | GPU 发布读数 |
|---|---:|---:|---:|---:|
| 首波前约 3 秒至前 0.2 秒 | 65.1 FPS | 15.36 ms | 10.02 ms | 10.55 ms |
| 首波后 0–5 秒 | 29.6 FPS | 33.74 ms | 14.82 ms | 29.89 ms |
| 首波后 5–10 秒 | 15.6 FPS | 64.02 ms | 21.32 ms | 62.45 ms |
| 首波后 10–20 秒 | 17.1 FPS | 58.61 ms | 19.08 ms | 56.94 ms |
| 导出前最后 10 秒 | 20.0 FPS | 50.01 ms | 20.91 ms | 47.17 ms |

Game/Draw/GPU 是异步发布读数，不能按同一帧相加或直接配对。GPU trace 提供了进一步证据：首波后 5–10 秒，77 个完整 Graphics GPU Frame 的平均跨度 64.05 ms，与已提交 GPUWork 的平均交集 61.75 ms。持续慢态不是仅靠 CPU 未提交工作造成的时间线空洞。

同一窗口的平均 GPU scope 跨度：

| 阶段 | 每完整 GPU 帧平均跨度 |
|---|---:|
| 整体 SkinCache 更新 | 17.09 ms |
| MorphUpdate 形变更新 | 11.89 ms |
| 动态光追几何更新 | 7.10 ms |
| 阴影深度 | 6.72 ms |
| Hair | 5.94 ms |

这些是范围跨度，父子范围不能重复相加；不等于逐 Actor 独占 GPU 执行时间。

**当前首要异常是相同计算的巨大耗时分化。** 迎宾员同为 162110 顶点的 Normalize，快速派发约 0.0082 ms，慢派发中位约 3.5–3.9 ms，相差约 430–480 倍。慢范围均位于已提交 Graphics GPUWork 区间，不能归因于这段范围内 CPU 没来得及提交；但 GPUWork 仍不能排除驱动层抢占、迁移或资源访问等待。派发顺序不是可靠 Actor ID。

玩家 `SK_Jason_ue_leather_boots` 的 SkinCache 派发范围合计，也由首波前约 0.053 ms/帧升到最后窗口约 5.13 ms/帧；同一网格、分段、顶点参数也出现从微秒级到毫秒级的变化。衣物和怪物同时受影响，优先追共享输出缓冲、内存余量和驱动调度，不能直接判定某个怪 AI 或靴子面数是主因。

DXGI 本地内存报告使用量约 9.16–10.55 GiB，预算约 10.58–10.79 GiB，最小余量约 126 MiB，记录中的超预算值为零。非本地使用约 305–377 MiB。这支持“余量很紧”的判断，**不证明特定 Morph/SkinCache 缓冲已被换出**。RHI 清单含 transient 别名，其总分配量不能当作实际物理显存占用。

## 4. 已归因的额外长帧

### 玻璃破碎特效首次编译

最后窗口的最长帧为 260.39 ms。对齐后的 CPU 栈：

`Ballistics` 232.49 ms → `UNiagaraSystem::RequestCompile` 230.12 ms → `NiagaraAsyncTask_DigestSystem` 214.56 ms。

父子范围相互包含。日志随后明确记录 `NS_GlassShatter_NoMarks` 编译；同段 scope 出现 `WardGlassBurst` 与 `GlassGlints`。源码 `WardBreakableGlass.cpp:265` 在击碎时创建/取出效果实例，`Play:243–245` 设置 Niagara 资产并激活，当前池是首次使用时才逐个创建。

方案：将该确定使用的玻璃破碎系统及材质/PSO纳入进入区域前的准备链，明确等待 Niagara 可运行状态；有界准备少量现有池实例。保留碎片、声音和命中效果，不通过命中时等待编译或跳过效果掩盖卡顿。属于 PIE 编辑器编译路径，不能未经打包证据就声称打包版也有同样 230 ms 停顿。

### 描述符堆与 PSO

本次 28 次 Bindless GPU 描述符堆创建累计约 154.90 ms，最长 11.13 ms。没有复现历史采样的累计 6.26 秒创建停顿；不沿用旧结论把它当作本次持续低帧主因。

另记录到图形 PSO 创建最长 223.73 ms、Compute PSO 创建最长 116.95 ms，分布在不同线程，不能将总和视为游戏停顿时长。它们说明预准备仍有缺口，后续应将首波材质、玻璃特效与动态光追组合的真实使用路径纳入现有 PSO 准备，先确认等待依赖再量化收益。

### 观察开销

本次开启了 RHI 资源清单，基线枚举约 96.19 ms，后台聚合约 108.72 ms；后续枚举约 4.75–5.82 ms。最后面板快照构造每次约 8.73 ms，不能当作每帧都有。最初点击采样本身也有开销。持续数十秒慢态不能都归给面板，但未来同场景对比应保持采样开关一致，资源枚举尽量安排在计时窗口外。

## 5. 刷怪准备池问题

本次提前准备了 11 个实例，正式激活命中准备池只有 3 个；其余 8 个在首波开始后的约 0.14–1.14 秒以 `memory_headroom` 原因被回收。随后对应槽位又走普通创建。第一波 35 个激活中 3 个命中，第二波本次录到的 8 个均未命中。

当前 `FacilityHallSpawnSubsystem.cpp:136–166` 以 1 GiB 余量判断回收压力，虽会优先回收较低优先级实例，仍可回收马上需要激活的当前区域实例。采样显示的问题已从旧版“远处区域占满两个槽位”变化成“临界余量导致准备后又回收”。

方案：区分新准备的准入线与已有准备的回收线，加入滞回；优先停止新分配和回收远处/无效预留，对当前已到期、下一步就会使用的实例优先复用。保留真实硬内存压力时的回收路径。先处理不需要的常驻资源，不能盲目扩大准备池或永久保留所有实例。

本次 `Hall.NativeAllocation` 共 40 次累计约 34.71 ms，`FinishSpawning` 43 次累计约 68.01 ms（不含延后的渲染工作）。因此修好准备池能减少重复初始化，但不能承诺单靠它解决 60 ms 级持续 GPU 慢态。

## 6. 建议实施顺序

1. **完成死亡物理修复的常规构建**，用户复测击杀螳螂及共用布娃娃死亡交接。本轮已落盘两处源码。
2. **落地确定的长帧修复**：玻璃破碎 Niagara/材质/PSO 提前准备；准备池准入与回收分离，减少已准备实例的销毁重建。分别记录改动，不与降画质混杂。
3. **优先定位持续 GPU 慢态**：使用项目现有 `Launch-F6-WddmCapture.cmd` 由用户确认 UAC 后再采集。将迎宾员慢 Normalize 和靴子慢 SkinCache 的资源、父堆、生命周期与 WDDM 调度/迁移关联。本次没有这份数据，不修改引擎同步屏障或盲目提高热堆驻留优先级。
4. **按实际持有者释放多余常驻资源**：结合本次清单检查远处房间持有链及互斥装备实例。只释放确定不再需要且可恢复加载的资源，不因为材质或缓冲体积大就删除。保持画质和怪物数量。
5. **再处理持续基础成本**：动态光追更新、非 Nanite 阴影与毛发阶段；优先排除冻结尸体、不可见且无必要贡献的实例重复更新，再讨论按距离的既有 LOD。以上需要用户同场景体验/后续数据，不在本轮全局关闭 Lumen、光追、阴影或削减怪物。

## 7. 交付与可复用证据

离线分析产物在 `Saved/MantisCrashHallDiagnosis20261022/`：

- `gpu-analysis.json`：分阶段完整 GPU 帧、GPUWork 交集、scope、Normalize 分布。
- `cpu-and-frames-analysis.json`、`clock.json`：原始帧窗口、CPU 对齐和长范围，嵌套值不可累加。
- `cpu-gt.csv`、`cpu-submit.csv`、`cpu-timers.csv`：Unreal Insights 无界面离线导出。
- `analyze_gpu.py`、`analyze_cpu_frames.py`：本次离线分析脚本。
- `trace/ordered/`：GPU 队列顺序重建；不完整边界已从报告窗口中排除。
- `build.ps1`：后台构建脚本，沿用批次互斥并等已有构建退出，不停止其他进程；成功/失败由目标级 `build-FPSGAMEEditor.json` 与 `build-FPSGAME.json` 记录。

本轮构建状态：脚本等待 `Local\CodexUeMcp-Port-8000` 批次锁 10 分钟后超时退出，退出码 1，未提交本轮 UBT。期间共享 Editor 构建曾成功，但随后当前物理源码又有兼容接口修订，Game 构建窗口也仍被占用；不把该共享成功记录当作最终源码的 Editor/Game 完整构建回执。没有停止、重启或协调其他进程。源码已保存，最终普通构建待完成；具体状态见 `completion.json`。

续办结果（北京时间 2026-10-23）：用户授权继续后，死亡崩溃修复与玻璃准备、准备池回收修改一起完成 Game/Editor 的 Win64 Development 常规构建，均退出 0。此前“构建待完成”仅描述首轮状态；最新回执为 `Saved/MantisCrashHallFix20261022/completion.json`，实施说明见 [玻璃准备与刷怪回收](glass-preparation-and-spawn-retention-20261022.md)。未运行游戏测试。

没有进行游戏、视觉、物理或主客机验收。用户复测范围为随机地牢击杀螳螂、共用布娃娃死亡交接，以及后续性能修复后的同场景数据；本轮没有执行这些复测。
