# 地牢刷怪后持续卡顿排查与修订（2026-10-12）

用户明确反馈：怪物出现后开始持续卡顿，之前进入速度相近且无此现象。本次读取已有运行日志、加载改动和刷怪/感知实现，没有启动游戏或新增性能采样。

## 已有证据与判断边界

- 原运行日志为 `Saved/Logs/FPSGAME-backup-2026.10.12-03.44.47.log`，其中时间戳是 UTC；以下叙述为本地时间 UTC+8。最小摘录保存在 `Saved/TaskBackups/DungeonPostEntryStutter20261012/runtime-evidence.txt`。
- 11:43:00 两厅首波配置为 15 + 12 只；迎宾厅 11:44:06 触发第二波 14 只。首波配置合计 27，不等于每帧存活数或可见数。
- 快速进入模式下，该次地牢生成报告 `elapsed_ms=49025.0453`。这是生成阶段墙钟时间，不能和成功进入总用时、游戏线程占用相混淆，不能证明前轮已经提速。
- 进入地牢后，WeaponIcon 持续准备、渲染不同武器配方，日志延续到 11:44:44。前轮改动只在加载遮罩持有输入时阻止新任务，解除遮罩后又释放整条队列。因此确实把一部分图标工作推迟到了游戏期间，属于这轮需要纠正的调度问题；没有帧采样，不能宣称它解释全部低帧。
- 地牢生成器成功结束会释放 BuildState 并关闭 Tick；未发现新增装配轮询在成功进入后继续逐帧运行。批次实例边界更新也没有取代原本按房间模块范围判断可见性的逻辑。
- MonsterAIController 原本在构造与 OnPossess 都开启全部视线阵营。UE 自动把 Pawn 注册为视线源，在 RegisterNewQuery 建立观察者/目标查询；项目在 Perceived/UpdateKnowledge 才过滤到玩家。怪物之间因此有无效查询；27 个怪物最多对应 702 个有向同伴组合，**这不是每帧射线数或实测耗时**。
- 该次运行未留下可用的同场景 CPU/GPU 帧捕获。新波次数量带来的骨骼动画、蒙皮、阴影等开销仍不能量化。本次不以降画质或减少怪物掩盖问题，也不宣称完成帧率验收。

## 已落盘修订

1. 图标调度：普通实时图标仅在背包/图鉴等现有库存面板或强化面板打开时启动新任务，加载遮罩仍优先。关闭面板时队列保留，继续使用缓存/目录图；正在执行的单个任务继续收尾，避免悬挂 GPU 回读和重试计时。离线目录导出保留原流程。增加控制器只读 `IsItemIconPanelOpen()`，不把 F6 或 ALT 光标状态误作图标需求。
2. 怪物感知：控制器将带 MonsterCombatComponent 的非玩家 Pawn 识别为同伴，视线排除 Friendly，在原生查询分配前过滤。组件在被 AI 接管前已存在，不依赖目标控制器创建顺序。其他目标沿用父类关系；不修改全局 TeamId。听觉仍检测全部原有阵营，视距、波次数量、追击和群体预警规则保留。

修改文件为 `Monsters/MonsterAIController.h/.cpp`、`FPSGAMEPlayerController.h/.cpp`、`UI/ColdSteelWeaponIcons.cpp`，均位于 `Source/FPSGAME`。修改前副本保存在 `Saved/TaskBackups/DungeonPostEntryStutter20261012/`。未改地图或美术资产。

## 交付状态

用户保存并关闭 UE 后，已完成 `FPSGAMEEditor Win64 Development` 常规后台构建，结果 `Succeeded`、退出码 0，两处修订已编入 `Binaries/Win64/UnrealEditor-FPSGAME.dll`。首次编译发现新增局部变量 `Pawn` 隐藏基类成员，已改名为 `TargetPawn` 后成功重建，未改变过滤行为。

成功构建日志：`Saved/BuildEditor/dungeon-post-entry-stutter-20261012-120734.log`；回执：`Saved/BuildEditor/dungeon-post-entry-stutter-20261012.json`。没有重新打开 UE、运行游戏或进行测试；构建成功不代表帧率改善已经实测，实际变化由用户测试。
