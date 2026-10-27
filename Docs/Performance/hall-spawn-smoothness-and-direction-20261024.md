# 迎宾区规则恢复、刷怪准备补漏与持续低帧方向

日期：2026-10-24。用户进一步明确症状是“每次进入一个新场景，开始进入刷怪时就会持续低帧”。因此持续 GPU/资源成本是后续主线；生成预热只能解决其中首次创建的一部分，不能当作持续低帧已经修复。

## 本轮源码修改

- `FacilityEncounterPacing.cpp`：迎宾大厅与分流大厅不再参与按击杀数释放的小组。全部原首波槽位恢复生成资格，四只鼓囊保持两只地面、两只上层。共享队列、原逐只生成间隔和合法落点检查保留。
- `FacilityHallEncounter.cpp`：这两个大厅恢复击杀普通首波过半触发第二波，取消新增的 6 秒等待；任务精英不计入普通首波阈值。其他主题区域的分组规则没有在本轮顺带改写。
- `FacilityMonsterGpuWarmup.*` / `FacilityHallPreparation.cpp`：把鼓囊接入现有同实例的光栅蒙皮预热。使用其实际 AnimationSet.ReferenceMesh 和原 UQuadrupedTemplateAnimInstance，零时间求值并保留正式 BeginPlay 的初始化时机。绝不切成 SingleNode 导致 Wolf::BeginPlay 取不到正确动画实例。
- `DungeonMonsterRenderPreparation.h` / `AuthoredDungeonGenerator.cpp` / `FacilityHallSpawnSubsystem.cpp`：记录本机组件 PSO 缓存是否真的启用，标记编辑器模式不可用；模板/类别提交数不再被解释为已经编译成功的 PSO 数。F6 导出中的准备快照增加覆盖范围说明。

没有扩大准备池、削减怪物、改变画质、AI 攻击规则、奖励或自动 LOD。鼓囊的预热仍受既有准入预算限制，不能声称每一只都会命中；覆盖光栅蒙皮/Morph，不覆盖动态光追、VSM、攻击特效和客户端每实例缓冲。

## 已确认的方向偏差

### 1. PIE 的组件预缓存与打包版不是同一路径

本机 UE 5.8 `Engine/Source/Runtime/Engine/Private/PSOPrecache.cpp:139` 的 `IsComponentPSOPrecachingEnabled()` 明确包含 `!GIsEditor`，资源级入口同样如此。

所以在 PIE 中，调用组件 `PrecachePSOs()` 后 `IsPSOPrecaching()==false` 可能表示根本没有启用组件缓存，不表示已经把实际场景渲染管线准备完毕。项目 ini 中 `r.PSOPrecaching=1` 也不能绕过这条引擎条件。本轮只修正项目可观察状态，不修改引擎全局条件。

最新日志在 2026-10-24 15:45:13 记录累计 50 次 PSO 创建卡顿（29 graphics、21 compute），其中 0 次被归类为 precached。该计数是会话累计值，不能直接当作迎宾大厅独占的 50 次卡顿，也不足以解释所有持续低帧。

官方说明强调加载阶段应等待真实 PSO 请求完成，并区分资产与组件状态。参见 [Epic PSO Precaching](https://dev.epicgames.com/documentation/en-us/unreal-engine/pso-precaching-for-unreal-engine)。本机编辑器排除条件以本地源码为准。

### 2. 当前准备池不是“全部初始化完成的活体对象池”

现有链路为：异步类/资产准备 → 有预算时分配延迟 Actor → 部分物种的真实身体 GPU 预热 → 正式生成时选落点、恢复状态、FinishSpawning → BeginPlay、AI与复制。

这保护了原战斗时钟和奖励规则，但 FinishSpawning、其他组件注册、部分材质/物理/动画初始化仍留在生成时。生成间隔把大批操作分散开，不代表单只怪物的重活已消失。

通用池插件常预先完成 Actor 构造，再通过专用激活/回收接口复用。本项目若采用完整怪物池，需要逐物种明确 AI、音频、Niagara、死亡、伤口、定时器、网络、任务槽与奖励重置。直接把完整 BeginPlay 提前，或直接隐藏已死亡 Actor 复用，会改变玩法状态。

### 3. 旧持续慢态已有 GPU 证据，不能继续只优化生成

2026-10-22 的既有采样里，首波后 5–10 秒平均 Graphics GPU Frame 约 64.05 ms，与已提交 GPUWork 交集约 61.75 ms；相同顶点规模的形变派发出现巨大耗时差异，玩家装备也一起变慢。最紧时 DXGI 本地预算余量约 126 MiB。原记录见 `mantis-crash-and-reception-capture-20261022.md`。

这使共享缓冲、显存压力与持续渲染成为重点；但当时 WDDM 捕获失败，不能据此断言某个缓冲已经被换出。本轮没有新采样，旧结果也不能替代当前改动后的状态。

## GitHub 可学习的实现

以下是读过 README / 相关代码的学习对象，不是已安装或已证明适配本项目的插件。

| 项目 | 适合借鉴的部分 | 本项目使用边界 |
| --- | --- | --- |
| [JanSeliv/PoolManager](https://github.com/JanSeliv/PoolManager) | 有优先级的创建队列、分帧创建、不同对象类型的 Factory、取出/回收回调 | 公开版本面向 UE5.7、MIT。已读 `PoolFactory_UObject.cpp` 和 `PoolFactory_Actor.cpp`；Actor 创建仍在游戏线程，不是把 SpawnActor 扔到工作线程。完整怪物需要自己的休眠与复位合同。 |
| [bennystarfighter/UnrealEngine-ObjectPool](https://github.com/bennystarfighter/UnrealEngine-ObjectPool) | WorldSubsystem 拥有池，初始预建、Push/Pull 和池满行为清晰 | MIT。预建循环会集中在世界开始阶段执行，应借其生命周期接口，不原样复制为一次大量生成。其高频弹丸示例不能换算成本项目的怪物 FPS。 |
| [tomlooman/ActionRoguelike](https://github.com/tomlooman/ActionRoguelike) | UE5.8 示例中的 AssetManager 异步加载、PSO 预缓存与 Bundled PSO 配置，以及实验性的弹丸池/聚合更新 | 已读 README 与 DefaultEngine.ini。适合参考端到端准备流程；部分池化/数据化功能标为实验，不应把其默认动画/画质策略照搬到本项目。 |

可直接阅读的源码：

- [PoolManager 的创建队列](https://github.com/JanSeliv/PoolManager/blob/main/Source/PoolManager/Private/Factories/PoolFactory_UObject.cpp)
- [PoolManager 的 Actor 生命周期](https://github.com/JanSeliv/PoolManager/blob/main/Source/PoolManager/Private/Factories/PoolFactory_Actor.cpp)
- [ObjectPool 的 WorldSubsystem](https://github.com/bennystarfighter/UnrealEngine-ObjectPool/blob/main/Source/ObjectPool/Private/ObjectPoolSubsystem.cpp)
- [ActionRoguelike 的 PSO 配置](https://github.com/tomlooman/ActionRoguelike/blob/master/Config/DefaultEngine.ini)

本轮没有复制第三方实现，也未引入插件。

## 后续按症状排序

1. **持续低帧优先：** 下一次用户采集应覆盖进场前、首波后持续窗口，并带完整 WDDM/UE trace 完成状态。重点判断是 GPU 实际持续执行昂贵工作，还是资源迁移/调度等待；同时记录同屏怪物、显存余量和每实例输出缓冲，避免再凭总 scope 猜某个物种。当前 16 实例/256 MiB 估算池不可盲目增大。
2. **正式运行路径：** 在用户授权采样时用独立的已 cook 构建比较同地图、同种子、同怪数与画质；它用于隔离 PIE 的编译/编辑器影响，不是假设打包必然变快。PSO 依据实际渲染通道补齐，必要时用 [Bundled PSO cache](https://dev.epicgames.com/documentation/unreal-engine/manually-creating-bundled-pso-caches-in-unreal-engine) 覆盖遗漏。
3. **仍有生成尖峰时：** 依据已有 Hall.NativeAllocation / Hall.FinishSpawning / Hall.GpuWarmup 标记拆开成本，把测到的重项迁入受预算约束的准备阶段；完整怪物池先从普通人形的明确初始化/激活合同做起。不能只增加另一层队列。
4. **GPU 持续执行确认后：** 依实际热点消除无贡献实例、重复几何更新和错误常驻引用；保留画质和怪数。Animation Budget / 更激进 LOD / 降低阴影或光追只可作为另需用户决定的取舍，本轮未启用。

“顺滑生成”的关键是把同样的工作提前完成并复用，同时让整个战斗场景持续帧成本在预算内。对象池只解决创建/销毁开销，无法把已存在怪物每帧的昂贵渲染消掉。

## 构建与边界

源码备份、构建脚本和回执位于 `Saved/HallSpawnSmoothness20261024/`。`FPSGAME Win64 Development` 与 `FPSGAMEEditor Win64 Development` 均已后台构建成功，退出码均为 0。用户保存并关闭编辑器后才执行 Editor 构建，没有关闭或重启用户进程。本轮未启动 UE、PIE、commandlet 或测试，不宣称 FPS 已提升或持续低帧已根治。
