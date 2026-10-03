# 性能面板可靠性补充：15:08 导出后的修改

状态：用户关闭项目编辑器后，FPSGAMEEditor / Win64 / Development 常规构建成功，Editor 模块已更新；下次打开项目加载。未启动 UE、PIE、Trace、截图、lint 或运行测试。

依据：[本次排查](performance-export-analysis-20260922-1508.md)、[UI 实现规划](../UI/performance-reliability-followup-20260922.md)。本轮继续面板可靠性阶段，没有修改枪械材质、图标生成调度、场景画质或游戏玩法；不宣称 FPS 提升。

## 已写入源码

- 最慢 3 帧始终显示，不再被 100 ms 门槛过滤。按超目标预算、超过慢帧门槛、≥50 ms、≥100 ms 统计累计数量。旧 `hitch_engine_frame_ids` 字段保留，默认门槛改为 50 ms；JSON 同时保存真实阈值。
- 最近 16 次 ≥50 ms 长帧独立于 10 秒窗口保留，包含前 2/后 2 帧及最多 32 条相交事件。短窗口之外仍可导出；缺失前后帧、历史覆盖、事件容量限制及边界时未结束分段均显式记录。清空/重新开始采集清除这份性能历史，停止采集不再补录后续帧。
- 保留原始线程读数，并在数值旁说明独立发布和未对齐。机器可读字段将来源帧号、发布时间标为 null；不靠固定移动一帧或重复数值猜测发布状态。
- 图标失败保留最近 32 条详情：配方、阶段、资源、错误、UTC/单调时间、帧号及目录图回退状态。原因超过 2048 字符显式标记截断。面板显示最近 3 条，悬停展开配方与资源；JSON 保存全部保留详情。
- 材质编译、无材质代理、回读像素数、空图和纹理创建失败分别给出原因；其他 Prepare 失败明确标为缺少细分原因，不猜测具体资源。图标业务失败集合和回退行为保持原样，清空性能采样不会重试失败图标。
- 增加 `World.Tick`、`PlayerBody.EquipmentCapture`、`PlayerBody.OwnerVisibility`、`PlayerBody.WorldVisibility`、`Panel.UiUpdate` 分段。World Tick 只绑定当前游戏 World，销毁时解绑；停止/清空沿用事件代次规则。子分段包含在 World 等外层工作中，不重复累加。

## JSON schema 4

保留 schema 3 的原始帧、事件和汇总字段；新增：

| 字段 | 范围与解释 |
| --- | --- |
| `frame_severity` | 同一 `raw_frames` 窗口的累计门槛计数；类别重叠，不相加 |
| `slowest_engine_frame_ids` | 同窗最慢 3 帧，无门槛过滤；相同帧时优先较早帧 |
| `thread_timer_alignment` | 发布源说明、未知来源帧号/发布时间、不可同帧归因状态 |
| `recent_hitch_history` | 当前采集代次的有限历史，独立于滚动窗口；按 session + frame 去重 |
| `icon_task_at_snapshot.recent_failures` | GameInstance 当前仍失败配方的最近详情，独立于性能代次 |

历史事件的 `crosses_window_start/end` 相对于该条历史的前后帧上下文区间；完整事件时长保留，`parent_missing` 按实际保留事件重新计算。不同历史项之间的上下文和事件可能重叠，不能将其重复累加。仍在进行的分段没有最终时长，历史记录不保证覆盖所有 CPU/引擎内部工作。

失败详情在新代码加载后的失败路径产生，不从旧日志猜测并回填当前状态。ASH12/AKM 的材质错误尚未修复；新详情用于明确显示此类失败。

## 文件范围

- 新增 `Source/FPSGAME/UI/FPSPerformanceHitches.cpp`。
- 指标：`FPSPerformanceMetrics.h/.cpp`、`FPSPerformanceEvents.cpp`、`FPSPerformanceMetricsExport.cpp`。
- 展示：`DevelopmentPerformanceDiagnostics.cpp`、`DevelopmentPerformancePanel.cpp`。
- 失败详情：`ColdSteelWeaponIcons.h/.cpp`。
- 项目计时：`Characters/FPSPlayerBodyEquipment.cpp`、`FPSPlayerBodyComponent.cpp`、`FPSPlayerBodyCamera.cpp`，仅在已有入口加入计时 scope。

## 生效和后续范围

本轮扩展了带资产快照结构与子系统成员布局，已在用户关闭项目编辑器后完成常规 Editor 构建。204 个构建动作，耗时 218.35 秒，结果 `Succeeded`；已链接 `UnrealEditor-FPSGAME.dll`。未启动编辑器、未进行跨任务协调。构建日志：[build-editor-reliability-followup-1.log](D:/FPS3D/FPSGAME/Saved/PerformanceDiagnosis20260922/build-editor-reliability-followup-1.log)。本次没有构建 Game/Shipping 目标。

实际显示、导出与操作由用户测试；构建成功不代表运行验证。持续约 30 ms 的周期帧、约 62 ms 等待的具体来源、材质修复和首次图标生成的异步改造继续按后续证据与授权推进。
