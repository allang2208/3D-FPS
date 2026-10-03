# 性能面板缺陷与优化改进方案

日期：2026-09-22。范围：用户提供的截图、当前 FPSGAME 源码、本机 UE 5.8 引擎源码，以及 Epic 性能追踪文档。

本次完成只读分析与方案编写；没有修改运行代码、资产或配置，没有启动游戏、采样、编译或执行运行测试。下述“确定”指源码中可定位的行为，不表示已经量出其运行耗时。现有文档中的历史诊断仅作背景，没有作为本次新测量结果。

## 1. 这张截图能说明什么

- 显示约 14.7 FPS、平滑帧时间 67.82 ms；面板窗口平均 68.87 ms、P95 72.62 ms。至少在截图对应窗口内，持续低帧明显，不能只关注偶发尖峰。
- Game 65.30 ms、Draw 4.31 ms、RHI 2.29 ms，使游戏线程及其调用链成为优先排查方向。但这些是不同更新点的统计，GPU 取数还有错误，不能据此排除 GPU、呈现同步或编辑器影响。
- Draw 等待 64.80 ms 是等待统计，不能再加到 Game 上当作额外计算量，也不能仅凭等待长就断定在等哪个线程。
- 地板 19.9%、身体 19.6%、仓库箱 14.3% 是手工加权后在当前显示列表中的比例，不是 CPU/GPU 时间占比。不能把 65.30 ms 乘以这些百分比，不能承诺删掉对应物体会获得相同比例的帧率收益。
- 标志改动、武器副本重建在该周期为 0，仅说明已埋点的路径没有计到事件；不能排除其他路径、此前尖峰或未统计的服装重建。
- “7 个每帧强制刷骨骼”“隐藏投影 0”和“峰值 125.00 ms”均存在下面列出的统计问题，不能直接作为优化依据。

## 2. 面板中已确定的缺陷

### F01 / P0：帧时间来自 UI Tick，长卡顿可能被截到 125 ms

位置：`Source/FPSGAME/UI/DevelopmentPanelWidget.cpp:566`、`DevelopmentPerformancePanel.cpp:134`、`FPSPerformanceMetrics.cpp:100`。

采样链是 Widget NativeTick → RefreshPerformance(Delta) → SampleFrame(Delta)。只有面板打开、处于性能页且未暂停时，才追加样本。

本机引擎 `Engine/Source/Runtime/Slate/Private/Framework/Application/SlateApplication.cpp:1676` 的 TickTime 将 Slate delta 限制在 1/8 秒；`Engine/Source/Runtime/UMG/Private/Slate/SObjectWidget.cpp:114` 将控件 delta 传入 NativeTick。因此当前窗口不能充当可靠的原始游戏长帧记录器。截图峰值恰为 125.00 ms 与该限制吻合，但无法从截图还原真实停顿长度。

改进：

- 采集与 UI 显示解耦，在固定的引擎帧边界用单调墙钟记录实际间隔，每帧只记一次；不要改用同样可能受限或受时间缩放影响的 gameplay delta 来替代。
- 记录 FrameId、时间戳、World/PIE 实例、是否暂停/后台/加载；长帧保留原值。
- 面板关闭时允许显式开启的后台记录继续；打开面板查看过去的长帧，避免只看到 UI 已打开的场景。
- 区分“暂停显示”和“停止采集”，增加新会话/清空窗口入口。

### F02 / P0：GPU 使用了错误的计时接口

位置：`FPSPerformanceMetrics.cpp:301` 将 `RHIGetFrameTime()` 赋给 GpuMs。

本机 `Engine/Source/Runtime/RHI/Private/RHIUtilities.cpp:539` 表明它返回的是 RHICalculateFrameTime 基于墙钟计算的 RHI 帧间隔，涉及帧呈现追踪，不是 GPU busy 时间。返回 0 不能解释为显卡无法报告 GPU 计时；返回非零时也不能标成 GPU 执行耗时。

引擎自身 `Engine/Source/Runtime/Engine/Private/UnrealClient.cpp:410` 的 stat unit GPU 数据使用 `FPlatformTime::ToMilliseconds(RHIGetGPUFrameCycles(GPUIndex))`。

改进：对齐本机引擎 stat unit 的 GPU 取数路径，并明确 GPU 索引、有效性和数据延迟。没有有效结果时显示未知/未就绪及来源，不显示 0 ms，不据此判定 CPU 独占瓶颈。RHI 呈现间隔若保留，应单独命名。

### F03 / P1：百分比与“前 N 项占总权重”的公式错误

位置：`FPSPerformanceMetrics.cpp:393`、`DevelopmentPerformancePanel.cpp:153`、`:219`、`:327`。

数据层先截断成前 N 项，UI 再对截断后的列表求 Total，因此同一个组件在“前 20/40/80”之间切换时，百分比会改变。状态文字声称“下列 N 项占统计总权重”，实际代入的是第一项 Rank / 当前列表 Total。截图中的“20%”接近第一行 19.9%，正是这个错误的表现。

改进：截断前保留 AllRankTotal、显示项之和 DisplayedRankTotal，以及每项 Rank。覆盖率用 DisplayedRankTotal / AllRankTotal；每项占全部候选比例用 Rank / AllRankTotal；相对榜首条仍可用 Rank / TopRank，但必须单独标明。建议把榜名改为“资源复杂度线索”，并在标题附近明确“经验权重，无耗时单位”。

### F04 / P1：静态网格的 LOD 链末尾追加了假的 0

位置：`FPSPerformanceMetrics.cpp:55`。

代码假设无效 LOD 返回 -1，实际引擎 `Engine/Source/Runtime/Engine/Private/StaticMesh.cpp:5002` 返回 0；代码先把 0 加入数组再退出。于是一个只有 LOD0 的网格被显示成“120.1K → 0”，并避开“仅 LOD0”的提示。

改进：使用运行时公开的 `UStaticMesh::GetNumLODs()` 枚举真实档位。显示“资产 LOD0 面数”“LOD 链”“当前视图使用的 LOD/未知”三个不同概念，不把资产 LOD0 当成本帧实际绘制面数。

### F05 / P1：7 个“每帧强制刷骨骼”只是配置计数

位置：`FPSPerformanceMetrics.cpp:429`。

只检查 VisibilityBasedAnimTickOption，没有检查组件是否注册、是否启用 Tick、是否有有效网格、是否追随 Leader Pose，也没有统计手动 TickAnimation/RefreshBoneTransforms。

当前项目存在直接反例：`Weapons/RuneSwordComponent.cpp:78` 和 `Production/ProductionToolComponent.cpp:79` 设置 AlwaysTickPoseAndRefreshBones 后又关闭组件 Tick；`Characters/FPSPlayerBodyEquipment.cpp:171` 也关闭世界武器副本 Tick。这些组件依然会被配置统计计入，不能因此认定每帧运行。

改进：将当前字段改名为“配置为 AlwaysRefresh 的组件”，另报注册/启用 Tick/有效资源/Leader Pose/最近渲染状态。真正的更新次数和耗时应覆盖引擎动画路径以及项目手动求值路径，区分动画更新、并行求值、骨骼刷新及等待；总骨骼数仅作资产规模。

### F06 / P1：可见性、隐藏阴影和视锥判断不完整

位置：`FPSPerformanceMetrics.cpp:173`、`:189`、`:348`、`:438`。

- IsVisible 不等价于对当前玩家可见，未区分 bHiddenInGame、Actor 隐藏、OwnerNoSee/OnlyOwnerSee、阴影专用以及实际遮挡。
- 隐藏投影采用 `bCastHiddenShadow && !IsVisible()`，会漏掉 IsVisible 为 true、但 OwnerNoSee 的第一人称身体；没有同时检查 CastShadow 和有效渲染状态。“0”不能排除这些阴影成本。
- GetViewTarget 返回 Actor，把它 Cast 成 UCameraComponent 无法取得实际相机，通常一直使用默认 90°。本机 PlayerCameraManager 的 GetFOVAngle 是公开接口。
- “5 米内一律视锥内”以及方向圆锥近似不能等同于实际视锥，还忽略纵横比和遮挡。

改进：分开列组件可见标志、当前玩家可见性、阴影资格、视锥相交和最近渲染线索。使用正确相机投影与包围盒判定；没有遮挡结果时明确未知，避免显示成“实际可见”。隐藏投影也要区分资格计数与实际 shadow pass 成本。

### F07 / P1：多个重要对象类别实际上漏算

位置：`FPSPerformanceMetrics.cpp:137`、`:206`、`:216`、`:238`、`:246`、`:381`。

| 类别 | 当前问题 | 改进 |
| --- | --- | --- |
| 光源、音频 | 只填写 Primitives，但 ComputeRank 不使用该字段，通常 Rank=0，随即被排除 | 单独分类统计光源覆盖/阴影与活动音源，不套网格公式 |
| Niagara | 专门统计的是旧 UParticleSystemComponent，没有 Niagara 活跃系统/模拟/粒子统计 | 接入 Niagara 的系统、模拟和渲染指标；GPU 粒子数量不可用时显式未知 |
| ISM/HISM | 继承静态网格分支，只读一份资产面数，未记录实例数、可见实例和各实例 LOD | 先补实例总数与可见性口径，不能简单乘总数后宣称实际绘制成本 |
| DynamicMesh 地形 | 不属于 StaticMesh/SkeletalMesh 两个读几何分支，几何量缺失 | 添加本项目运行时地形对应数据源，并覆盖更新/碰撞构建 |
| 纯逻辑系统 | BuildSnapshot 明确排除纯逻辑组件；角色、AI、物理查询、库存、地形/建造任务不在排行中 | 新增按系统计时的 CPU 区，不再试图用网格榜解释游戏线程 |

Nanite 不应因 IsNaniteEnabled 是编辑器构建选项接口就整体放弃。本机 StaticMesh.h:2187 存在运行时 HasValidNaniteData；但“资产有数据”“平台支持”“组件实际走 Nanite”仍须分开，不能由一个布尔值推断本帧路径。

### F08 / P1：面板自身开销低报

位置：`FPSPerformanceMetrics.cpp:395`、`:429`；`DevelopmentPerformancePanel.cpp:156` 以后。

ScanMs 在第二轮骨骼组件遍历之前结束，后续计数聚合未计入。UI 格式化、SetText、控件增长、布局、绘制和面板背景模糊也不属于这个数。截图“扫描 0.3 ms”只能表示前半段扫描，不能解释成整个面板成本。

改进：先将指标命名收窄，并分别计时完整采集、排序聚合、UI 更新。Slate/GPU UI 成本用对应追踪表示；不要将不同线程重叠的时间直接相加。复用同一次遍历获取骨骼信息，静态资产元数据缓存，发生变化时失效；原始样本改环形缓冲，避免数组首部移除。

### F09 / P1：统计窗口与计数器生命周期不一致

位置：`FPSPerformanceMetrics.cpp:100`、`:108`、`:127`、`:397`；`DevelopmentPanelWidget.cpp:580`。

- 顶部 Frame/FPS 使用引擎平滑量，Game/Draw 使用原始量，P95 使用最近 240 次 UI tick；当前只对帧时间保存窗口，没有 Game/Draw/GPU 的同窗分布。引擎 stat unit 自己还会对线程时间平滑，因此“同源”不表示屏幕数值必然相等。
- 240 帧在 15 FPS 下约 16 秒，在 120 FPS 下约 2 秒；两个场景的窗口含义不同。截图仅 72 个样本，P99 实际只依赖末尾很少的样本，置信度不足。
- ClearSamples 没有调用入口，且不重置计数器时间基线；关闭、暂停、重新打开会混入旧样本，第一次快照也会接收到开面板以前累计的事件。
- 计数器为进程级 static，但快照属于 WorldSubsystem。多 PIE/多 World 会混记，任一面板读取即清零，其他消费者可能丢计数。
- `FrameSamples.Num() - LastCounterFrames` 在 240 帧窗口满后恒为 0，且目前算出的 Frames 没有用于输出；现在的标题“每帧动作计数”实际显示周期次数与每秒速率。

改进：每条样本带来源、时间和 World；统一展示所选时窗的均值/P50/P95/P99/峰值，并报告样本量与窗口秒数。采用每 World 单调累计计数和每个读取者的差分基线；用单调帧计数计算次/帧，不用缓冲区长度。

### F10 / P1：动作计数覆盖与解释不准确

位置：`Characters/FPSPlayerBodyEquipment.cpp:29`、`:140`、`:191`；`Characters/FPSPlayerBodyCamera.cpp:37`。

- ApplyOwnerVisibilityFlags 一次调用即使改了三个标志，也只加一次；这不是 setter 次数，更不是实际重建次数。
- 标称 RebuildWeapons/ApplyOutfit 的“装备重建”，实际上只在 RebuildWeapons 加计数；ApplyOutfit 没有计数，而且 RebuildWeapons 在提前 return 之前就已计数。
- UpdateOwnerVisibility 内调用 UpdateWorldOwnerVisibility，二者都递增同一个计数；计数混合了不同层次。
- ApplyWorldBodyShadow 中直接调用的 setter 没有覆盖。
- 本机 PrimitiveComponent.cpp:2088、:2097、:2212 的三个 setter 自己已检查值是否变化，再 MarkRenderStateDirty。旧文档中“每调用一次 setter 都会重注册”的解释不成立；置脏事件也不保证与实际渲染状态重建一一对应。

改进：分别统计请求、实际字段变化、资源创建/销毁以及可取得的实际重建事件；每个事件携带来源和对象。针对本项目可控函数添加作用域计时，不必因为缺少通用“所有组件 tick 耗时 API”就放弃 CPU 归因。

### F11 / P2：界面可读性和预警口径

截图里白色卡片配浅色文字、页签逐字竖排，已经影响读取。`DevelopmentPerformancePanel.cpp:238` 构造的卡片没有设置共享暗色 brush；占比条只创建空 SizeBox，没有有色前景内容。排行中表面上很醒目的白块不应被理解为有效性能条形图。

改进：应用共享 ColdSteelUI 卡片/文本样式，页签禁止逐字换行并设置可用宽度；用有色前景控件实现条形图。把来源、统计范围、未知值原因放在指标附近。颜色阈值应跟随 TargetFps，而当前 BudgetColor 固定 16.7/33.3 ms。第一人称专用手臂没有远距离 LOD 不应与场景物件使用相同告警级别；Nanite 与普通 LOD 也应分开。

## 3. 运行代码中的优化缺陷与候选

这些路径可以从源码定位，但还不能给出它们各自占了多少毫秒。

### A. 阴影开关会被两条路径反复改写，影响优化与隔离判断

`Characters/FPSPlayerBodyCamera.cpp:51` 对身体、武器、配件、服装传入 bCastShadow=true，随后 `ApplyWorldBodyShadow()` 又根据设置改回 false。在关闭身体阴影时，会反复产生不必要的状态变化；因此这个开关并不是干净的阴影成本隔离。

另外 `FPSPlayerBodyComponent.cpp:107` 使用 `WorldBodyShadowEnabled && !IsThirdPersonViewEnabled()`，第三人称会得到 false，与“第三人称保留阴影”的注释相反。

方案：集中计算最终可见性/阴影策略，同一轮只应用一次目标值；第三人称、本地第一人称隐藏投影、远端角色和全局抑制分别定义。所有实际变化通过同一统计入口，不再先开后关。优先级 P1，属于明确状态逻辑问题，但不能据此认定本截图稳态 65 ms 全由它造成。

### B. 未使用的枪械手模仍有后台动画更新风险

`FPSGAMECharacter.cpp:202` 为 AKMViewmodel 配置 AlwaysTickPoseAndRefreshBones；`FPSGAMECharacterProfile.cpp:72` 在切换到非枪械装备时只切可见性。双持左手在 `Weapons/PistolDualWieldComponent.cpp:149` 的 Deactivate 也只隐藏，仍保留网格、动画实例及上述配置。

方案：按实际使用状态管理网格 Tick、动画实例和手动求值入口；非活动装备休眠，重新激活时同步姿态。仍被施法、切换过渡、动作接触点或世界附着使用的骨骼必须保留更新，不可仅凭隐藏标志一刀切。优先记录实际调用次数和耗时，再确定哪些实例可以休眠。

### C. 仓库箱静止时仍保留强制动画配置

`UI/ColdSteelWarehouseChest.cpp:141` 配置 AlwaysTickPoseAndRefreshBones，播放开关箱动作后只把 PlayRate 设为 0，未关闭骨骼组件 Tick。PlayRate=0 不是组件停止 Tick。Actor 本身每帧还执行交互提示逻辑。

方案：开关动画期间更新，结束时固化最后姿态并休眠骨骼 Tick，下一次交互前唤醒；交互提示按距离/状态更新。箱子的 43.4K 面、11 材质槽列为资产优化候选，先核对实际 section 和渲染成本，再决定 LOD、材质合并，保持近景外观与开箱动画。

### D. 稳态装备采集反复构建资源和字符串

`Characters/FPSPlayerBodyComponent.cpp:355` 每约 0.2 秒 CaptureEquipment；`FPSPlayerBodyEquipment.cpp:69`、`:92` 每次遍历材质/子组件、构建数组、软路径和 Transform 字符串，之后才比较 EquipmentKey。

方案：以装备、配件、材质和外观变更事件/版本号触发更新，缓存稳定描述；需要兜底时保留低频同步。把“装备配置变了”和“同一装备正在播放机械动作”分开，避免动态 transform 造成无谓副本重建。由于截图重建计数为 0，本项是可减少的固定工作，不是已确认的主要瓶颈。

### E. 地板、柱子与身体的高几何量只能作为后续资产候选

截图中的地板 120.1K 面、身体 LOD0 92.2K 面以及多个重复柱件值得追踪实际渲染路径。先修正 LOD/Nanite/实例统计，确认阴影、实际可见 section、pass 和 GPU 时间之后，再选择简化平面几何、补 LOD、实例化重复构件或降低阴影代理复杂度。第一人称近景手臂不能因 37.8K 面和“仅 LOD0”就优先降面。

## 4. 检测覆盖中应补的内容

| 优先级 | 补充项 | 用途与边界 |
| --- | --- | --- |
| P0 | 原始帧时间、有效 GPU 时间、同窗 Game/Draw/RHI 分布与等待、采样来源/延迟 | 先保证数据可用于方向判断；未知保留为未知 |
| P1 | CPU 系统计时：角色/武器/身体动画、库存与 HUD、AI/寻路、物理查询、地形与建造队列 | 将几十毫秒拆到可维护的业务模块；区分 inclusive/exclusive 和并行等待 |
| P1 | 动画真实活动：Tick、Update/Evaluate、RefreshBones、手动求值、Leader Pose | 分开资产规模、配置和实际执行，不把总骨骼直接换算成时间 |
| P1 | GPU pass：阴影/VSM、Lumen、BasePass、透明/粒子、后处理及 UI | 通过有效 GPU 计时和按需详细追踪定位；不承诺任意组件都能直接获得 GPU 毫秒 |
| P1 | 内存：进程内存、RHI 分配、显存预算/驻留、纹理流送池及超额 | 各项有交叉，不能简单相加；池超预算不等于整张显卡内存耗尽 |
| P1 | 慢帧事件：GC、同步/异步资源加载、PSO/着色器、碰撞构建、资源创建销毁 | 记录时间戳、最近事件、最大停顿和连续慢帧，区分持续低帧与间歇卡顿 |
| P1 | 环境快照：地图/位置/视角、分辨率/渲染比例、画质、天气、构建、PIE/独立运行、VSync/限帧、前后台 | 使两次数据具有可比性，防止降分辨率或改变场景后误报优化收益 |
| P2 | JSON/CSV 报告、基线对比、筛选/聚合、稳定对象路径 | 保留可复查证据，支持按对象/资源/类别查找变化；记录统计口径版本 |
| 按场景启用 | 联机复制/带宽、活动音源、流送队列、AI 数量与更新频率 | 用于相应场景，不必全部常驻展开 |

详细分析可使用 Unreal Insights 的 CPU、GPU、Frame、Task、Counters、Slate、Niagara、LoadTime 等通道；这是后续方案，本次没有开启追踪。通道含义以 [Epic Trace 文档](https://dev.epicgames.com/documentation/en-us/unreal-engine/trace-in-unreal-engine-5) 为依据。

## 5. 建议的实施顺序与交付边界

1. **修正采样与公式。** 覆盖 F01–F06、F08–F10：可信帧钟、正确 GPU 来源、窗口/会话生命周期、稳定分母、真实 LOD 链、活动骨骼语义、完整扫描计时。数据结构先具备有效/未知/过期状态。
2. **建立 CPU 归因。** 对已定位的自有函数加入作用域计时与次数，补角色、身体/装备、动画、UI、地形/建造和 AI 等系统分组；追踪实际资源重建。等待依赖用时间线进一步辨认，不从单一等待数字猜因果。
3. **处理明确的重复工作。** 先修阴影策略先开后关，按调用证据休眠闲置手模和箱子，改装备采集为变更驱动。每项独立，避免把材质、动画、画质一起改后无法归因。
4. **补齐 GPU/资源/内存分类和 UI。** 保留复杂度线索，增加 Niagara、DynamicMesh、ISM/HISM、光源等专门指标；应用共享暗色样式、修复横排页签和可见条形图。
5. **在可信数据上决定资产优化。** 只对证实有成本的模型、材质、阴影、粒子和地形路径做对应优化。保留动画接触时序、交互、碰撞、存档与近景外观。

当前面板目标是 60 FPS，可继续将 16.67 ms 作为暂定预算，不擅自更改用户目标。收益应报告同条件下 Frame/Game/GPU 的 ms 差值、P95/P99 和内存变化；本次没有前后实测，不能承诺提升多少 FPS。

以后由用户测试时，建议同地点、同视角、同分辨率、画质、天气、存档与运行模式比较。先校准统计，再分项比较；后台轻量记录与打开面板分别记录，以识别 UI 观测开销。这些是待执行步骤，不表示本次已执行或通过。

## 6. 对现有说明文档的修订建议

`Docs/Performance/dev-panel-performance-page-20260922.md` 中以下结论需要同步更正：

- “与 stat unit 同源所以数值必须相等”：漏了平滑、窗口、采样时点和当前 GPU 错误来源。
- “Nanite 运行时无法判断”“静态网格没有公开 LOD 数接口”：本机引擎有可用的运行时数据接口，但资产能力与实际渲染路径要分开。
- “每次 setter 调用都导致重注册”：引擎 setter 有相等值守卫，置脏与实际重建也不是等价事件。
- “7 个 AlwaysRefresh 就是每帧 7 个在求值”“隐藏投影 0 就没有该成本”：当前采集不足以支持。
- “换不同武器仍卡就必然不是武器路径”：共享手模、停用后仍活动的组件和公共动画逻辑仍可能保留。
- “没有通用逐组件 API 就不能计时”：自有函数和系统可以埋作用域事件，通用引擎/并行归因使用对应追踪；不要把资源权重替代成耗时结论。

本次未修改上述原文档，仅在此记录建议，便于后续连同实现一起修正。
