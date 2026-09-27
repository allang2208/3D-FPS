# 大小手基础动作接地修复

用户要求修复完成度检查中发现的基础动画接地问题。修改限于原基础作者入口及 Idle、Slam、GrandSlam、Hit、Dizzy、Death 六个已绑定片段的根骨位置轨道。

## 修正方式

旧脚本将世界竖直偏移写入 root 的局部 Z；本骨架局部 Z 朝水平方向，局部 Y 朝上。现将实际蒙皮最低点的世界 Z 补偿，依次通过骨架对象和根骨绑定坐标的逆变换，转换为正确的骨骼局部位移。

`repair_basic_grounding.py` 在已有 `Animations/FleshHand_Animated.blend` 的六个动作上重新烘焙根位置：逐帧去掉旧的错误水平补偿，再求该姿态的竖直支撑。原关节旋转、缩放、手指动作与时间不重制；根位置使用 60 Hz 密集线性关键帧。`author_animations.py` 同步修正，后续全量重建也使用正确坐标。

普通拍击和重拍仍为 2 秒，Hit 0.7 秒、Dizzy 2 秒、Death 1.8 秒、Idle 2 秒。伤害接触时刻、冷却、击退、眩晕、朝向、胶囊、网格、权重和材质不在本次修改范围。两个新移动循环、三个冲锋片段及十个击飞／起身片段继续使用原绑定。

六个动画沿用原 UE 资产路径，因此大小手原有引用直接取得修正；小手只执行其中待机、受击、眩晕、死亡，拍击仍只有大手执行。根运动提取继续关闭，根部支撑补偿不叠加游戏世界位移。没有增加运行时扫描、IK、射线或布娃娃。

## 源与接入

- 制作脚本：`SourceAssets/FleshHand20260926/repair_basic_grounding.py`。
- 导入脚本：同目录 `install_basic_grounding.py`；只重导六个现有动画包，不重导模型或重写蓝图参数。
- 可编辑源／FBX：`Animations/FleshHand_Animated.blend` 和六个原同名 FBX，已更新。
- 原作者脚本、Blender 源与六个 FBX 备份：`GroundingRepair/BeforeSource/`。
- 原 UE 六个动画备份：接入时保存到 `GroundingRepair/BeforeAssets/`。
- 制作回执：`GroundingRepair/authoring.json`；接入回执：`GroundingRepair/installation.json`。

制作与 UE 接入均已完成。编辑器在接入前退出，随后通过后台 Python commandlet 导入并保存六个动画包，进程退出码 0；`GroundingRepair/installation.json` 状态为 `six_corrected_animations_saved`，日志为同目录 `import.log`。大小手共用片段沿原路径取得更新，不需要重新绑定蓝图。本次没有原生源码变更或启动 GUI。

本轮没有追加运行测试、截图、渲染或性能采样；逐帧蒙皮最低点求解属于动画制作过程，不代表真实场景斜坡和墙角的视觉验收。
