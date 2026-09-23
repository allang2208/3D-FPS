# 突变体-3：参照原动作修正飞扑手臂扭曲（2026-09-23）

当前版本与恢复顺序见 [突变体发布入口](Mutant3FeralPublication20260923.md)。本文保留阶段记录；其中 before/baseline 快照及已退役独立手臂求解已按归档清单移至 trash。

后续[贴图修复](Mutant3TextureRepair.md)已将默认查看图改为带贴图版本；最初查看手臂形变的白模图另存为 `refined_export_arms_clay.png`。手臂和动作曲线没有因此改变。

用户反馈上一版双爪下挥出现手臂扭曲。本修订替代 `pounce_downclaw` 的固定肘部方向与独立手腕朝向求解，正式飞扑资产已通过现有编辑器的 MCP 批次互斥导入并保存。

## 原因与处理

对照原 Khaimera `RMB_60fps` 及尚未叠加上次 IK 的重定向动作，上一版腾空片段的前臂局部旋转相对同一时刻原动作最大偏离约 149°，手腕约 178°。固定肘部方向和强制手掌朝下破坏了原肩、肘、腕之间的配合；目标模型没有原 Khaimera 的上臂、前臂扭转辅助骨，外观问题尤其明显。

原动作真正的下挥发生在源时间约 0.60–0.88 秒，并同时伴随明显俯身。仅提前手臂而保留另一时刻的直立躯干，仍需过大的肩部补偿，因此最终版本统一重排完整原姿势的时间，保留原肩、肘、腕、躯干和骨盆的协调，不再设置 IK 肘部方向、肩部补偿或手腕朝向覆盖。

- 从 `claw_reference_20260923/Mutant3_OpenClaw_Animated.blend` 的原有接地动作取样，保持已制作的张开爪形与指骨绑定。
- 蓄力恢复干净的原版本，时长 0.60 秒。
- 腾空映射原动作 0.08–0.92 秒，时长 0.65 秒；原下挥段移到腾空约 0.402–0.619 秒。
- 落地从同一原姿势 0.92 秒继续到 2.25 秒，时长 0.80 秒。
- 所有骨骼的位移、旋转和缩放按同一源时刻烘焙，四元数保持相邻关键帧同半球。源落地片段已有的接地修正随姿势保留。

沿用现有角色飞行、碰撞、伤害和落地过渡代码，没有修改 C++、正式模型、蒙皮权重或其余六段动作。

## 已保存资产

正式目录 `/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations`：

- `A_Mutant3_PounceWindup`
- `A_Mutant3_PounceFlight`
- `A_Mutant3_PounceLand`

保存三段动画及沿用的 `SK_Mutant3_Claw_Skeleton`。导入记录返回 `MUTANT3_POUNCE_REFERENCE_RAKE_SAVED 3 animations`；逐项保存记录在作者目录 `import_state.json`。使用已经运行的编辑器完成资产接入，没有另起编辑器或启动游戏。

## 本次定向查看

按用户要求比对了原参考动作与手臂扭曲：作者文件中左右肩、上臂、前臂、手腕及原掌骨的旋转与对应源姿势最大数值偏差小于 0.1°；蓄力到腾空的手臂端点相同，腾空到落地的端点数值差小于 0.1°。该微小差值包含浮点角度计算误差。

另从实际导出的 FBX 读取蒙皮，在腾空 0.18、0.45、0.60 秒查看正面与侧面，确认原抬臂姿势连续进入俯身下挥，未再使用上一版强制翻腕。查看图为 `refined_export_arms.png`，相关数值为 `refinement_inspection.json`。这些是用户指定的离线手臂与参考动作检查，不代表运行时验收；游戏内观感及落地表现交由用户测试。

## 作者文件

`SourceAssets/Mutant3Khaimera20260923/pounce_arm_refine/`：

- `author_reference_rake.py`、`Mutant3_Pounce_ReferenceRake.blend`：最终完整姿势重排配方与可编辑源。
- `animations/`：正式使用的三段飞扑 FBX。
- `animation_contract.json`：每帧源时间及片段时长。
- `import_reference_rake.py`、`import_state.json`、`import-bridge-02.txt`：接入与保存记录。
- `before_content/`：本次覆盖前的三段动画和骨架本机副本。
- `reference_arm_inspection.json`、`reference_vs_previous.png`：原动作与上一版问题的对照。
- `inspect_refined_export.py`、`refinement_inspection.json`、`refined_export_arms.png`：本次手臂定向查看资料。

后续重新导入这三段飞扑应使用本目录的最终导出。`pounce_downclaw`、本目录的 `author_arm_only_attempt.py` 均为被替代的制作过程，不能作为现行飞扑来源。
