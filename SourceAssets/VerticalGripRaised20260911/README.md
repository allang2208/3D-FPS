# 垂直握把类：抬臂微调

相对 VerticalGripClass20260911 共用姿态，两款配件肘部沿安装基准上方向提高约 22.09 mm，肩部同步移动；手掌目标、手指闭合曲线、撤手路线及原换弹接触段保持。

raise_support.py 由原姿态测量前臂长度，设置新方向并联动肩部。共用生成器逻辑未改变；新的 profile.json 为本次主要变化。侧面对比为 before_top.png / after_top.png（文件名沿用旧预览脚本，实际为侧面）。

validate_contact_preserved.py 逐整数帧比对九组动作中的手腕/手指位置与旋转，结果 contact_preservation.json；check_geometry.py 检查真实变形网格。待机腕轴折角约 17.15 度到 21.31 度，本次目标是适度抬臂，视觉验收需同时查看腕臂过渡，不能单纯以较小角度作为自然度标准。

运行资源使用 /Game/Weapons/M4VerticalGripClassRaised/Vertical 与 /Prism，经 VerticalGripAnimationFamily.h 统一选择。结果见 family_acceptance.json；游戏截图及无声预览和可编辑源位于两成员目录。旧共用版保留用于对比。
