# M24 右手指尖修订 — 2026-10-28

本轮针对用户反馈的拉栓拇指与右手手指问题。按 `ue5-fps-arms-animation` 的原生轴向、自然握持和局部修订规则制作。

## 根因与修正

- V9 右手末节的实际蒙皮沿骨骼 **负 X** 轴延伸。旧迁移和松手脚本使用正 X，令拇指末节反折约 150–170°，其余指尖也发生同类折返。
- 保留当前掌心、腕臂和枪械轨道，只替换五根右手 `*_03_r` 末节的旋转。拇指采用原生局部 Z 屈曲，接触段轻弯、松开段舒展；无名指和小指末节按栓柄、镜身的空隙调整。
- 沿用当前抬栓、后拉、推回、闭锁和回握时点，并重接松手与回握曲线。所有原有位移、缩放曲线保留。
- 修正 `M24BoltRematch20261027/author_candidate.py` 和 `M24GripFinish20261028/author_finish.py` 中的负 X 方向；修改前脚本位于 `SourceBackups/`。

## 已保存接入

最终 `install_receipt.json` 记录四个资产的保存结果：

- `/Game/Weapons/M24/MotionPolish20261027/DA_M24_SupportGrip`
- `/Game/Weapons/M24/MotionPolish20261027/DA_M24_Mag10`
- 上述两套配置在 `/Game/Weapons/M24/Thumb20261028/` 下的独立制作副本。

作用于射后拉栓 `fire`、独立拉栓 `cycle`、默认空仓换弹 `reload_empty` 和 10 发空仓换弹 `reload_empty_mag10`。保留其余动作、原始动画序列、模型、骨架、蒙皮、机械时序和上一版镜头反馈。本轮没有 C++ 修改。

`Backups/` 保存此次修改前的两套活动配置及 JSON。通过现有批次互斥锁和无界面 commandlet 完成保存，没有主动打开编辑器或运行游戏。

## 检查边界

- 进行了源动作手背/掌侧近景检查。
- 拉栓接触段第 12–43.5 帧按半帧采样，五根已修改末节的蒙皮采样点未检测到枪体、栓柄和瞄准镜的穿入。记录见 `intermediate_review.json`；这是源模型表面采样，不能代表完整实机验收。
- 当前未修改的拇指根部及掌侧仍有之前记录的少量约 1–2 mm 表面重叠；本轮没有移动整手去追逐这些点。
- 源姿态中所有非末节骨骼矩阵保持不变。资产读回结果写入 `saved_readback.json`；记录仅针对本轮动作与曲线。
- 未进行 PIE、实机播放或音画验收，最终体验由用户确认。

## 制作文件

- `M24_Thumb_Editable.blend`：四段动作的可编辑源文件。
- `M24_Thumb_Before_After.gif`：源动作近景前后对照，约 0.67 倍速；非游戏截图。
- `ue_before.json`：固定的原始输入快照，重新制作时保留此文件，不用修订后的配置覆盖它。
- `author_thumb.py`：从该快照重建局部修正，并生成 `rotation_patch.json`。
- `install.py`：仅合并本轮末节旋转，保留其他曲线；`run.ps1 -Stage install` 使用项目既有资产批次入口。
- `read_after.py` 和 `check_saved.py`：本轮用户要求的落盘读回检查入口。
