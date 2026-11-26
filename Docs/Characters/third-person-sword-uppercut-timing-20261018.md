# 第三人称双手剑上挑：蓄势、出手与前进步伐

用户反馈当前第三人称上挑像慢动作，要求匹配蓄力、出手及腿部前进。本次调整世界身体的播放映射，复用当前 `player_body.json` 指向的 `KwangSwordRecovery20261010/Animations/J_Kwang_Uppercut` 和 `Unarmed.Jog.Fwd`，不重制或覆盖动画包。

## 时钟与动作分段

此前 `SampleLocalState` 先用技能播放秒数填写动作时长和进度速率，随后又将进度覆盖为作者时间比例；通用动画映射则把整个片头至 Contact 都铺进一秒蓄势。现统一使用执行器提供的技能播放进度，第三人称另设准备结束、正前方接触、出手结束三个阶段。

| 技能播放时间 | 第三人称表现 |
| --- | --- |
| 0–1.000 秒 | 从待机缓入压低蓄势，仅播放当前 Kwang 作者源约 0.16 秒的入场段 |
| 1.000–1.280 秒 | 前四分之一先蹬地，随后加速挑起；在前冲结束时到达源动作 Contact |
| 1.280–1.355 秒 | 从 Contact 继续到 Release，保留上挑的完整出手与随动 |
| 1.355–约 2.280 秒 | 播放原动作的收势回位 |

源分段依据：`ThirdPersonSwordKwang20261006/adapt_kwang.py` 的 `attack('Uppercut', 'PrimaryAttack_A_Slow', .0666667, 1.2, .20, .28)`，入场 0.16 秒；当前恢复资产由 `ThirdPersonMeleeRegression20261010/restore_accepted_arms.py` 保留该整臂链。准备姿态以 Contact 标记比例定位，保留原作者采样取整。

伤害窗口、150 cm 前冲、体力、冷却及第一人称动画均沿用现有执行器。这里的 Contact 是第三人称剑刃朝前的姿态时点，不是将玩法命中窗口延后。蟠螭免准备直接从执行器的释放进度进入；普通连段升龙及双手锤沿用原分支。

## 腿部衔接

- 移动中的蓄势与后段收势保留普通移动步态，前冲附近才接管腿链。
- 释放前 0.10 秒混入起步姿态，腿部进度与上挑读取同一份动作进度；不额外用墙上时钟推进。
- 根据现有跑步片段的步幅和脚触地标记，把前冲对应步数对齐到最近的半周期；沿实际执行器的平滑前冲曲线推进，结束时到达左脚或右脚接触姿态。
- 落脚后再用 0.14 秒混回原上挑腿姿，避免减速阶段提前失去跑步腿链。遇阻或腾空时停止推进该步相并淡出。
- 继续使用原胸腔保持、双手握柄及地面适配层，不新增根运动或角色位移。

## 落盘与构建

修改范围为 `FPSBodySwordMotion.h`、`FPSPlayerBodyActions.cpp`、`FPSPlayerBodyAnimInstance.cpp`。修改前工作区副本位于 `Saved/TaskBackups/ThirdPersonSwordUppercut20261018-195751/`，保留已有并行修改。

源码已落盘，并已被共享的 `FPSGAME Win64 Development` 常规构建编译、链接：`FPSPlayerBodyActions.cpp` 为第 48/129 项，`FPSPlayerBodyAnimInstance.cpp` 为第 66/129 项，最终 `Result: Succeeded`，耗时 344.92 秒。构建日志为 `SourceAssets/BowLeftCastHandoff20261018/Build-20261018-200152-Game/build.log`；本轮复用这次实际构建，不重复启动 Game 构建。

Editor 接入尚未完成。前两次互斥桥等待超时，均未发送请求；等待共享 Game 构建结束后，Editor 常规构建的启动保护发现新的 `UnrealEditor.exe` 进程，未启动构建。该进程启动参数含 `-NoLiveCoding`，也不能沿当前进程热更新。未关闭或重启它，当前编辑器不能视为已经应用本次修改；后续仍需关闭占用后完成常规 `FPSGAMEEditor Win64 Development` 构建。

本任务未运行游戏、PIE、截图、渲染或自动测试，动作观感由用户实机体验。
