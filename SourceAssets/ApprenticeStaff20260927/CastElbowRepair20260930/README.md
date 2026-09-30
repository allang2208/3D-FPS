# 法杖施法右肘修复源

当前输入是 `../ArmSupportV13/full-pose.json`，保留 V13 握点、指部、待机/跑姿，修正四种握柄的 Raised/Windup/Release/Follow。V28 普攻仍独立使用原表。

制作顺序：`author_pose.py` 生成 `full-pose.json` 与运行时 `StaffAuthoredCastElbow20260930.h`；`export_takes.py` 输出两段施法及各自收势的采样；后台 Blender 执行 `save_editable.py`，保存 `Staff_CastElbow20260930.blend`。编译 `StaffGripPose.cpp` 后生效，无需另行导入动画 uasset。

`diagnose.py` 是本次用户要求的专项排查入口，不作为后续每次制作的自动前置步骤。`diagnosis.json` 覆盖四握柄、1176 个默认静止姿态样本、裸臂作者表面及已保存锁子甲三档 LOD；并非游戏/穿模验收。完整结论、构建状态和限制见 `Docs/Weapons/staff-cast-elbow-20260930.md`。

`Before/StaffGripPose.cpp` 保留切换姿态表前源码；旧 V13/V17 文件仍是制作依赖，不能按日期删除或覆盖。
