# 追踪栏扩展机制排查 · 2026-10-13

用户范围：排查后续新增任务/目标能否正确进入左侧栏，修正必要机制并制定标准工作流。正式入口：[任务与目标工作流](../../TASK-WORKFLOW.md)。

## 原实现问题与处理

| 代码发现 | 影响 | 本次处理 |
| --- | --- | --- |
| 单个 FDungeonTrackingView 只含一段 Objective/Progress | 第二目标覆盖第一目标，无法同时显示 | 共享 FTrackedTaskView + Objectives 数组，支持多个任务 |
| UI 用区域中文名与目标文案组成身份 | 改名重播，同名目标混淆 | Task.Id、InstanceId、Objective.Id 稳定身份 |
| HUD 直接访问 DungeonRunSubsystem，主标题固定 | 非地牢新任务需要改 HUD | ITaskTrackingSource + World 注册表，HUD 只消费共享快照 |
| 一个完成标志和一条绘制线 | 多目标会共用完成反馈 | 每个目标一份状态和划线进度，增删/重排复用对应行 |
| 固定 144px 高度 | 长说明或追加目标会溢出 | 内容自适应高度、视口高度上限与纵向滚动 |
| 只有运行时大厅槽位状态 | 不能证明跨档/客机任务接入 | 明确记录现有存档与网络边界，不自动扩写任务存档系统 |

现有精英和开门条件已经共用 `IsWelcomeEliteDefeated()`，本次保留。目标进度读取不发奖励、不改变闸门，UI 动画不是玩法完成时钟。来源查询中的上个房间记录按 Viewer 隔离，失效 Pawn 清理，重新生成清空。

## 本次代码与文档

- `Source/FPSGAME/Tasks/TaskTrackingSubsystem.*`：显示快照、来源注册、稳定排序和 ID 合同。
- `Source/FPSGAME/UI/ColdSteelDungeonTracker.*`：任务组/目标行的稳定 ID 复用、独立反馈、透明布局与滚动。
- `Source/FPSGAME/Dungeons/DungeonRunSubsystem.*`：作为第一个实际来源注册，原首阶段玩法保持。
- `Source/FPSGAME/Tasks/TaskTrackingContractCommandlet.*`：仅按本次排查授权执行的数据合同检查。
- 根目录 `TASK-WORKFLOW.md`，由 AGENTS.md、UI-WORKFLOW.md、UI 索引链接，后续任务开发先读。

## 排查边界

代码确认 Alt 已有只显示鼠标的 HUD 交互入口，滚动复用该入口，没有新增按键。屏幕排版、真实滚轮操作与闸门动画仍需游戏体验；本次不自动启动游戏或截图。

初始排查时生成器 BeginPlay 在 NM_Client 返回，RunSubsystem 每次绑定生成新 RunId 并清空本轮进度。已有奖励槽位去重不等于任务断点恢复；现有显示来源也不等于网络复制。制作期间工作区追加了世界/地牢网络快照接口，但构建时其实现尚不完整。将来明确要求持久/联机任务时，按实际最新代码和工作流同时实现对应业务链。

## 构建与检查结果

- 已完成本次源码机制排查和范围内 `git diff --check`，没有空白错误。现有 UI/任务栏类、注册来源和地牢来源已写入源码，未更改任务奖励、保存格式或大厅战斗规则。
- 已编写数据合同 commandlet，包含 15 项：重复注册、多任务/多目标、同名、顺序/改名、新实例、移除、独立来源注销和完成/失败划线转换。由于最终基础 DLL 未能链接，本次**未执行这些检查**，不能声称 15 项通过。
- 必要 Editor 构建三次遇到工作区其他原生改动的阻塞。`build-20261013-104914.log` 为复制参数名错误；准备最小修正时对应文件已更新，补丁未应用，本任务没有覆盖它们。`build-20261013-105147.log` 为新增建造联机代码编译错误，之后相关文件有新修改。
- 最后日志 `Saved/BuildEditor/build-20261013-105321.log` 已到链接阶段，但缺少 `AColdSteelPlayerState::ExecuteWorldAction`、`UDungeonRunSubsystem::FillNetworkState`、`UDungeonRunSubsystem::ApplyNetworkState`，最终 `Failed (OtherCompilationError)`。这些接口属于同时在改动的业务文件，本轮保留现场，不填空实现绕过链接。
- 本轮没有成功生成新的基础 Editor DLL，没有运行数据 commandlet、游戏、截图或视觉验收。代码和工作流已落盘，整体构建和合同检查留待上述接口实际实现完成后继续。
