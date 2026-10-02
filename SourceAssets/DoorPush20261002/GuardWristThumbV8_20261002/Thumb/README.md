# 撞门护拳拇指作者补丁

本目录只制作 `thumb_01_l`、`thumb_02_l`、`thumb_03_l` 的局部旋转。输入是父任务保存的 `../BeforeAuthored/full-pose.json`；没有修改共用 StaffQuickCombat 拳形、腕臂、骨长、位移、缩放、蒙皮、材质或其他手指。

旧源把拇指根的 dorsal 方向强制拉到指甲展示方向。分离原生骨长轴的 swing/twist 后，CMC 根部带有约 -127.00° 的轴向转动。新源使用原生 CMC swing＋有限 opposition，MP/IP 沿实际原生关节 across 轴屈曲，整条拇指继承根部对握；没有把每节指骨分别拧到同一个指甲法向，也没有使用局部 Euler 轴调姿。

新 CMC 掌向累计折角为 35°（旧语义角 47.5°），径向打开 18°。在 V7 实际蒙皮指腹与已冻结的食指／中指外侧之间构造自然托靠姿态：CMC 轴向对握约 -69.01°、MP 额外屈曲约 10.11°、IP 额外屈曲 30°。这些是本骨架制作参数，不是通用人体角限。

`thumb-rotations.json` 提供三根骨骼的 `local_rotation_xyzw`，以及可编辑矩阵、原生语义参数、输入文件 hash 和制作记录。`author_thumb.py` 可以后台重新制作，并提供 `apply_to_pose_data(data, patch=None)` 合入函数。

父任务合入腕臂修改以后调用 `apply_to_pose_data`，它只替换 Prepare、三条 GuardSway 和 GuardHoldEnd 的拇指旋转，并从父任务最终 `hand_l` component 逐级更新三根拇指 component 矩阵。首尾示例不动，现有实时入场和回握继续走原有插值。随后由父任务生成完整头文件与 Blend。

根任务已将三骨补丁合入完整护拳姿态、C++ 动作表和正式 Blend，并完成正常 Game／Editor 构建；完整接入状态见上级 `integration-completion.json`。未运行游戏、未渲染、未进行测试或验收。数值记录用于说明制作依据，不代替用户测试后的手型判断。
