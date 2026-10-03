# 第一批实现：长帧与后台图标计量

本批落实 [修复方案](performance-repair-plan-20260922.md) 的面板可靠性部分。图标、预热、捕获及回读的执行顺序保持现状；异步加载、共享视觉装配和异步 GPU 回读属于后续批次。

## 已写入源码

- 帧缓冲保存完整起止单调时间及引擎帧号。显示/导出同窗的峰值帧、长帧列表和全部原始帧。
- 新增当前 World 的计时事件缓冲（4096 项），预览工作通过所属 GameInstance 上报；事件包含父事件、配方、起止帧号和时间。停止/清空使尚未完成的旧 scope 失效，并报告边界丢弃数量。
- 记录图标 Tick、Studio/角色创建、视觉初始化、配件/包围盒、近战图标准备、掉落物预热/构建/初始化、Capture 提交、Readback 和完成通知。各处增加 CPU Trace scope，未启动 Trace 采集。
- 图标请求、缓存命中、排队去重、失败配方命中、入队、完成、失败和延期在帧边界保存增量。请求年龄与当前处理轮次使用单调时钟，不将累计游戏 Delta 当作实际等待时间。
- 性能页增加“长帧事件”和“后台图标任务”。长帧阈值默认 100 ms，展示最慢 3 帧，JSON 保留全部；现有慢帧阈值 33.34 ms 保持独立。
- JSON schema 3 保留旧汇总字段；后台写入不可变快照，不读取实时 UObject。导出按钮有忙碌状态，旧面板销毁后不会更新旧控件。
- 增加快照构建、导出提交与导出完成标记。完成标记的总历时包含复制/排队/后台写入，不冒充主线程执行时长。

## 导出字段与解释

| 字段 | 含义 |
| --- | --- |
| `session_id` / `capture_generation` | World 指标实例的会话及清空代次；跨窗口按会话和引擎帧号去重 |
| `raw_frames` | 与汇总同窗的完整帧记录；线程/GPU 数据仍是该边界读取的异步发布值 |
| `peak_engine_frame_id` | 帧时峰值的引擎帧号；并列取较早帧 |
| `hitch_threshold_ms` / `hitch_engine_frame_ids` | 长帧阈值与满足阈值的完整帧号列表 |
| `events` | 与帧窗口相交的已完成主线程 scope，以及瞬时标记 |
| `inclusive_wall_ms` | 含等待与嵌套调用的墙钟时间，不是独占 CPU 时间 |
| `parent_id` / `parent_missing` | 调用嵌套关系；父事件未包含在导出中时明确标记 |
| `crosses_window_start/end` | 事件跨越采样窗口边界；保留全长，不悄悄裁短后作为完整分段参与均值 |
| `events_capacity_limited_in_window` | 环形缓冲覆盖了本窗口内事件，不能当作完整记录 |
| `events_overwritten_since_clear` | 本次清空后累计被覆盖的事件数，与当前窗口是否缺失分开 |
| `events_discarded_at_recording_boundary` | 停止或清空时中断的 scope 数，不跨代次拼接耗时 |
| `active_events_at_snapshot` | 快照时仍执行的 scope 数；它们尚未完成，未列入事件数组 |
| `window_icon_actions` | 两个帧边界之间的图标动作增量累计；缓存命中计 Request，不计绘制时 Find |
| `icon_task_at_snapshot` | 当前队列、阶段、缓存和任务年龄，与过去帧窗口的计数分开 |
| `export_requested_at_utc` / `export_submitted_engine_frame_id` | 实际导出提交时间，与冻结快照的原采集时间分开 |

面板的分段均值/峰值仅使用未跨窗的完整事件。Tick 已包含 Prepare，Prepare 已包含预热，不能将这些行相加。掉落物 Warm 的计时包括缓存命中检查，实际模型构建另有 BuildWeapon 事件。

导出完成事件发生在冻结快照之后，会进入后续采样窗口，不能出现在自身文件的过去帧记录中。当前工作仍没有覆盖所有加载、GC、Slate、动画与物理耗时；无已埋点事件相交的长帧继续标明未知。

## 文件范围

- 新增：`Source/FPSGAME/UI/FPSPerformanceEvents.cpp`、`DevelopmentPerformanceDiagnostics.cpp`。
- 指标与导出：`FPSPerformanceMetrics.h/.cpp`、`FPSPerformanceMetricsScene.cpp`、`FPSPerformanceMetricsExport.cpp`。
- 面板：`DevelopmentPanelWidget.h`、`DevelopmentPerformancePanel.cpp`；`DevelopmentTuningPanel.cpp` 仅补现有 NativeDestruct 的导出回调清理。
- 埋点：`ColdSteelWeaponIcons.h/.cpp`、`ColdSteelMeleeIcon.cpp`、`ColdSteelPickupStudio.cpp`、`ColdSteelPickupWeapon.cpp`。

## 构建与运行状态

FPSGAMEEditor / Win64 / Development 常规构建成功；补齐来源不可用状态和导出覆盖说明后的最终增量构建也成功（5 个构建动作，12.69 秒）。日志：[首次构建](D:/FPS3D/FPSGAME/Saved/PerformanceDiagnosis20260922/build-editor-events-1.log)、[最终构建](D:/FPS3D/FPSGAME/Saved/PerformanceDiagnosis20260922/build-editor-events-2.log)。Editor 模块已更新，Game/Shipping 目标本轮未构建。

本轮没有启动 UE、PIE、Trace、截图或运行测试。下次正常打开项目可加载更新，面板实际显示、导出内容与运行表现由用户测试；构建成功不代表已测得性能收益。
