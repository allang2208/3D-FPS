# F6 GPU 驻留与调度采集

本次为现有 UMG 性能记录页增加一枚诊断按钮和状态行，直接接入，未要求预览或测试。

- 入口：F6 → 性能记录。操作区沿用 UWrapBox 和已有按钮样式，新按钮宽 224px，标准操作高度，标签单行；窄窗整枚换行，状态说明占整行并允许正常换行。正文沿用现有滚动容器。
- 数据与职责：UFPSPerformanceMetricsSubsystem 持有记录器；FFPSGpuTraceCapture 管理独立 ETW 会话和 UE trace 文件。按钮只请求开始／停止，窗口仍按现有 0.5 秒状态刷新，变化时更新文字；所有耗时启动、停止和写盘在后台线程。
- 状态：未开始、启动中、记录中、收尾、已停止、权限／提供程序／写盘失败、事件丢失。GPU 记录最长 180 秒；普通性能采集关闭时先按原入口开始新采集。导出按钮在异步收尾期间禁用，完成后显示实际路径。
- 导出：保留当前显示快照语义，即使冻结显示也附带当前 GPU 记录器的文件与元数据；两者时间和 generation 分开保存。导出成功仅表示 JSON 已保存，GPU 侧文件是否完整看状态行及 files_finalized。
- 输入／生命周期：沿用 F6 的焦点、关闭、返回游戏和防穿透逻辑。关闭抽屉不停止记录；清空采样、停止普通采集、世界销毁、引擎退出会停止自己创建的记录；不接管其他 trace。控件绑定仍由当前 WidgetTree 管理，没有新增全局 UI 委托。
- 文件：DevelopmentPerformancePanel.cpp、DevelopmentPanelWidget.h、FPSPerformanceMetrics*、FPSGpuTraceCapture.h/.cpp 和 FPSGAME.Build.cs。复用 ColdSteelUI，不新增图片／材质／场景资产，不改变战斗、怪物或画质。
- 交付边界：必要后台构建与实际运行分开记录；未启动应用、采集或测试，由用户复现后导出。
