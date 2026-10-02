# 空手双拳与双臂步态制作源

新待机腕点相机厘米为左 `(29,-15,-18)`、右 `(30,16,-19)`，比旧待机仅将前向 X 后收 `5 cm`。保留已制作闭拳与拇指 profile、镜头后肩点、4.2 秒低幅呼吸。待机重新按原生骨长求肘，而非只移动手掌。

步行与奔跑使用法杖 `LeftGaitV16` 已有左肩、腕和肘的完整轨迹节奏；Walk 幅度较小，Run 独立较大轨迹。右侧用相机 Y 镜像与原生左右掌语义框架迁移方向，按右侧原生骨长和肘铰链重新求解。右臂已偏移半周期。左右拳形保留，新版步态不独立随机张合手指。upper/lower twist 保留完整原生 rest-local。

## 运行接口

头：`Source/FPSGAME/Weapons/Unarmed/UnarmedAuthoredLocomotion20261001.h`；命名空间 `UnarmedAuthoredLocomotion20261001`。

- `Revision=2026100101`，`BoneCount=54`，`Samples=32`，`IdleKeyCount=2`，`PeriodSeconds=4.2`。
- `FBone{ FQuat Rotation; FVector Position; }`，`Names[54]` 原生顺序。
- `Idle[2][54]`：Exhale=0，Inhale=1。
- `Cycles[2][32][54]`：Walk=0、Run=1；每帧同时含左右手，右臂已反相。
- `JointDefinitions[2]`：Left=0、Right=1，`LowerRestRotation`、`ElbowHinge`（上臂局部）、`ForearmAxis`（下臂局部）。
- `IdleJoints[2][2]`、`CycleJoints[2][32][2]` 的 `FJoint{double Flex; double Roll;}` 与相应姿态相同索引。

呼吸权重 `h=0.5-0.5*cos(TAU*t/4.2)`。步态只采样同一个 `UFPSFootstepAudioComponent::GetStridePhaseRadians` 距离时钟：`x=positive_mod(phase/TAU,1)*32`，`a=floor(x)`，`b=(a+1)%32`，`alpha=frac(x)`。不要再给右手加 PI。

姿态总权重为 `Idle*(1-Move) + Walk*Move*(1-Run) + Run*Move*Run`；Idle 内按呼吸权重拆分，Walk/Run 内按相邻样本 alpha 拆分。普通骨用同组最短路四元数归一化加权混合与局部位置线性混合。父 ref scale 的处理沿用已有空手组件（头的位置为归一化厘米）。

下臂使用同组权重先混合 Flex/Roll，再组装 `FQuat(ElbowHinge, Flex) * LowerRestRotation * FQuat(ForearmAxis, Roll)`，随后一次完整 FK；不退回任意下臂四元数直接混合。轴向标量制作时已展开到连续分支，避免 +/-PI 表达边界造成翻臂。

## 可编辑源

`author_locomotion.py` 生成完整姿态 JSON、作者参数和运行头；`save_editable.py` 后台保存当前 V7 原生 rig。

保存源为 `Unarmed_V7_Locomotion_20261001.blend`，三个 120 Hz take：`A_Unarmed_V7_Idle_20261001`（4.2 秒、505 帧）、`A_Unarmed_V7_Walk_20261001`（参考播放 1 秒、121 帧）、`A_Unarmed_V7_Run_20261001`（参考播放 0.7 秒、85 帧）。游戏中循环速度由距离相位确定，不使用参考秒数独立推进。

运行使用 C++ 姿态表，不需要 UE AnimSequence 导入。实际源保存状态记在 `editable-source.json`；该记录不代替运行接入或构建记录。未进行渲染、游戏测试或视觉验收。
