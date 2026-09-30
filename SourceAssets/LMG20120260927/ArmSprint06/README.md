# 201 前臂与战术冲刺修复（ArmSprint06）

后续状态：用户再次否定本版肘部形变。前臂旋转分配已由 [Skin07](../Skin07/README.md) 替代；本版冲刺收手与手部接触继续沿用。下文为历史制作记录，其中“原生辅助骨相对关系保持”不能作为实际蒙皮不扭曲的证明。

用户指出 Support05 的左小臂仍扭曲、战术冲刺左手没有收回，并要求参考 Skill 已积累的方法排查修复。

## 原因

1. Support05 对 `sprint_enter/loop/exit` 同样使用恒定 `WPN_root × support`，把原本自由撤下的左手重新锁到护木。这是本轮源动画可直接复现的问题，运行组件本来就正确读取 201 的三条专用冲刺动画。
2. Support05 的腕臂求解又额外叠加 `0.72`、`0.60 + 0.35 × along` 两套扭转比例。原生 AKM 骨架本来已有自己的辅助骨关系；追加分数扭转改变了同一骨段内的蒙皮关系。全掌旋转差也混进了前臂 roll，未遵守 Skill 对腕部背屈与轴向扭转的区分。

## 复用的现有方法

- Skill `ue5-fps-arms-animation/references/pose-contact.md`、`casting-arm-volume.md`：完整骨段、掌宽轴确定前臂 roll、避免对主骨和辅助骨重复叠加分数扭角。
- Skill `grip-arm-refinement.md`、`accepted-bare-hands.md`：固定现有接触与 V7 原生表面、骨长和蒙皮；按实际 rig 保留已经成立的辅助骨关系。
- `Docs/Weapons/akm-sprint-left-wrist-relax-20260917.md`：AKM V4 的提前收手、肩心弧线、自然下垂、局部腕关节放松与渐进松指。
- `SourceAssets/RifleTacticalSprint20260915/author_sprint.py::make_pose` 和同目录 `sources.json` 的 AKM 配置：直接读取这些现有函数制作 201 的左臂，不改 AKM/191 文件。
- `SourceAssets/DanWesson71520260913/author_weapon.py::hand_at`：同一 AKM 冲刺作者源使用的完整两骨段求解。
- `Source/FPSGAME/Skills/FPSCastingMeshComponent.cpp`：掌宽投影生成前臂朝向，以及小幅上臂滚转分担。

## 修改范围

- 保留 Support05 的正常持枪手腕和手指世界接触，移除该版自定肘面与额外分数扭转，使用现有完整腕臂方法重新适配。前臂主骨与辅助骨共同携带原生骨段关系，不把辅助骨一律清零，也不重做手指抓握。
- 冲刺单独制作：松指让开 → 肩下弧线收手 → 自然下垂随步幅摆动 → 反向回握。手的位置与方向在离枪后独立于 `WPN_root`。
- 三条冲刺按原有 0.30 / 0.60 / 0.30 秒保留时钟，按现有 AKM 作者流程烘焙 120 Hz；只替换左臂动作，右手和枪体使用上一版同时间的源姿态。
- 普通/空仓换弹和检视按原支撑权重接入腕臂修正，自由手势、弹匣接触与右手拉柄时序不改变。
- 模型、权重、材质、共享骨架参考姿态和 C++ 均未修改。本轮输出 12 条动画。

## 用户要求范围内的源排查

`source_diagnosis.json` 保存修改前与成熟供体的骨段关系、腕部位置和冲刺轨迹；`focused_source_checks.json` 对保存后的 Blend 动作逐帧回读，覆盖辅助骨关系、原持枪接触、右手/武器轨道与冲刺五处接缝。

修订后的 Enter 末端、Loop 首尾和 Exit 起点左臂矩阵一致；待机与 Enter/Exit 边界只有浮点误差。辅助骨相对原生骨段的矩阵最大元素偏差约 `5.96e-7`，正常持枪接触和右手/武器矩阵只存在浮点误差。冲刺 Enter 左手有约 0.736 m 的实际撤离轨迹，不再跟枪固定。

这些是针对本次反馈的源数据检查，不是实机蒙皮或视觉验收。没有启动 GUI、PIE、截图或渲染；游戏观感仍待用户测试。

## 作者和接入文件

- `LMG201_ArmSprint_Editable.blend`：修订后的完整待机作者母版。
- `Motions/A_LMG201_*.blend`、`Exports/A_LMG201_*.fbx`：12 条可编辑动作与导出。
- `arm_recipe.py`、`author_motion.py`：现有方法的复用及 201 阶段适配。
- `import_animations.py`：批次互斥下导入保存到 `/Game/Weapons/LMG201/Production20260927/Animations`。
- 修改前备份目录 `/Game/Weapons/LMG201/ArmSprint06/Before/Animations`。
- 实际保存进度和完成状态见 `import_receipt.json`、`DELIVERY.json`，不以导入脚本存在代替接入完成。

12 条动画已通过带批次互斥的无界面 commandlet 导入并保存，修改前 12 条备份也已落盘；未打开或重启 UE GUI。
