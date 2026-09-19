# M4 快速近战 K：肩部约束与统一肘部弯曲

> 整理状态（2026-09-19）：本目录保留参考／作者依赖，不是当前运行母版。最终 M4 为 N；QBZ191 为 O；收势使用统一 runtime recover。完整入口见 [发布与恢复](../../Docs/Weapons/quick-melee-publication-20260919.md)。


2026-09-19，用户反馈 J 的左小臂、上臂、肩部仍扭曲，右侧肩部模型开口被带到画面中。K 针对这两项继续制作，保留已认可的挥击方向、双手握点与时序。

## J 的机制问题与修改

J 的肩部先向手腕方向补偿最多 7 cm，随后又在肩腕距离超限时继续向前移动；第二段没有后侧位置约束。即使枪先后收 9 cm，肩根仍可能被自动追手补偿推向镜头前。

K 取消这两段肩部追手补偿。工作阶段右肩作者坐标为 `(0.12,-0.12,-0.14)` m，左肩为 `(-0.28,-0.14,-0.16)` m；作者坐标 +Y 朝前，肩部支撑保持在相机后侧。起止阶段平滑衔接原待机肩位。

枪械与双手作为同一组刚体，按两臂各自可达范围共同收回。工作阶段肩腕最大距离取上臂、小臂总长的 91%，骨长、缩放与手指姿态沿用源。由此产生的位移包含后收、适量回中与下移；具体最大位移记录在 `authoring.json` 的 `support`，不是整个动作固定减同一段距离。

左臂与右臂均改用同一肘部弯曲平面构造大小臂方向。上臂与上臂辅助骨完整随该骨段运动，取消 J 的上臂分段额外轴向旋转；剩余掌面扭转沿前臂辅助骨分布。肘位在受限范围内兼顾腕部折弯、旋前和肘部外侧位置，避免累计肘部极向角继续绕圈。

没有新增遮挡模型、隐藏手臂、缩放骨骼或修改蒙皮。肩部模型开口是否仍会在运动中露出，需用户实机观察。

## 文件与接入

- `fit_reference_motion.py`、`reference_motion.json`：保留 I 的武器旋转和 J 的 9 cm 基础后收。
- `arm_support.py`：肩后侧支撑、整组可达性修正、肘部弯曲平面与前臂扭转。
- `author_replica.py`：六种握把各自的可编辑 Blend / FBX，120 Hz、0.9 s，接触仍为 0.1667 s。
- `import_replica.py`：继续覆盖当前 M4 专用 `/Game/Weapons/M4QuickMeleeReplica20260919/<Profile>/A_M4_QuickCombat_<Profile>`。
- 可编辑源：`<Profile>/M4_QuickCombat_<Profile>_Editable.blend`。
- FBX：`<Profile>/Animations/A_M4_QuickCombat_<Profile>.fbx`。

J 版源和覆盖前 UE 动画备份已归档到项目 `trash/quick-melee-retired-20260919/SourceAssets/M4QuickMeleeRefine20260919J/` 与 `trash/quick-melee-retired-20260919/SourceAssets/M4QuickMeleeRefine20260919K/BaselineJ/`。K 的作者源和支撑解算仍被 N／跨枪版本依赖，继续保留。

本轮没有修改 C++、材质、镜头、命中时钟或技能数值，不需要原生构建。制作、导入回执分别为 `authoring.json`、`import.json`；未启动游戏、渲染或运行验收，由用户测试。

交付回执：六套动画导入并保存为 0.9 s，Python 导入进程返回 0（`import.json`、`import-engine.log`）。Base 相对 J 最大额外后收 0.1663 m、最大三维位移 0.1976 m，属于制作输出记录。
