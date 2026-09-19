# 左斜握把拇指闭合微调

继承 FirmGrip 已验证握姿，仅修改左拇指三个关节的旋转。掌面位置、四指、手腕和握把保持前版；指腹向内扣合，松手时逐渐恢复原展开曲线。

`solve_thumb.py` 为局部拟合，`refine_thumb.py` 缩回少量旋转以排除边缘穿模。最终参数见 `fist_solution.json`，以真实网格完整检查及游戏画面验收，不将径向距离近似视为实际接触保证。

九组动作使用 `/Game/Weapons/M4CantedThumbClose`；因旧资产文件被占用，已更新 C++ 动画引用并新增 cook 目录。最终结果见 `acceptance.json`、`geometry_contact_full.json` 和运行日志；`M4_CantedForegrip_Integrated_Editable.blend` 为可编辑源，游戏视频是截图序列的无声预览。
