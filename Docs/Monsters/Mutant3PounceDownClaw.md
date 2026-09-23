# 突变体-3：飞扑双爪下挥（2026-09-23）

当前版本与恢复顺序见 [突变体发布入口](Mutant3FeralPublication20260923.md)。本文保留阶段记录；其中 before/baseline 快照及已退役独立手臂求解已按归档清单移至 trash。

本页记录的固定肘部方向与独立手腕朝向版本已因手臂扭曲被替代。当前正式版本见[参照原动作修正飞扑手臂](Mutant3PounceArmRefine.md)，后续重导入使用 `pounce_arm_refine/animations`。

按用户要求，将飞扑的双臂与手腕微调为双爪向下抓击。沿用刚按用户照片重做的张开爪形：四指外展、中末节内钩、拇指保留开口。

## 动作制作

- 蓄力后段逐渐把双爪带到抬爪姿势，与腾空首帧衔接。
- 腾空前 0.18 秒抬爪蓄势，随后沿前下方弧线双爪下挥，到 0.60 秒完成下抓。
- 手腕随挥落转向，指尖朝抓击方向；双手分居身体左右，不向中线交叉。
- 落地前 0.12 秒继续小幅下压，随后回收，到落地片段 0.70 秒回到原动作。

使用双段手臂求解，在实际上臂和前臂长度内确定手腕位置，再单独调整手掌朝向。仅重写左右 `Arm`、`ForeArm`、`Hand` 六根骨的旋转曲线；手指保留新爪形，模型与绑定不变，肩骨、躯干、骨盆及腿部曲线沿用已有接地版本。

蓄力、腾空和落地时长仍为 0.60、0.65、0.80 秒。角色飞行、碰撞、伤害与 0.14 秒落地上身混合继续由原代码处理，本次没有修改 C++。

## 正式接入

更新 `/Game/Monsters/Mutant3Meshy/KhaimeraV2/Animations` 中：

- `A_Mutant3_PounceWindup`
- `A_Mutant3_PounceFlight`
- `A_Mutant3_PounceLand`

首次经现有 MCP 批次互斥等待接入时，编辑器已退出，因此未执行在线导入。随后将当前模型、骨架与三段动画复制到隔离的 `UEAuthoring/Mutant3Khaimera.uproject`，用后台 Python commandlet 完成导入；在主编辑器未运行且正式文件未被并行改动的条件下，将三段动画及保存的 Skeleton 包写回正式 `Content`。正式接入已完成，记录为 `MUTANT3_POUNCE_DOWNCLAW_INSTALLED 4 packages`，清单在作者目录 `import_state.json`。

没有重新打开交互式编辑器，没有重导入正式模型或改动其余六段动作；Skeleton 沿用当前张开爪形的绑定。

## 作者文件

`SourceAssets/Mutant3Khaimera20260923/pounce_downclaw/`：

- `author_pounce_downclaw.py`：手臂路径、手腕方向、抬爪与收势混合配方。
- `Mutant3_Pounce_DownClaw.blend`：含本次飞扑修订及先前张开爪形的可编辑源。
- `animations/`：三段飞扑 FBX。
- `import_pounce_downclaw.py`、`import_state.json`：正式接入脚本与保存记录。
- `before_content/`：三段动画及 Skeleton 保存前的本机恢复副本。

本修订曾覆盖 `claw_reference_20260923` 中三段飞扑的手臂姿态，目前仅保留为制作历史；现行飞扑以 `pounce_arm_refine` 为准。

未启动游戏、制作验收渲染或执行额外测试。实际观感由用户在 F6 中重新生成突变体-3 后确认。
