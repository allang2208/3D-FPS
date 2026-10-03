# 性能离线排查：图标生成阻塞与面板统计遗漏

日期：2026-09-22。用户当前无法使用 UE，本次仅读取已有导出、日志及项目/引擎源码，生成分析记录；没有启动或操作 UE，没有修改游戏、面板源码或运行测试。

## 结论

两份性能导出中的秒级卡顿，已经有很强的证据指向**实时武器图标准备链路中的同步资源加载、资产就绪等待和角色初始化**。图标准备还同步调用掉落物模型预热。当前面板的 Game 时间包含这些工作，但场景列表和玩家身体计数没有覆盖它们，无法据计数为 0 排除后台重建。

这项发现解释的是长卡顿路径。约 54 ms 的典型帧时间仍未完成耗时归因，不能承诺改完图标就恢复目标帧率。

## 证据来源与帧号对齐

- [导出 A](D:/FPS3D/FPSGAME/Saved/PerformanceReports/performance-20260922-051503-C02E29044521E9F96A5BDFA58D507A72.json)：UTC 05:15:03.083，帧 927–1086。
- [导出 B](D:/FPS3D/FPSGAME/Saved/PerformanceReports/performance-20260922-051511-EFE4B8D14B65CE6091AAC38CE454CB58.json)：UTC 05:15:11.535，帧 1069–1225。
- [原始运行日志](D:/FPS3D/FPSGAME/SourceAssets/FrostSpiritBurst20260922/editor-load.log:58082)：时间与两份导出一致。
- [保留原始行号的日志摘录](D:/FPS3D/FPSGAME/Saved/PerformanceDiagnosis20260922/icon-hitch-log-evidence.txt)。
- [结构化关联记录](D:/FPS3D/FPSGAME/Saved/PerformanceDiagnosis20260922/icon-hitch-correlation.json)。

UE 的日志方括号帧号是 `GFrameCounter % 1000`，见 [OutputDeviceHelper.cpp](<E:/Program Files (x86)/UE_5.8/Engine/Source/Runtime/Core/Private/Misc/OutputDeviceHelper.cpp:35>)。面板在 `OnEndFrame` 保存完整 `GFrameCounter`，引擎在该回调后递增计数，见 [面板采样](D:/FPS3D/FPSGAME/Source/FPSGAME/UI/FPSPerformanceMetrics.cpp:117) 和 [引擎帧尾](<E:/Program Files (x86)/UE_5.8/Engine/Source/Runtime/Launch/Private/LaunchEngineLoop.cpp:6127>)。结合时间与导出范围，可以将日志 `[69]` 对齐到 1069、`[176]` 对齐到 1176。

下面区间从同帧第一条 `FlushAsyncLoading` 到 `WeaponIcon: prepare` 完成日志。它是**同帧内已经观察到的墙钟时间跨度**，不是完整帧时，也不是某一个函数独占的 CPU 耗时。它包含加载、等待、初始化，以及期间可能执行的其他工作。

| 引擎帧 | 本地时间 UTC+8 | 准备对象 | 同帧日志跨度 | 导出范围 |
| --- | --- | --- | ---: | --- |
| 927 | 13:14:52.691–13:14:53.057 | DW715 | 366 ms | A |
| 1008 | 13:14:57.412–13:14:57.630 | M1911 | 218 ms | A |
| 1069 | 13:15:00.936–13:15:01.915 | A762 | 979 ms | A、B |
| 1176 | 13:15:08.139–13:15:08.770 | AKM | 631 ms | B |

A762 这一帧还出现 `正在等待蒙皮资产就绪（SK_A762_Manny）`，随后两条 `GUNPLAY_FX_READY`、掉落物构建完成、图标准备完成。979 ms 高于 A/B 各自第二慢样本 424.97 / 718.23 ms，而且在共同窗口内，因此它与两份相同的 1065.37 ms 峰值高度吻合。当前 JSON 未导出原始帧记录/峰值帧号，这仍是日志与汇总交叉推断，不能写成“InitializeWeaponVisuals 独占耗时 1065.37 ms”。

DW715、AKM 的同帧跨度分别与 A/B 的第二慢帧接近，但不据此断言逐帧精确对应。

## 调用链与具体缺陷

```text
ColdSteelInventoryWidget::LoadIcons
  → WeaponIcons::Request（加入队列，已有去重）
  → WeaponIcons::Tick，Stage 0
    → Prepare（整段在同一次 Tick 内完成）
      → 图标预览场景中的 FPSGAMECharacter::InitializeWeaponVisuals
        → 同步 LoadObject：网格、动画等；设置网格时可能等待资产就绪
      → 配件装配、CPU 蒙皮顶点包围盒计算、渲染资源更新
      → PickupStudio::Warm
        → 临时 Pickup::BuildWeapon
          → Acquire 另一套角色；首次创建时 InitializeWeaponVisuals
          → 装配、包围盒计算及临时组件建立
    → 后续帧检查材质/纹理就绪并 CaptureScene
    → Readback：ReadLinearColorPixels → FlushRenderingCommands
```

1. **分阶段队列没有限制首次准备的阻塞时间。** [Tick](D:/FPS3D/FPSGAME/Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp:177) 在 Stage 0 直接调用完整 `Prepare`。后续阶段虽然会让出帧，但不能打断前面的同步加载。10 秒任务超时也不能给这一段提供单帧预算。

2. **静态图标复用了完整的武器玩法初始化。** [InitializeWeaponVisuals](D:/FPS3D/FPSGAME/Source/FPSGAME/FPSGAMECharacter.cpp:286) 不只取图标所需网格和姿态，还加载开火、瞄准、换弹等动画并初始化武器特效。函数开头先同步请求 AKM 网格，再按当前定义覆盖；M4 弹鼓动画也先无条件请求，再由部分武器覆盖。已缓存的资源请求未必再次发生磁盘读取，但这些依赖和初始化对图标而言过重。

3. **图标和掉落物预热同步耦合。** [Prepare](D:/FPS3D/FPSGAME/Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp:140) 调用 [Warm](D:/FPS3D/FPSGAME/Source/FPSGAME/UI/ColdSteelPickupStudio.cpp:27)，再进入 [BuildWeapon](D:/FPS3D/FPSGAME/Source/FPSGAME/UI/ColdSteelPickupWeapon.cpp:23)。两个 Studio 各自维护角色。A762 的 `DropTiming: model 26.779 ms` 只计掉落物构建这一小段，不能用它代表整个图标准备的 979 ms。两条 FX 初始化日志与这条双角色路径一致。

4. **图标回读是另一处确定存在的同步等待点。** [Readback](D:/FPS3D/FPSGAME/Source/FPSGAME/UI/ColdSteelWeaponIcons.cpp:144) 调用 `ReadLinearColorPixels`；[本机引擎实现](<E:/Program Files (x86)/UE_5.8/Engine/Source/Runtime/Engine/Private/UnrealClient.cpp:129>) 提交读回命令后执行 `FlushRenderingCommands`。这次没有回读分项时长，不能把它说成本次秒级尖峰的主因。

5. **任务请求没有跟随实际抽屉可见状态。** [LoadIcons](D:/FPS3D/FPSGAME/Source/FPSGAME/UI/ColdSteelInventoryWidget.cpp:71) 会请求背包/装备中的武器图标，在初始化、构建和数据变化时调用；没有检查抽屉是否打开。因此存在离屏图标仍入队的路径。本次导出没有背包开关状态，无法确定用户当时是否关闭背包。队列已经有 Pending/Cache 去重，不应误报为每次刷新都重复生成全部图标。

## 面板应先补什么

当前组件遍历限定在 [当前 World](D:/FPS3D/FPSGAME/Source/FPSGAME/UI/FPSPerformanceMetricsScene.cpp:186)，动作计数也明确只埋在玩家身体路径。图标和掉落物使用另外的 Preview World；它们的 GameInstance 子系统工作不会自动进入这些计数。

| 优先级 | 改进 | 数据口径 |
| --- | --- | --- |
| P0 | 导出原始长帧记录：引擎帧 ID、单调时间、帧时和事件标记 | 与加载、图标准备、预热、回读、导出事件对齐；窗口重叠按帧 ID 去重 |
| P0 | 图标队列长度、当前物品/阶段、缓存命中，以及准备/预热/回读的次数和耗时 | 分开记录单次执行时长与跨帧任务等待时长；不能把数秒的队列等待算作连续 CPU 阻塞 |
| P0 | 区分进程计时、当前游戏 World、预览场景与已埋点子系统 | 保留目前范围说明；为未覆盖项显示“未采集”，不以 0 代替未知 |
| P1 | 记录资产加载/就绪等待、GC、实际 UI 开关状态及导出耗时 | 事件携带帧号；区分“开始到返回”的执行时长与“相邻通知间隔” |
| P1 | 补 Game 内部分类：游戏 Tick、Slate/编辑器、动画/物理等 | 用于解释约 54 ms 的典型帧；嵌套或并行耗时不能简单相加 |

最小可靠性改动应先覆盖这次已经暴露的图标路径，并保留原始长帧证据。没有必要为了统计预览组件而每帧扫描整个 UObject 系统；可由对应子系统主动上报自身队列、阶段和事件。

## 后续优化方案

在面板能记录上述证据后，再按以下顺序修改性能路径；本次未实施这些游戏逻辑变化。

1. 保留现有目录图作为立即可用的显示，按实际可见物品安排实时图标；取消或延后离屏任务，将掉落物预热从图标完成的同步路径中拆开。不要把首次卡顿简单搬到鼠标松开/丢弃动作上。
2. 图标与掉落物使用共享的最小视觉装配数据：目标网格、必要姿态、实际配件和材质。先按武器定义决定依赖，避免为静态预览初始化完整玩法角色、无关动画和特效。
3. 将资源请求与就绪等待拆成可让出帧的异步阶段；资产加载完成和渲染/编译就绪分别判断。仅把外层函数改名为 Async 或延迟若干帧，不能消除内部同步 `LoadObject`/等待。
4. 在确有回读成本后使用异步 GPU 回读，维持现有图标尺寸、材质和构图。最终图标缓存按武器配方与视觉版本失效；现有 64 项内存缓存已经存在，不重复实现同一层缓存。

这些措施目标是减少长卡顿与无必要的预览初始化；它们对持续帧率的收益尚未测量。

## 仍未确定的部分

- A/B 的帧时 P50 为 53.58 / 54.06 ms。去掉各自最慢两帧后，剩余均值仍为 56.07 / 56.65 ms，所以持续低帧还需要独立归因。
- GPU0 典型时间约 10–11 ms，组件复杂度排行不等于真实耗时。当前证据不支持优先降低贴图、关闭阴影或删减场景模型。
- 日志中的约 4608 MiB 资产编译内存估计超过当时调度预算，说明发生了资源编译压力；这不是显存耗尽或必须升级硬件的证明。
- 源码中的 `ExportCatalogIcon` 另有显式 `FinishAllCompilation`，属于目录导出路径，不是运行时 Tick 路径，本次未将其误归为游戏内阻塞源。运行时回读内部的等待则已从引擎源码确认。
- 现有较早 CSV 可提供历史线索，但不是这两份 13:15 快照的同次采集，不能拿它们替代当前对照数据。

后续仍可离线继续做依赖与调用链分析，或读取以后保存的 CSV/Insights 文件。只有需要量化约 54 ms 的内部占比及确认改动收益时，才需要新的运行采集；本次没有请求或执行该采集。
