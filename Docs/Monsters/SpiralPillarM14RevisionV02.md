# 螺柱 M-14 — V02 移速与死亡修正

> 此为该阶段的制作记录。当前版本、归档位置与恢复依赖见 [整理发布](SpiralPillarM14Publication20261005.md)；不将中间方案视为当前安装入口。

2026-10-04。用户要求改名、移动速度翻倍并修正死亡扭曲、错误拉伸和三角尖刺。

## 已保存的改动

- F6 怪物目录及血条显示名统一为“螺柱 M-14”。稳定 ID、蓝图路径与存档身份保持 SpiralPillarM14。
- WalkSpeed 从 28 改为 56 cm/s，蓝图和原生默认值均更新。AnimationWalkSpeed 保留原动作源速度 28，实际速度除以源速度后得到 2 倍播放，2.4 秒原地蠕行循环在满速时为 1.2 秒。转弯移动同样按实际位移速度匹配，原地转向仍按真实转向角速度匹配。
- 新死亡动作 A_M14_Death_v02 为 3 秒，0.3 秒开始倾倒，1.8 秒时达到 50 度并沿用原有物理交接时刻。全身由 base 做一致的旋转与平移，其他骨骼固定局部偏移和单位缩放，取消逐级叠加的柱体弯曲及囊体、根裙和链条的独立死亡位移。
- 根据原模型表面计算每个制作帧的最低点，设置倾倒过程的平地高度。预算不足时继续播放至 2.65 秒的侧卧姿态，3 秒保持末姿并由既有尸体流程接地与回收。
- 新建 PA_M14_Corpse_v02，把原有局部凸碰撞形状转换到 base 坐标并作为一个复合刚体使用，不再用 26 个独立刚体及关节牵拉连续皮肤。死亡瞬间切换这份专用资产；活体查询物理资产、模型、权重和其他动作保留。
- 继续使用共享尸体预算、地形碰撞、速度交接、稳定定姿及 20 秒寿命。此次改动不是新的软体物理；落地后各器官不会独立散开。

## 制作判断

旧源码中，死亡主链多级弯曲、刚性金属分区以及独立根裙/囊体物理共同作用于连体表面，存在明显的相对牵拉来源。本轮同时替换动画和尸体驱动，避免仅改动画后仍被旧物理拉坏。未做运行复现或画面验收，不能把这一源码判断报告为已实测的唯一根因，也不宣称画面已验证无尖刺。

## 文件

- [可编辑 V02 Blender](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV02/Authoring/M14_Rigged_Animated_v02.blend)
- [新版死亡 FBX](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV02/Exports/A_M14_Death_v02.fbx)
- [制作记录](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV02/Records/authoring.json)
- [已保存 UE 资产记录](../../SourceAssets/SpiralPillarM14Meshy20261004/ProductionV02/Records/ue_revision.json)
- [动作制作脚本](../../Tools/SpiralPillarM14/revise_death_v02.py) / [导入脚本](../../Tools/SpiralPillarM14/import_revision_v02.py)

UE 蓝图仍为 `/Game/Monsters/SpiralPillarM14/BP_SpiralPillarM14`，新增动画为 `/Game/Monsters/SpiralPillarM14/Animations/A_M14_Death_v02`，死亡物理为 `/Game/Monsters/SpiralPillarM14/PA_M14_Corpse_v02`。V01 动作和制作源保留，修改前蓝图备份在 ProductionV02/Before。

FPSGAMEEditor 与 FPSGAME 的 Win64 Development 后台构建完成，资源已实际导入保存。未启动图形编辑器、运行游戏、截图、渲染或追加测试，由用户在 F6 中生成“螺柱 M-14”体验。
