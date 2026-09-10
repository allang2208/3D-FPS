# MAT / Control Rig 的已验证用法

MAT 是 Locodrome 的 Editor Utility Widget，辅助 Sequencer / Control Rig 编辑，不会自动修好任意手模的权重。以下来自本机 `SourceAssets/M4HandMATRepair20260910/README.md`、`mat_nudge.json` 及最新烘焙脚本；不是所有 MAT 版本、所有 rig 的功能承诺。

## 手工编辑入口

1. 在 UE 打开目标 Level Sequence。当前序列路径见 [M4 基线](m4-baseline.md)，不回到已淘汰的早期 HandMATRepair 动画作为运行源。
2. 对 `/Game/Locodrome/MAT/Locodrome_MAT` 执行 **Run Editor Utility Widget**。
3. 在 MAT 的 Rig 列表选中该序列的 Control Rig，必要时刷新。只打开 Skeletal Mesh 不足以建立编辑上下文。
4. 选 `hand_l_fk_ctrl`、`hand_r_fk_ctrl` 或对应指节控制器，定位明确帧，微调并写关键帧；读回所选控制器数值验证操作生效，再查看模型。
5. 保存序列。若运行时播放的是 AnimSequence，还需要把最终修改烘焙/导出到候选 AnimSequence、核对压缩姿态并更新实际引用；保存 Level Sequence 本身不会自动改变 C++ 加载的 clip。

历史实测 MAT W 将选中食指控制器约 -36.999° 调到 -35.999°，S 恢复；测试改动已撤回。不要把 W/S 当任何轴、模式下固定语义的全局快捷键。Tween 在当时的密集曲线上未改变数值，不能据此宣称已用 Tween 修改动画。

当前定制 rig 只有 FK，具备正解/反解；MetaHuman 的 Keep Aligned、手指自动插值及完整 FK/IK 切换依赖相应通道，不能假设此 rig 支持。需要 IK 时先检查并建立相应控制，不用按钮成功点击代替姿态验证。

## 从已验证动画建立可编辑序列

最新本机可复用脚本：`SourceAssets/M4TacticalToss20260910/build_mat_sequences.py`（普通）、`M4SlapImpact20260910/build_mat_sequences.py`（空仓）、`M4WrapGrip20260910/build_mat_sequences.py`（装备参考）。复制到新候选目录后再改目标路径，不覆盖其他分支。

关键步骤：

- 载入匹配的 mesh 与 `/Game/Weapons/M4ContactImpactFinal/CR_M4_ContactImpact`，先 `rig.recompile_vm()`；未编译 VM 曾导致空通道/无效烘焙。
- 在有 editor world 的 GUI 编辑器上下文创建序列、spawnable 和 Control Rig track；这一 Control Rig 导入流程在 nullrhi commandlet 中不能视为已验证可用。
- `set_display_rate(FrameRate(480,1))`，明确 playback 起止和独占结束帧。普通 1009、空仓 1297、装备 305 个样本；不能把 60 Hz 逻辑帧直接当作 480 Hz 序列帧。
- 使用 `load_anim_sequence_into_control_rig_section_with_range`，本案例关闭 key reduction，并使用 LINEAR。重建已有候选绑定前确认归属。
- 保存后独立进程读取通道和键数量，且对最终 AnimSequence 的压缩姿态另行采样。909 个通道只证明本 rig 数据存在，不证明接触或观感。

## 已知退出故障

本机辅助编辑器在保存后关闭 Sequencer 时出现过 EXCEPTION_ACCESS_VIOLATION。将“烘焙成功标记、磁盘保存、独立读回、游戏运行”和“辅助进程退出失败”分别记录。不能仅凭中间 PASS 忽略失败，也不要在资产已保存且读回正确时反复重烘焙。新错误先调查；不要误停用户或其他任务的编辑器。

作者说明入口保存在上述本地 README 中。要研究未验证的新 MAT 功能时，再查看当前作者手册及已安装版本；不要从这些实测片段推断支持情况。
