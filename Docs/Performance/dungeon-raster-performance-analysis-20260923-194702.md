# 关闭光追后的地牢性能排查：2026-09-23 19:47

> 本文记录关闭光追状态下的历史样本。用户随后要求恢复原光照，恢复已完成，见 [恢复记录](lighting-baseline-restoration-20260923.md)。本文统计不能当作恢复后的性能结果。

本次按用户要求读取新导出、日志、当前 CVar 和相关代码；没有修改游戏配置、源码或资产，没有启动/重启编辑器或游戏。只新增诊断脚本、分析结果和本文。

## 结论

光追已在当前编辑器启动时禁用，但缺少可比的关闭前基线，不能给出光追单项提升百分比或净显存释放值。

最新有效地牢窗口平均 **31.43 FPS**，GPU0 发布耗时平均 **6.41 ms**。当前最明显的慢帧集中在主线程的 **Slate 窗口 Paint 区间**：174 个慢帧中，每帧平均 49.72 ms，Paint 平均占 40.03 ms。应首先细分这个区间，不能继续把低帧率统一归因于 GPU 光照，也不能直接把 Paint 时间归因于某个游戏 HUD 控件。

## 数据和场景

- 用户导出：[19:47 原始 JSON](../../Saved/PerformanceReports/performance-20260923-114702-3EBC98344BEA9D5EB2CB2887F9F24597.json)。
- 统计结果：[分组和区间计算](../../Saved/PerformanceInvestigation20260923/export-194702-analysis.json)；[可重复的离线分析脚本](../../Saved/PerformanceInvestigation20260923/analyze_export.py)。脚本取同阶段区间的并集并裁剪到帧边界，不叠加重叠阶段。
- UE 5.8.2，PIE，`L_Dungeon_Randomized`，D3D12，2552×1222，FOV 107.5。
- 相机 `(11161.43, -6217.73, 266.15) cm`；种子 `1182907040`，生成状态 ready。
- 窗口 10.0237 秒、315 帧；后台 0 帧、暂停 0 帧。
- ScreenPercentage CVar=0（默认策略，不能只凭该值判定实际内部渲染分辨率）、VSync=0、MaxFPS=0。
- 快照/导出时性能面板打开，页签 3，刷新 500 ms，模糊强度 9/半径 21。只代表端点，不代表整个窗口。

| 指标 | 平均 | P50 | P95 | 峰值 |
| --- | ---: | ---: | ---: | ---: |
| 帧时间 | 31.82 ms | 47.75 ms | 50.75 ms | 83.91 ms |
| GPU0 发布耗时 | 6.41 ms | 6.37 ms | 7.51 ms | 10.52 ms |
| Draw 发布耗时 | 4.36 ms | 4.22 ms | 5.36 ms | 6.56 ms |
| RHI 发布耗时 | 2.26 ms | 2.15 ms | 3.03 ms | 5.08 ms |

174/315 帧（55.24%）超过 33.34 ms，45 帧达到 50 ms，无 100 ms 以上帧。GPU/线程计时独立发布且未对齐，不做逐帧因果对应，不把 Game、Draw、RHI、GPU 相加。

## 1. 首要方向：窗口 Paint 内的周期性停顿

| 帧组 | 帧数 | 平均整帧 | Paint 区间平均 | World.Tick 平均 |
| --- | ---: | ---: | ---: | ---: |
| ≥33.34 ms | 174 | 49.72 ms | 40.03 ms | 5.67 ms |
| <33.34 ms | 141 | 9.73 ms | 0.86 ms | 5.42 ms |

315 个 Paint 事件均属于 `FPSGAME - 虚幻编辑器` 窗口。项目 `FPSPerformancePhases.cpp` 的埋点绑定 `FSlateDebugging::BeginWindow/EndWindow`；本机 UE 的 `SlateApplication.cpp:1265` 到 `:1275` 将它们放在 `PaintWindow` 调用两侧。这里是主线程墙钟区间，可能包含嵌套工作或等待，仍不等于纯 CPU 指令执行时间，更不等于 GPU 界面耗时。

性能面板的两次 Snapshot/UiUpdate 出现在窗口第 9.025/9.554 秒附近，共约 11.07 ms。前 8 秒已经平均 31.08 ms/帧，255 帧中有 138 个慢帧。因此不能将持续约 40 ms 的 Paint 直接解释为性能面板的两次扫描，也不能据此保证关闭面板就恢复帧率。

建议下一步对同一场景做 CPU/Slate 调用栈采样，定位具体 Paint 子树或阻塞函数；再比较相同种子/机位下的编辑器界面与游戏 HUD 贡献。当前 JSON 到窗口粒度为止，未提供控件级调用栈，不能据此任意删减 HUD 功能。

本窗口房间灯光调度共 101 次、累计 4.29 ms（单次峰值 0.13 ms）；Icon.Tick 累计 17.30 ms；装备预览提交区间 43 次共 1.63 ms。这些已覆盖的主线程区间解释不了持续 Paint 停顿；也不能用它们排除其未覆盖的 GPU/引擎开销。

## 2. 阴影和几何的具体遗漏

快照共 156 盏局部灯，86 盏启用，82 盏带阴影标志。视锥/距离筛选留下 17 个候选，全部带阴影标志；这是保守候选，不是实际绘制数量。

其中 **12 个候选距相机 99.6–125.7 m，MaxDrawDistance 全为 0（未设置距离上限）**。包括 `DGN_Link_InspectionLight`、`DGN_A_AV2_Light_*`、`DGN_A_Room_RU_WorkLightSource`、工作台 Spot/Rect 灯。它们没有生成房间的角色标签。源码 `AuthoredDungeonLighting.cpp` 的调度只处理注册到 `LightModules` 的灯；生成器明确保留起始区灯光。应补齐这批旧场景/起始区灯的距离与房间管理，保留近处主灯和实体遮挡。

全场注册网格按 LOD0/回退几何乘实例数合计 **21,730,372** 三角，其中 Tiles 命名资产 **12,009,990（55.27%）**。这是源几何统计，不能当作每帧实际绘制三角或 GPU 成本比例。

复杂度最高的 20 个组件全部 `has_nanite_asset_data=false`，且只含一个 LOD。主要包括 841,008 面的 Boss 地砖、520,373 面的 Drainage 地砖、511,905 面的 Freight 地砖、454,922 面的 Ventilation 地砖。应优先处理大量重复地砖/栏杆的几何密度和 LOD，再评估适合的刚体使用 Nanite、实例化；保留轮廓、碰撞和近景缝隙。

当前导入脚本仍有回退入口：`SourceAssets/DungeonUnderground20260923/Scripts/import_assets.py:33` 和 `SourceAssets/DungeonGoddessStatue20260922/Scripts/import_diana.py:195` 显式关闭 Nanite。只处理已保存资产而不处理后续导入规则，仍可能重新引入高面数单 LOD 资产。

当前启动日志在 19:46:36 记录 VSM 非 Nanite 标记队列溢出，处于新导出同一编辑器会话。VSM 是保留下来的普通阴影路径；其非 Nanite 成本独立于硬件光追。[Epic VSM 文档](https://dev.epicgames.com/documentation/unreal-engine/virtual-shadow-maps-in-unreal-engine)建议适用网格优先 Nanite、其余配置完整 LOD，并注意缓存失效。

## 3. 纹理流送和武器图标

- 19:39 启动日志最终 `Texture pool size now 1000 MB`；19:48 当前 CVar 读取同样 `r.Streaming.PoolSize=1000`。启动时较早的 7129 MB 日志不能当作最终流送池设置。
- 新导出图标队列剩 8 项，当前 M16A2 图标等待 `TextureNotFullyResident`，本窗口 4 次延后；请求年龄约 112 秒是等待历时，不是 112 秒 CPU 工作。
- ASH12 一个材质编译失败：`Too many texture coordinate sets defined on GPUSkin vertex input. Max: 4.`，已使用目录图标回退。这是独立材质问题，不能把本次 Paint 停顿归因于它。
- 后续应先记录实际纹理需求、总显存预算和流送超量，再制定分档预算与纹理尺寸；图标材质修复、预生成和缓存可以减少重复等待。不能把 PoolSize 设置为无限，也不能把显卡总容量全部分给纹理。

## 4. 关闭光追究竟省了多少

`Saved/Logs/FPSGAME.log:1140`：`Ray tracing is disabled. Reason: disabled through project setting (r.RayTracing=0).`

本轮只读 CVar 回执：[19:48 状态](../../Saved/PerformanceInvestigation20260923/current-scene-20260923-114813.json)。其中 RT、Lumen、PathTracing、MegaLights、DFAO、距离场阴影、SSR/SSGI 为 0；VSM=1，SMRT 射线数=0，普通阴影继续保留。该脚本的首次网格三角 API 读取失败，**仅采用其中成功读取的 CVar，不采用其几何统计**；地牢几何结论全部来自用户 JSON。

关闭硬件光追会去掉相应的光追加速结构建设和追踪工作；BLAS 本身也消耗显存。[Epic 光追性能说明](https://dev.epicgames.com/documentation/unreal-engine/ray-tracing-performance-guide-in-unreal-engine)

但旧截图的 606.145 MiB 常驻/617.06 MiB 请求量属于光追几何池统计，**不是总显存前后差值**。新 JSON 没有显存遥测或细分 GPU pass，无法报告实际释放量。

关闭前唯一地牢导出在地下约 1.8 km，且有 17 个后台帧；其余旧样本是不同机位的主场景。新样本种子也不同，并包含地牢生成等其他改动。不能用旧 12.96 FPS 对新 31.43 FPS 宣称光追优化倍数，也不能拿主场景的旧 GPU 时间与本次地牢 GPU 时间相减。

精确收益需要相同内容版本、种子、机位、渲染分辨率、画质、运行模式、前台状态和采样窗口的隔离 A/B，并记录 GPU pass 与显存预算。本轮没有重新开启生产项目的光追。

当前可确认的是：这个观察窗口的 GPU 耗时低于 60 FPS 的 16.67 ms 帧预算，而界面/编辑器 Paint 区间仍出现大量约 40 ms 停顿。优先定位该停顿，再处理远处灯、几何和纹理预算，比继续整体关闭阴影更有针对性。

## 5. 对“视觉重调成本高、帧率收益不明显”的评估

用户在收到新数据归因后指出：全面移除后要重新处理各场景光照，但体感帧率没有明显改善。

**以解决当前已测地牢卡顿为目标，这个性价比担忧有依据；目前没有数据证明继续重调所有场景值得。** 这不等于证明光追在任何场景都没有开销，也不能把本次一个机位推广成全项目 GPU 基准。

本次落盘范围不仅是硬件 RT 开关：`r.DynamicGlobalIlluminationMethod=0`、`r.ReflectionMethod=0`、`r.Lumen.Supported=0`，并关闭距离场 AO、SSR/SSGI、接触阴影、SMRT 软阴影采样。项目原本 `r.AllowStaticLighting=False` 继续保持，因此移除动态间接光后也没有自动接替的烘焙 GI。太阳/点光源仍存在，但原有反弹光、部分遮蔽、反射和软阴影效果同时变化，原配光数值自然不能保证维持外观。这应被描述为光照方案迁移，而非已经证明有效的帧率优化。

硬件 RT 与 Lumen 效果不是不可拆分的开关；Lumen 也有软件距离场追踪路径，见 [Epic Lumen 技术说明](https://dev.epicgames.com/documentation/unreal-engine/lumen-technical-details-in-unreal-engine)。保留自动间接光、关闭硬件 RT 是可以单独评估的路线，但软件 Lumen 仍属于追踪，恢复它会改变此前“全部剔除”的项目路线，也不能保证无需配平或必然更快。

当前建议：暂停进一步逐关卡重做配光，先定位约 40 ms 的 Paint 停顿，再用同场景数据决定保留/恢复哪些光照效果。共享天空蓝图和预设可以集中处理共性问题；不能未经逐场景检查就断言每张关卡一定要全部手工重做。本轮仅完成评估，未回滚或重新开启任何追踪功能。
