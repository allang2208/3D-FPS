> 后续实施与归因修正见 [本轮优化记录](main-scene-optimization-20260923.md)。本文保留导出分析时的证据；AKM 后续确认是静态材质继承了不适用的骨骼编译标志，不需要压缩原 UV。

# 主场景昨夜导出分析（2026-09-23）

范围：只读取已导出的 JSON、保存记录、项目源码和本机 UE 5.8.2 源码。没有启动或连接 UE，没有运行测试，没有修改玩法源码、材质或地图。本文件是分析与实施建议。

## 数据来源与结论

两份文件实际为 JSON，文件名使用 UTC；以下时间换算为北京时间。

- A，9 月 22 日 23:33：`Saved/PerformanceReports/performance-20260922-153331-D320AE914C4262E74D4BB9B1133D177F.json`。
- B，9 月 23 日 00:16：`Saved/PerformanceReports/performance-20260922-161631-B40F5B924A3F35A48630B283BA9FD818.json`。

均为 schema 8、PIE、`DayNight_Lighting`、D3D12、2552×1222、FOV 107.5，窗口内没有暂停或后台帧。两份 session 不同，相机位置/朝向不同；B 中铺装已有 LOD 链且关闭投影，A 中尚无。不能把两份统计直接当作受控优化前后对照，也不能用这两份旧数据宣称今天修改后的实际效果。

| 指标 | A：23:33 | B：00:16 |
| --- | ---: | ---: |
| 窗口时长 / 帧数 | 8.62 s / 233 | 10.03 s / 481 |
| 平均 FPS | 27.03 | 47.97 |
| 平均帧时间 | 37.00 ms | 20.85 ms |
| P50 / P95 / P99 帧时间 | 36.04 / 47.01 / 93.21 ms | 10.84 / 42.92 / 51.82 ms |
| 窗口峰值 | 225.27 ms | 121.11 ms |
| 超过 16.67 ms 的帧占比 | 96.57% | 38.88% |
| 超过 33.34 ms 的帧占比 | 69.96% | 37.01% |
| GPU0 独立发布读数，平均 / P95 | 31.21 / 33.51 ms | 12.44 / 17.02 ms |
| Draw 独立发布读数，平均 | 37.31 ms | 7.87 ms |

当前证据同时指向：**铺装 LOD 设置有确定错误；反复慢帧的主要已观测区间是 Slate；图标首次准备另有秒级阻塞。** 三类问题应分别处理，不能只继续降低光照质量。

## 1. 确定错误：铺装强制 LOD 写错一位

本机 `Engine/Source/Runtime/Engine/Classes/Components/StaticMeshComponent.h:111` 定义：0 自动选择；正数选择 `ForcedLodModel - 1`。

| 属性值 | 含义 |
| --- | --- |
| 0 | 自动 |
| 1 | 强制 LOD0 |
| 2 | 强制 LOD1 |
| 3 | 强制 LOD2 |

当前三个脚本仍把 1 当作 LOD1：

- `SourceAssets/MainPlaza20260922/apply_plaza_optimization.py`：`FORCED_LOD = 1`。
- `SourceAssets/MainPlaza20260922/build_main_plaza.py:61`：`PAVING_FORCED_LOD = 1`。
- `SourceAssets/MainPlaza20260922/verify_plaza_optimization.py:22`：`WANT_LOD = 1`。

已有 `plaza_level_optimization.json` 的铺装样本明确记录 `forced_prop=forced_lod_model`、`forced_lod=1`、`mesh_lods=3`、`cast_shadow=false`。B 的网格条目也记录了 `[120140, 12014, 3604]` 的 LOD 链与关闭投影。

因此“增加了低面 LOD”和“关闭了铺装投影”有保存证据，但**不能沿用旧文档的“铺装已强制到 12,014 面”结论**。脚本实际上要求 LOD0。78 块铺装按完整资源计算，LOD0 共 9,370,920 面，LOD1 共 937,092 面；这是资源数量对比，不是实测可见面数、GPU 工作量或 FPS 收益。

建议首先修复属性编码，把目标 LOD 索引与 UE 强制属性值分开命名；同步修改已有地图的铺装与重建脚本。资产可用性判断应按实际 LOD 索引检查，例如目标 LOD1 要求 `num_lods > 1`，不要把属性值 2 直接当作索引判断。保持已关闭的铺装投影与原碰撞。

旧文档 `plaza-geometry-regression-20260922.md` 中“约 137 万实际绘制三角面”和“组件数量等于绘制调用次数”的推断不能当作已测结论：当前导出没有实际 LOD、遮挡、section/pass 或 draw-call 数据。本次没有改写旧记录。

## 2. 反复低帧率：已定位到 Slate 区间，尚未定位具体控件或等待

按每个原始帧的单调时钟区间裁剪 `World.Tick`、`Slate.TickAndDrawWidgets` 事件，避免把异步发布的 Game/Draw 数值强行平移对齐。B 的结果：

| B 中的帧组 | 帧数 | 平均帧时间 | World.Tick 平均重叠 | Slate 平均重叠 |
| --- | ---: | ---: | ---: | ---: |
| 小于 16.667 ms | 294 | 9.94 ms | 5.69 ms | 1.59 ms |
| 大于等于 33.34 ms | 178 | 38.97 ms | 5.82 ms | 29.70 ms |

178 个慢帧全部有超过 20 ms 的 Slate 重叠；同组 `Viewport.Draw` 约 0.21 ms，`Icon.Tick` 约 0.08 ms。世界逻辑在快慢帧间变化很小，优先继续拆解 Slate 比盲改角色 Tick 更有依据。

但 **Slate 区间不等于性能面板自身的计算成本**。本机引擎 `SlateApplication.cpp` 中该区间包含所有窗口的 Prepass/绘制与绘制缓冲获取；`SlateRHIRenderer.cpp:686` 的 `AcquireDrawBuffer` 在缓冲忙时还可能执行 `FlushCommands`。需要区分控件布局/绘制、编辑器其他窗口、渲染线程回压。数据没有证明其中哪一项占了 29.7 ms。

性能面板已有的直接开销：B 每次快照平均 1.55 ms，每次 UI 更新平均 4.30 ms，约每 0.5 秒刷新，**不是每帧都付出 5.85 ms**。仍值得做的源码改进是：

- `DevelopmentPerformanceDiagnostics.cpp` 现在按每个阶段重复遍历整个事件数组；改为每份快照单次汇总再显示。
- 只对变化字段设置文本，稳定标题与表格行缓存布局；性能页停止显示刷新时继续后台记录。
- 区分面板 UI 更新、Slate 布局/绘制和 GPU 背景模糊，不把刷新计时作为面板总成本。
- `UpdateLayout()` 已按视口尺寸和缩放值短路，不能误报为每帧重建全部布局；网格榜单也已有行复用。

进一步精准定位适合 Slate Insights 的逐控件更新/失效记录，并配合 CPU 等待调用栈；这里只提出后续方向，没有启动采样。[Epic Slate Insights](https://dev.epicgames.com/documentation/unreal-engine/slate-insights-in-unreal-engine)

## 3. 确定的卡顿来源：图标首次装配仍同步执行

B 的历史记录独立于最后 10 秒窗口：

- 帧 1230：整帧 1,328.82 ms；`Icon.Prepare` 1,239.74 ms，其中 `Icon.InitializeVisuals` 1,100.31 ms，装配与包围盒 135.89 ms。对应 PKM 配方。父子分段包含关系明确，不能再次相加。
- 帧 1365：冰霜剑图标 `Icon.MeleeAssembly` 392.08 ms。
- A 的窗口内：A762 图标准备 55.78 ms，包含蒙皮包围盒 23.02 ms。

当前 `ColdSteelWeaponIcons.cpp` 的 `Prepare()` 仍直接调用 `AFPSGAMECharacter::InitializeWeaponVisuals()`；后者使用多处 `LoadObject` 并初始化武器资源。已有包围盒缓存及异步 GPU 回读可以降低重复工作，但没有消除首次资源加载/装配阻塞。

建议：为当前需要显示的配方建立明确的软引用资源清单，异步加载完成后再装配；把初始化、附件构建、包围盒等主线程工作分阶段执行；固定目录图优先使用已有图片，定制图标按需生成并缓存。不要把所有枪械资源一口气常驻内存，也不要将 UObject 创建移到不安全的工作线程。

`OnReady.Broadcast()` 没带配方键，订阅者调用 `LoadIcons()` 重新刷新库存；B 的 5 次通知各约 4.08 ms。可改为按配方/物品通知与更新。这是小峰值优化，不能解释持续约 30 ms 的 Slate 慢区间。

另外 B 的 4,162.10 ms、3,592.63 ms 历史长帧，分别约有 3,947.65 ms、3,527.55 ms 出现在 `World.Tick` 之前；帧 973 的约 1.15 秒主要位于 Slate 结束到 CoreTicker 标记之间。这些空白没有细分采样，不能全部归因图标、加载、GC 或纯 GPU 等待。

## 4. 确定的资源缺陷：AKM 图标材质编译失败

B 的 `icon_task_at_snapshot.recent_failures` 记录：

- 材质 `/Game/Weapons/ExtMagContinuity20260919/Materials/M_AKM_Continuous_Graph`。
- 骨骼着色器报错：`Too many texture coordinate sets defined on GPUSkin vertex input. Max: 4.`
- 该配方已失败并回退目录图。

当前 `SourceAssets/ExtMagContinuity20260919/install.py:37-38` 使用 UV1，并将连续性数据放入 UV2～UV6，与错误一致。应重排/烘焙连续性权重和法线变换数据，使其适配当前骨骼着色路径并保留接缝效果；不能只延长等待或隐藏错误。

快照另有 M16 材质等待和 M1911 纹理驻留等待。等待年龄是墙钟时间，不是 GPU/CPU 实际占用，不能据此计算帧数损失；失败缓存也意味着 AKM 并非每帧都重试编译。

## 5. 光照、几何和身体优化的优先级

两份快照均有 10 个普通光组件，但**仅 1 个处于启用状态：主方向光**。其余点光/聚光未启用，不能沿用“地牢局部灯太多”的判断。当前灯统计不含 SkyLight，也没有 Lumen、虚拟阴影、雾的 GPU 分项；这些通道仍可能昂贵。

B 的 GPU0 发布读数平均 12.44 ms、P95 17.02 ms；59/481 条读数高于 16.67 ms。GPU 仍有尾部压力，但这些读数没有来源帧 ID，不能断言它们与某个慢帧一一对应，也不能承诺只优化 GPU 就稳定 60 FPS。

几何后续候选：先修铺装 LOD，再考虑柱、矮柱、栏杆按空间分组实例化及兼容资产 Nanite；保留原碰撞、光照支持与剔除粒度。穹顶在导出里仍只有 126,732 面的 LOD0，可补 LOD。避免把整个广场合成一个巨大网格，或仅因源几何榜排名高就降低第一人称模型质量。

身体路径不是本次首要对象：两份均无武器/服装重建、无可见性字段变更；B 的 45 次装备扫描合计仅 2.90 ms。A762 榜单的 285,175 面和 22 材质槽是源资产总量，包含隐藏 section 的可能性；第二份同资产组件明确对当前视图隐藏，不能把二者简单相加当作实际渲染量。

## 面板应补的最小信息

1. 导出 `ForcedLodModel` 原始值、解释后的目标索引、MinLOD/覆盖值；与“资产有哪些 LOD”分开。实际渲染选择未知时仍用 null，不能用配置冒充实际选择。
2. 记录导出时性能页是否展开、显示刷新是否冻结、刷新周期及 UI 模糊配置；现在难以分离观察工具的影响。
3. 将 Slate 进一步分为布局/绘制/等待，或导出关联 Trace 信息。保留“进程级、包含编辑器窗口”的范围说明。
4. GPU 分项和实际渲染分辨率/屏幕比例，兼容时补内存/流送预算、资源加载/编译/GC 标记；采不到时明确缺失。当前 `ScreenPercentage=0` 不是 0% 分辨率证据。
5. 场景资源排名仍只叫几何复杂度；按资产聚合并区分视图隐藏条目，避免 17 块相同铺装挤满 Top20。组件数、材质槽数不等同实际 draw calls。

## 推荐实施顺序

| 优先级 | 工作 | 要解决的问题 |
| --- | --- | --- |
| P0 | 修复铺装 LOD 编码及重建脚本，补面板 LOD 配置字段 | 已确认的优化未按预期生效 |
| P0 | Slate 细分归因；面板单次事件汇总、变化字段更新 | 持续快慢帧交替，区分计算与等待 |
| P1 | 图标资源异步预载、分阶段装配、按配方通知 | 1.24 秒 / 392 ms 级首次卡顿 |
| P1 | 修复 AKM 连续性材质 UV 数据布局 | 明确的资源编译失败与回退 |
| P2 | 广场按空间分组、兼容网格 Nanite、穹顶 LOD | 剩余渲染提交和几何压力 |
| P2 | 根据 GPU 分项再决定阴影、Lumen、雾优化 | 当前报告尚无法归因的 GPU 尾部 |

这些是数据支持的改进方向，尚未实施，也不代表已经达到 60 FPS。
