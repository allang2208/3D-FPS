# 垂直握把类共用动作

当前成员为 M4 的 vertical_foregrip 与 prism_handstop。两者调用同一个 build_family.py，使用 common_hand_pose.json 中完全相同的手指闭合姿态，以及相同前臂支撑方向；肩肘参照已验证的 LeftSupport（其方向来自棱镜阻手器）。contact_overrides.json 当前均为空。

共用九组源动作、120/240/480 Hz 烘焙频率与既有取弹/插入/拍击时序。Prism 接触位置在共用安装框架中调整 (0,-4,-8) mm，撤手方向增加向下分量，避免短阻手器的顶部/弯曲边缘；两者不改变模型、材质、骨长或手指局部平移。

生成：Blender 后台运行 vertical/build_animation.py 或 prism/build_animation.py。每个配置目录有独立真实网格、源约束、导入读回和游戏验收入口。validate_shared_pose.py 对比两款实际烘焙源的手型与前臂方向。最新结果为 family_acceptance.json，历史过程日志保留，不用未完成报告宣布通过。

运行资源：/Game/Weapons/M4VerticalGripClass/Vertical 与 /Prism。M4HandstopVisual.cpp 和 M4VerticalForegrip.cpp 通过 VerticalGripAnimationFamily.h 统一选择资源。AKM 专用分支保留，其他枪型新增该类别时需要按骨架/安装基准适配。

个人/工程技能均有 ue5-fps-arms-animation/references/vertical-grip-family.md；新成员默认复用本母版，只定义接触配置。不要复制一套动画实现再独立维护。左斜和穿孔三角握把继续采用专用类别。
