# 空手左右交替出拳制作源

以当前空手 `UnarmedLocomotion20261001` 的完整双闭拳 Exhale 待机作动作起止。第一拳为右拳，其后由运行逻辑左右交替。法杖 `StaffQuickCombat20261001` 左拳提供中间六个肩、腕、肘姿态和相同节奏：接触 `0.1716666667 s`，全长 `0.5516666667 s`，Ready 到接触的前冲仍为原始动作 1.5 倍速度，回收各段保持原时长。

左、右 take 每个包含 8 个完整双臂局部姿态，共 54 根原生骨。攻击臂沿原生长度和肘铰链重新求解；右拳由相机 Y 镜像加左右原生掌语义框架迁移方向，不能直接镜像四元数或使用负缩放。另一臂保持当前空手待机闭拳。每个关键帧保留已制作的 V7 四指闭拳与外侧对握拇指，不继承法杖收拳后张开的手型。upper/lower twist helpers 保持原生 rest-local，未改网格、蒙皮、绑定或骨长。

## 运行接口

`Source/FPSGAME/Weapons/Unarmed/UnarmedAuthoredPunch20261002.h`，命名空间 `UnarmedAuthoredPunch20261002`：

- `Revision=2026100201`、`KeyCount=8`、`BoneCount=54`。
- `Times[8]`：Idle、Collect、Ready、Contact、ShortRebound、Retract、Relax、IdleReturn。
- `FBone { FQuat Rotation; FVector Position; }` 和原生顺序 `Names[54]`。
- `Poses[2][8][54]`：攻击侧 0 为左拳，1 为右拳。
- `FJoint { double Flex; double Roll; }`；`Joints[2][8][2]` 最末一维为左臂 0、右臂 1。
- `FJointDefinition { FQuat LowerRestRotation; FVector ElbowHinge; FVector ForearmAxis; }`；`JointDefinitions[2]` 与空手步态表一致。

源位置为归一化相机厘米，运行按父 reference scale 处理。普通骨使用最短路四元数归一化混合和局部位置混合，各区间权重使用 `t³(6t²-15t+10)`。下臂先按同一权重混合 Flex/Roll 标量，再组成 `Q(ElbowHinge,Flex) * LowerRestRotation * Q(ForearmAxis,Roll)`；轴向角已连续展开，不直接混合任意下臂四元数。进退回到当前步态的权重由运行组件承担。

## 源文件

`author_punch.py` 只读既有制作源，通过有 main guard 的空手步态模块复用 `native_arm`，复用闭拳作者的 `make_fists`，生成 `full-pose.json`、`authored-parameters.json` 和 C++ 表。完整 JSON 保留各关键帧的 component/local 矩阵及双臂肘/下臂关节标量，可继续编辑制作。

`save_editable.py` 从合法现有 V7/M4 Blender 源后台保存 `Unarmed_V7_AlternatingPunch_20261002.blend`，两个 take 为 `A_Unarmed_V7_RightPunch_20261002` 和 `A_Unarmed_V7_LeftPunch_20261002`。以 120 Hz 密集曲线和精确作者时刻保存五次平滑，曲线使用 LINEAR，不追加 Bezier 过冲。实际落盘记录位于 `editable-source.json`。

运行使用原生 C++ 姿态表，无需导入新的 UE AnimSequence。源制作和源保存不等于游戏验收；未进行渲染、游戏测试或视觉验收。
