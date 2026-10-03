# 15:54 导出后的分段排查与图标优化

依据 [15:54 导出分析](performance-export-analysis-20260922-1554.md) 和 [实施规划](../UI/performance-attribution-plan-20260922.md)。用户授权边排查边优化；本轮修改源码，未自动运行 PIE、测试、截图或性能采样。

## 已修改

### 图标准备和等待

- `ColdSteelWeaponIcons.cpp` 在同一次蒙皮顶点遍历中分别累积原图标世界坐标、掉落物标准坐标的包围盒，附件继续按各自坐标计算。没有通过旋转一个轴对齐包围盒去近似另一个。
- 将计算好的掉落物包围盒传入 `ColdSteelPickupStudio::Warm`，仍做原有模型预热；`BuildWeapon` 命中已有缓存，省去重复顶点遍历。目标是原捕获中约 9 ms 的第二次计算，实际节省尚未测量。
- GameInstance 内缓存最多 64 套固定配方的图标/掉落物包围盒，延期后重试可复用；仍重新装配、确认可见部件、更新材质及构图。缓存与现有图标/掉落物缓存一样按配方区分，不支持运行中原地编辑同路径资产后的热失效。
- 材质查询使用独立的渲染线程异步结果：未返回、全部就绪、首个未就绪材质索引。查询每约 0.3 秒重新提交，尚未返回时不重复提交。每次尝试只有一次预热 Capture，资源就绪后再做最终 Capture，不因等待而反复渲染同一场景。
- 状态区分首次预热、查询未返回、材质未就绪、纹理正在初始化/流送、纹理未完全驻留但无活动流送；记录首个阻塞资源、已知阻塞持续时间、查询是否仍在进行、本次查询/捕获次数、配方延期次数和包围盒缓存命中。资源列表不是完整依赖列表；异步重新查询期间保留上次已知材质阻塞原因。
- 保留原约 10 秒延期和硬失败回退，不把时间超限当作渲染成功；不降低纹理质量或材质就绪要求。同步 Readback 路径本轮没有改动。

### 慢帧归因

- 新增 `FPSPerformancePhases.cpp`，用现有委托记录 `Viewport.Draw`、`Slate.TickAndDrawWidgets`，以及 `Engine.CoreTickerBoundary` 时间点；绑定在 World 子系统，释放时解绑。
- `Viewport.Draw` 是当前游戏视口的主线程绘制/提交区间，不是 GPU 渲染耗时。Slate 区间覆盖整个进程的控件更新/绘制，可能包含编辑器其他窗口、游戏视口和嵌套工作，不与其他分段相加。
- 本机引擎 `LaunchEngineLoop.cpp` 的正常循环先执行 `FFrameEndSync::Sync`，再执行 CoreTicker；标记点用于把 World Tick 后的区间继续拆小。Slate 后到该点仍包含 RHI、同步、清理及其他回调，不能直接报告为纯同步等待。
- 没有新增引擎二进制修改或强制 Trace。下次导出才能判断原约 35 ms 落在哪个新区间，现阶段没有锁定唯一函数。

### 面板与证据保留

- 新 JSON 版本为 **schema 5**。在原有字段之外增加阶段范围说明、等待诊断、最严重尖峰历史和 World 生命周期限制。
- 最近 16 条 ≥50 ms 历史照常保留；另外保留清空以来最严重的 4 条，按耗时降序、同耗时取较早帧。两类记录都保存前后各最多 2 帧，清空/重启采集清空、停止保留。
- `worst_hitch_history.peak_engine_frame_ids` 列出全部 4 个候选 ID，`entries` 只包含不在 `recent_hitch_history.entries` 的上下文；其余按 session+frame ID 从近期历史解析，避免重复导出相同峰值上下文。
- 总事件容量由 4096 调至 8192、每条长帧上下文由 32 调至 128，以容纳新增委托分段。区间读取按单调结束时间二分定位；同一帧的事件只读取一次供近期/最严重上下文复用，减少采样器自身重复扫描。
- 原性能文字区新增阶段统计、最严重历史和图标等待详情，沿用当前样式、自动换行、滚动及输入行为。

## 下一次导出的判断方向

1. 约 35 ms 若主要在 `Viewport.Draw`，继续跟踪视口构建视图、渲染提交及其同步。
2. 若主要在 `Slate.TickAndDrawWidgets`，区分游戏视口嵌套区间、其他窗口和控件绘制。
3. 若在 Slate 结束到 CoreTicker 点之间，进一步拆分 RHI/帧末同步/清理；不把整个间隙当成同一个等待函数。
4. 用实际 `Icon.SkinnedBounds`、`Pickup.Warm` 和 Capture 事件观察这轮优化后的分布，不能把源码中去掉的遍历直接换算为 FPS 提升。

## 仍未处理与交付边界

- 跨 World 的加载/长帧仍未保留，本轮在 JSON 和界面明确标注了遗漏；需要后续进程或 GameInstance 层的采样器。
- 目录回退图缺失、ASH12/AKM 材质资产错误以及异步 GPU Readback 是后续事项，本轮未更改资产。
- 不承诺帧数提升，不改变画质、动画姿态、玩法、库存或存档。
- 用户保存并关闭项目编辑器后，已完成常规 **FPSGAMEEditor Win64 Development** 构建：204 个动作，`Result: Succeeded`，总耗时 199.44 秒，已链接 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。重新打开项目后使用新版基础 DLL；未启动 UE 或运行测试，由用户测试。
- 构建参数：`-WaitMutex -NoHotReloadFromIDE -NoLiveCoding -MaxParallelActions=4`。日志：`Saved/PerformanceDiagnosis20260922/build-editor-attribution-optimization-1.log`。输出中的 C4996/C4305 位于既有其他代码，没有为消除这些警告扩大修改范围。未进行 Game/Shipping 构建或打包。
