# 地牢进入阶段资源与组装流水线（2026-10-12）

用户反馈进入地牢等待较久，要求兼顾进入后的性能。本次沿用 `AuthoredDungeonGenerator`、加载遮罩与现有房间调度；只进行后台源码修改和必要构建，不启动编辑器、游戏、测试或性能采样。

## 修改

- 原流程等待本轮所有资源完成后才开始组装。现在每个组装任务记录自己的资源索引，只有这些资源被接管并保存在 `GenerationResources` 后才运行；后续资源请求同时继续推进。
- 保持原有稳定排序：结构碰撞、外观、灯光、交互实体、摆件场景、摆件、家具散布、血迹。门框先于交互门，固定物体先于摆件碰撞选择；不跳过未准备好的前置任务。
- 资源请求按排序后任务的首次使用顺序去重排列，优先请求结构所需资源。共享资源仍登记为每个使用者的依赖；病区运行时 Actor 同时等待该模块的 `runtime_assets` 池。神像等延迟使用资源排在直接依赖之后，但提交布局前仍须全部完成。
- 单机加载遮罩持有输入期间，每帧资源接管与组装共用默认 8ms 预算；其中资源阶段最多使用预算的四分之一，剩余时间交给已准备好的组装任务。资源批次接管可中途暂停，全部对象被强引用保护后才释放句柄。
- 每批仍最多 32 个资源；单机加载遮罩期间最多同时 4 批，其余场景保持 2 批。未进入加载预算条件时，沿用默认 3ms 预算。没有改全局异步加载、显存池、画质或帧率限制。
- 旧布局拆除与新布局显示沿用独立帧预算，使用同一加载状态选择预算。只有全套资源、组装、物理和导航完成后才提交并放行玩家；取消和失败沿用原处理路径。
- 进度按资源和组装的合计进度显示，避免交叠执行时反复跳转阶段百分比。

单个不可分割的网格注册或物理操作仍可能超过预算；8ms 是调度参数，不是保证的总帧时间。进入后生成 Tick 仍关闭，保留既有房间显示、实例化与灯光调度，本批不新增游玩阶段的资源扫描。

## 参数与按需指标

| 控制项 | 默认值 | 用途 |
| --- | --- | --- |
| `fps.Dungeon.Generation.BudgetMs` | 3 | 未使用单机加载遮罩预算时的资源/组装预算，毫秒 |
| `fps.Dungeon.Generation.LoadingBudgetMs` | 8 | 单机加载遮罩期间的资源/组装预算，限制在 0.25–16ms |
| `fps.Dungeon.Generation.LoadingResourceBatches` | 4 | 单机加载遮罩期间并发资源批次数，限制在 1–8 |

已有按需生成报告增加 `loading_budget_ms`、`last_slice_budget_ms`、`loading_resource_batches`、`jobs_while_resources_pending` 和 `resource_dependency_wait_slices`。`peak_slice_ms` 现在覆盖资源接管与组装总时间；其他 scope 仍是包含子阶段的 CPU 时间，不应重复相加。没有新增自动采样或日志刷屏。

## 交付

- 修改路径：`Source/FPSGAME/Dungeons/AuthoredDungeonGenerator.cpp`、`.h`。
- 改动前本机副本：`Saved/TaskBackups/DungeonEntryPipeline20261012/`；未覆盖此前未提交修改。
- 本批无需重导资产、修改地图或重新生成布局库。
- `FPSGAMEEditor Win64 Development` 后台构建成功，普通 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 已落盘；本批执行 15 个构建动作，UBT 报告 `Result: Succeeded`。
- 必要构建回执：`Saved/BuildEditor/dungeon-entry-pipeline-20261012.json`；日志：`Saved/BuildEditor/dungeon-entry-pipeline-20261012-091617.log`。本次地牢文件无编译错误；构建另报告两处既有 API 弃用警告，位于其他模块，未扩展修改。
- 未运行游戏、自动测试或性能对比；实际加载时间、进门流畅度及视觉结果由用户体验，未声明提速比例。
