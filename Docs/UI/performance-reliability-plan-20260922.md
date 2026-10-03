# F6 性能面板可靠性改造

用户授权实现可靠性修复，帧数优化留待后续。保留现有 UMG 抽屉、F6/Esc 输入和焦点归还逻辑。数据层为当前游戏 World 的 FPSPerformanceMetricsSubsystem；引擎线程/GPU 数据明确标为进程级，不能归到单个 PIE World。

## 结构与布局

页面顺序：帧时间及同窗线程统计、采集状态与环境、已埋点动作计数、资源覆盖、网格复杂度线索。页签与关闭入口固定，内容沿用滚动区；采集控制可换行，长名称换行并提供完整路径提示。沿用 ColdSteelUIStyle、现有字体缩放和黑灰卡片，不新增美术资源。

## 数据、状态与动作

- OnEndFrame 单调墙钟记录实际帧间隔，每引擎帧最多一个样本，保留最近 10 秒；不读 Widget delta，不裁剪长帧。标明容量、实际时长与样本量。
- GPU 使用本机 stat unit 的 RHIGetGPUFrameCycles 来源，无有效读数为未知，注明异步发布与延迟，不伪造同帧关联。
- Frame/Game/Draw/RHI/GPU 使用同一观察时间窗；各列报告有效样本数，目标预算与颜色同源。
- 动作计数属于当前 World，帧边界记录增量，快照非破坏读取；字段变化不是渲染重建次数。
- 场景扫描仅在性能页显示且未冻结时按刷新间隔执行。静态 LOD 按真实数量读取；Nanite 仅表示资产存在数据；实例总量不是可见实例数。
- 排行仅比较可读取几何的网格，总分在截断前计算；其它类型单列覆盖数量，未知数据说明原因。
- 冻结显示不停止采样；停止采集保留历史，重新开始新窗口；清空重置窗口和基线；导出只在用户点击时将显示快照写入 Saved/PerformanceReports。
- 子系统销毁解绑 OnEndFrame，面板关闭不触发额外操作。无数据/停止/冻结/失焦等状态明确标注。不改玩法与存档。

## 文件与交付

修改 FPSPerformanceMetrics.h/.cpp、DevelopmentPerformancePanel.cpp、DevelopmentPanelWidget.h/.cpp，以及玩家身体三个文件中的统计调用。计数接入不改变阴影、动画、装备行为。必要 Game/Editor 构建按实际进程状态安排，不覆盖已加载模块，不自动处置来源不明的未保存资产。

运行测试未要求，由用户测试；构建与接入结果记录在性能页说明中。

## 第二轮：长帧与后台图标记录

对应 [分批修复方案](../Performance/performance-repair-plan-20260922.md) 的第 1 批。只扩展现有 UMG 性能页和计量接口，不修改图标加载、预热、捕获与回读的执行次序。

- 信息顺序：现有帧预算之后增加“长帧事件”“后台图标任务”，然后保留项目动作、资源覆盖与复杂度排行。新内容均在原主体滚动区中，控制按钮继续 WrapBox 重排；窄窗长配方键自动换行，字号和主题沿用现有公共样式。
- 长帧栏目显示阈值（默认 100 ms）、完整帧号、峰值帧、最慢 3 帧及与该时间段相交的已埋点事件。事件只是已覆盖范围内的关联，不自动宣判唯一根因。
- 图标栏目显示快照时队列、阶段与请求年龄，以及帧窗口内动作计数和完整分段的均值/峰值；跨帧等待与执行时长分开。嵌套计时不能相加。没有样本与缓冲截断明确说明。
- 数据由所属游戏 World 的指标子系统提供，预览通过所属 GameInstance 上报。采集独立于页签显示；显示沿用 0.5 秒默认刷新，冻结时数据保持不变。
- 导出复制显示快照后在后台序列化/写入，按钮显示忙碌状态并防止同面板重复提交；成功/失败只更新状态文本，不转移焦点。销毁时使旧回调失效，文件任务可以完成。
- 无新增键盘入口、资产、字体或存档字段。沿用 F6/Esc、滚动与焦点归还。
- 新增实现文件：FPSPerformanceEvents.cpp、DevelopmentPerformanceDiagnostics.cpp。现有改动范围补充 ColdSteelWeaponIcons.h/.cpp、ColdSteelMeleeIcon.cpp、ColdSteelPickupStudio.cpp、ColdSteelPickupWeapon.cpp、FPSPerformanceMetricsScene.cpp，以及 DevelopmentTuningPanel.cpp 中现有 NativeDestruct 的导出回调清理。
- 本批不自动启动 UE、运行测试、截图或性能采集；必要构建单独记录。
