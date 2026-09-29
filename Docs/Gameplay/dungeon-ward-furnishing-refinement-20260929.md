# 病区把手、病床尺寸与血迹调整

范围：独立病区 `L_AbandonedIsolationWard_Subject`，不加入随机房池。

- 门把手原本位于玻璃面内，玻璃被打碎后金属部分保留，造成悬空。两侧把手和安装脚由局部 Y=-0.6325 m 移到 Y=-0.7625 m，固定在 7 cm 宽的金属竖框上；安装脚埋入框面 1 mm，碰撞随把手移动。门扇独立开合、玻璃破碎及弹孔清理保持原实现。
- 病床尺寸烘焙为原来的 150%，仅修改病区派生网格，导入母资产不变。61 个凸碰撞体同步缩放；站立、左右侧倒、倒置的模型及碰撞联合边界重新制作，保留随机方向、通道预留和拥挤时少放的策略。床间净间距仍为 110 cm，墙边净距仍为 65 cm。
- 血迹继续使用 Quixel Blood Stain sgfjdepc 扫描材质。五个病房分别使用独立的一次性随机生成器，每间目标 20 处地面、6 处墙面；公共区域目标 36 处地面、12 处墙面。整层目标合计 178 处（原为 60 处），位置与旋转每次进入随机；采样不成功时实际数量可低于目标。
- 扫描贴花宽度由 25–60 cm 调为 35–85 cm，保留正方形比例及浅投射深度。病房新增侧墙和后墙接收区域，并避开后门洞与正面玻璃。沿用结构接收标签、射线命中和间距限制。

作者入口同步在 `Scripts/author_glass_doors.py`、`author_breakable_glass.py`、`BedScatter/Scripts/author_bed_collision.py`、`Scripts/room_blood_design.py`、`configure_room_blood.py`。`prepare_design.py`、整房安装、扫描血迹更新脚本均复用本轮配置。

本轮后台安装入口：`SourceAssets/DungeonIsolationWard20260929/Refinement20260929/install.py`。落盘结果以该目录 `Receipts/install.json` 为准。没有修改原生 C++，无需重新编译 DLL。未运行游戏、PIE、截图、渲染或验收，交由用户测试。
