# 原腕臂快照与换轴依赖（V3 方案已退役）

用户否定了 V3 下沉肘位后的手部观感。V3 解算器、作者／接入／诊断脚本、输出和覆盖前备份已移入 `trash/dual-melee-overhead-retired-20260920/SourceAssets/RuneSwordElbowRepair20260920/`。

此目录保留的文件仍是当前制作依赖，不属于废案：

- `Standard_active.json`／`LongGrip_active.json`：V3 修改之前的原腕臂姿态快照，仅在本机保留。
- `pose_conversion.py`：从旧作者脚本原样提取的五个纯换轴／邻域函数；V4 与 V5 通过 AST 读取，没有执行 V3 的姿态制作。
- `import_receipt.json`：V4 `capture_target_files.ps1` 读取的目标清单，回执中的旧备份路径按归档清单恢复。

当前其他动作使用 [腕部 V4](../RuneSwordWristLocked20260920/README.md)，两条冲刺下砍使用 [伸展 V5](../RuneSwordDowncutReach20260920/README.md)。固定手骨世界变换不等于固定腕部观感，前臂接入方向与腕侧辅助骨也必须区分。

恢复边界见 [发布说明](../../Docs/Weapons/dual-melee-overhead-publication-20260920.md)。不要把归档 V3 再次安装到当前路径。
