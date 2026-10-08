# 伏窥者死亡前段与软体交接 V13

2026-10-07。用户反馈伏窥者死亡后原地几乎不动、缺少可见动作。

## 原因与处理

`AWolfMonster::EnterState` 原先在进入 Dying 时立即调用 `TryStartSoftDeath`，隐藏活体并停用角色 Tick。M08 已制作、接入的 DeathV10 因而被跳过，原有 `DeathAnimationFraction=.55` 也没有机会控制动作交接。低伏、宽支撑的身体直接进入保持初始体积和边长的软体，重力下的可见变化有限。此结论来自现有入口和制作源读取，未进行游戏复现。

M08 现在按致命伤发生时的实际支撑状态选择：

- 地面支撑且没有腾空／飞扑：先播放当前动作集的 Death 前段。现有 DeathV10 时长 1.4 秒、交接比例 55%，因此前段约 0.77 秒，表现为四肢依次失去支撑、身体侧倒。
- 爬墙、倒挂、跳跃或空中：仍立即交给世界重力软体，不在墙面等待地面侧倒动作。
- 前段结束时，先提交动画姿态，再由原 `CorpseRagdoll::Start` 捕获这一帧建立软体；继续使用当前减面修复后的尸体及代理。
- 死亡入口立即清除表面路线、抓附和跳跃状态，终止空气炮；播放死亡声音并停掉待机／爬行循环音，避免立即停用 Tick 时漏掉音频清理。

共享狼类入口新增默认关闭的前段策略，仅 M08 覆盖启用条件。决策时长在解除支撑前记录并复制，客户端按同一时长播放；收到 Ragdoll 状态时先采样交接姿态，再启动本地软体。击杀奖励、伤害、AI、活体动作和其他物种的默认立即软体路线保持原逻辑。

## 修改与交付

Editor 和 Game 常规构建均已完成，最终退出码均为 0；基础 `UnrealEditor-FPSGAME.dll` 和 `FPSGAME.exe` 已落盘。没有使用热编译，也未在构建后打开编辑器。

- `Source/FPSGAME/Monsters/WolfMonster.h/.cpp`：前段选择接口、复制时长、死亡入口门控、客户端动作采样与物理交接通知。
- `Source/FPSGAME/Monsters/LurkerM08Monster.h/.cpp`：地面支撑选择、死亡时表面／空气炮／音效清理。
- `Tools/LurkerM08/Build-DeathLeadV13.ps1`：沿 UE 批次互斥进行 Editor/Game 常规构建，不自动开关编辑器。
- `SourceAssets/Monsters/LurkerM08/DeathLeadV13_20261007/Before/`：本次修改前的四个源文件，包含当时已有的并行改动。
- 同目录 `Records/`：各目标构建日志和回执；最终构建状态见 `delivery.json`。

复用 `/Game/Monsters/LurkerM08/DeathV10/Animations/A_M08_Death_DeathV10` 所在的现有动作集，以及 AnatomyRepairV5 活体／尸体绑定。本次没有重做、重导模型或动画资产，没有改变共享软体约束参数，也没有放宽尸体模拟预算。

未启动编辑器或游戏，未追加测试、截图、渲染或视觉验收。动作与实际落地效果由用户体验。
