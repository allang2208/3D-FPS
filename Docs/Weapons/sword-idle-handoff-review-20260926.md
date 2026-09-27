# 近战持剑姿态衔接检查与修复 — 2026-09-26

用户在调整待机持剑后明确要求检查各动作的衔接与恢复。本轮读取已保存动画的源姿态、压缩姿态和 C++ 状态切换；使用后台 Python commandlet，未启动编辑器界面或游戏，未做渲染或实机验收。

## 结论

常规回待机的动画端点已对齐；查出的疾跑轨道时间错误已经修复。中途取消、从呼吸／行走相位起手、提前松开蓄力、抬剑过程中受击等运行路径补上了持握约束过渡。

**不能把所有分支标记为自然衔接完成：高地大剑的瞬发格挡反击仍会直接切到重击命中姿态。** 这是已有的特殊攻击入口，不是本轮待机偏移引入的问题；详见下方剩余项。

## 已修复

1. **疾跑抬剑／收剑的源帧率错误。** 上一轮作者脚本使用 `AnimationLibrary.get_num_frames()` 得到压缩采样帧数 240 Hz，但 SprintEnter／SprintExit 的原生数据模型是 120 Hz。控制器按数据模型帧索引读取，只读到写入轨道的中间位置。
   - 普通柄／长柄 SprintEnter：121 个写入键重采样为源模型的 61 个键。
   - 普通柄／长柄 SprintExit：49 个写入键重采样为源模型的 25 个键。
   - 仅改写本轮已制作的骨轨道，保持原片段时长、其他轨道、握距与运行引用。4 个正式资产、对应 JSON 和完整 FBX 已保存；修复前副本在 `BeforeHandoffFix`。
   - 作者脚本也改用 `data_model_interface.get_number_of_frames()`，防止再次混用帧率。
2. **动作取消和恢复。** `SetClip` 对动作返回 Idle／Walk、从 Idle／Walk／Inspect 进入带前摇动作，以及 HeavyCharge 接普通三段攻击，捕获切换前的实际姿态，复用双手相对武器的约束过渡。包括中断旋风斩、检视后立即攻击和非零呼吸／步态相位。
3. **格挡起手中受击。** GuardHit／GuardBreak 用 60 ms 姿态过渡，接住尚未完全举起的手臂；格挡、弹反、扣体力与破防状态仍按原逻辑立即结算。
4. **攻击窗口约束。** 普通过渡最多 100 ms；攻击入口按可用前摇缩短，提前松开蓄力后按实际剩余前摇再次收紧。快速近战使用自己的播放时钟计算。过渡在伤害窗口前结束。HeavyRelease 从第 0 帧进入伤害窗口，清除残留过渡，沿用原命中姿态。

## 检查范围与证据

普通柄与长柄各 19 个当前动画：Idle、Walk、Inspect、Equip、Slash1、Slash2、Thrust、PommelStrike、Overhead、HeavyCharge、HeavyRelease、Guard、GuardHit、GuardBreak、WhirlwindV5，以及 SprintEnter、SprintLoop、SprintExit、SprintOverhead。

- 采样正常结束、格挡倒放放下、蓄力取消、满蓄力释放、格挡反馈／破防、疾跑进入／退出和循环，另列出早期格挡受击与瞬发反击，共 64 条跨姿态比较。
- 所有采样的回 Idle 端点，武器／双手最大位置差约 **0.00123 cm**；这是数值采样结果，不是视觉验收结论。
- SprintEnter 接 SprintLoop 保留原先步态差：普通柄约 **1.0443 cm**、长柄约 **1.0570 cm**，方向差约 **1.5395°**；运行时沿用 100 ms 持握过渡，并按实际步态相位采样。
- 两套共 34 份本轮编辑键的帧数与原生模型一致。
- 每条片段取起点、0.20 s、末尾前 0.28 s、终点，比较源与压缩姿态；所采样位置最大差小于 **0.0004 cm**。
- C++ 路径还读取了排队连击、装备结束、提前松开／取消蓄力、动作取消、旋风斩结束／打断、快速近战恢复和冲刺下劈入口。运行路径结论来自代码检查，未宣称游戏内已跑过这些操作。

数据与回执：

- `SourceAssets/SwordIdleClose20260926/handoff_audit_before.json`
- `SourceAssets/SwordIdleClose20260926/handoff_audit_after.json`
- `SourceAssets/SwordIdleClose20260926/source_grid_repair_receipt.json`
- `SourceAssets/SwordIdleClose20260926/repair_source_frame_counts.py`
- `SourceAssets/SwordIdleClose20260926/BeforeHandoffFix/`

## 剩余项：高地大剑瞬发反击

`RuneSwordClovenGuard.cpp::TryClovenCounter()` 直接调用 `StartSwing("HeavyRelease", true)`；该动画从 0 秒开始进行伤害判定。从完整格挡姿态切入时，WPN_root 相差约 **31.376 cm / 99.35°**，双手方向也相差约 99–100°，因此仍是明显的硬切。

本轮保留其现有即时命中行为。直接增加普通混合会使伤害窗口内的刀刃轨迹偏离已制作的重击，不能把这种处理称为修好了。要自然衔接，需要为反击单独制作入口，并明确它如何与即时伤害判定配合；这条分支仍未解决。

## 构建与交付状态

本轮原生改动限定在 `RuneSwordComponent.cpp`、`RuneSwordMeshComponent.cpp/.h`。复用组件内部姿态缓存，未新增蓝图接口或改变网络权限；当前组件仍走既有单机路径。

完整 FPSGAMEEditor Development 后台构建成功，最终日志：`Saved/BuildEditor/build-20260926-174427.log`。正式 `.uasset`、可编辑轨道、FBX 与原生 DLL 已落盘。没有启动／重启 UE 或游戏；自然程度、实际帧率下的混合观感仍由用户试玩。
