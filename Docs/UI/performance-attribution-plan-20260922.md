# 15:54 导出后的排查与优化

用户已授权边排查边优化。本轮面向 Windows Development Editor、DayNight_Lighting 的既有导出：普通慢帧在 World Tick 后多出约 35 ms，M1911 准备中两次蒙皮遍历约占 18 ms。此记录是实施范围，不宣称改后性能。

- 沿用 F6 性能页、当前主题、字号、自动换行与主体滚动区，只扩展已有长帧和图标文字块；无新输入、焦点、弹窗、存档或资源写入。
- 增加游戏视口 Draw、Slate TickAndDrawWidgets 的主线程包含式区间，以及 CoreTicker 回调时间点。使用引擎已有委托，不修改引擎。Slate 属于整个进程，CoreTicker 点在正常引擎循环的帧末同步之后，但不能将点之前的整段命名为同步等待。
- 最近 16 条长帧之外，独立保留清空以来最严重的 4 条 ≥50 ms 长帧及前后各 2 帧；相同峰值保留较早帧。JSON 去重引用，停止保留、清空/重启采集清空。增加事件容量以容纳新增分段。
- 图标同一次蒙皮顶点遍历分别计算原图标坐标和原掉落物坐标的精确包围盒，供预热复用；缓存固定配方的两套结果，避免延期后重复遍历。保持原姿态、可见部件、镜头构图和碰撞盒语义。
- 材质就绪检查改为独立的异步轮询，区分尚未返回、材质未就绪和纹理等待；预热 Capture 每次尝试只提交一次，就绪后再最终捕获。记录等待资源、持续时间、轮询/捕获次数及延期次数；不降低纹理就绪要求或将超时直接视为成功。
- 依然保留原 10 秒延期策略和图标失败回退。本轮不修改材质资产或目录图片，不把跨 World 加载混入帧窗口；导出明确标注生命周期遗漏。
- 修改范围为 FPSPerformanceMetrics/Events/Hitches/Export、新增 FPSPerformancePhases、DevelopmentPerformanceDiagnostics、ColdSteelWeaponIcons、ColdSteelPickupStudio。无需网络同步或蓝图 API 变化，委托随 World 子系统释放，缓存随 GameInstance 释放。
- 修改涉及原生对象布局，完成源码后安排常规 Editor 构建；保留正在运行的编辑器现场。未要求运行测试、PIE 或截图，由用户测试。
