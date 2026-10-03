# 观察台楼梯净空修正

问题来自保留线路样板中第一房的侧翼侵入第二房观察台楼梯，不是第二房需要无门侧室。采用完整房体外轮廓修正三房间距，以正式 Transit / Threshold 补足走廊，不删除原房体或更改正式求解器。

当前布局由 `DungeonIncineratorLine20261003/Scripts/subject_layout.py` 和 `Config/line.json` 保留；本目录 `Scripts/install_scenes.py` 为旧已保存样板的增量迁移入口，后台 `install_background.ps1 -Phase scenes` 使用现有桥互斥。诊断提取与试错输出已归档 `trash/incinerator-theme-20261003`，生产恢复包及实际保存回执留在本地，不发布提取几何。

测试地图继续保留，后续由用户测试。此迁移不改正式随机地牢的模块局部坐标和占位检测。
