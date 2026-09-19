# M4 手臂 IK 编辑

打开 Content → Weapons → M4ArmsIKEditor → LS_M4_Vertical_Idle_IK_Edit。

- hand_l_ik_ctrl / hand_r_ik_ctrl：W 移动手掌，上臂和前臂自动跟随；E 旋转手掌。
- elbow_l_pole_ctrl / elbow_r_pole_ctrl：W 调整肘部朝向。
- index、middle、ring、pinky、thumb 开头的 *_fk_ctrl：旋转手指关节。
- 在动画大纲搜索控制器名，避免选到 hand_l_fk_ctrl 或 ik_hand_l_fk_ctrl。

IK 是原动画上的偏移。要让同一个修正覆盖整个待机，在第 0 帧和第 360 帧设置相同 IK 偏移；需要变化时再增加中间关键帧。循环首尾应一致。不要删除用于保留原动作的密集 FK 关键帧。

CR_M4_ArmsIK 是独立控制绑定。LS_Vertical_UserFK_Backup 保存创建时用户 FK 编辑状态。没有替换游戏使用的 AnimSequence；编辑完成后需要另行烘焙为新动画并验收。

垂直握把作为序列内生成对象，使用 WPN_root 附着轨道及 M4VerticalForegrip.cpp 的参考骨架安装公式。预览整体移到 X=2000、Z=150，避开原场景对象；整体位移不改变握把相对安装位置。

验证：361 帧源姿态对比最大位置差 0.0000312 cm、旋转差 0.01955 度。双手可达目标、肘部方向、手指局部旋转保留、不可达目标不拉长骨骼均通过脚本检查。详细结果在 validation_summary.json。

这些构建脚本用于制作初始资产，后续手工编辑后不要重跑 create_sequence.py，它会重建本候选序列。
