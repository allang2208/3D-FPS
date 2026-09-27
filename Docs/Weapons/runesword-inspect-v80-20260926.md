> 2026-09-27 归档：本版旧 Export 和已完成的一次性保存助手（如有）移入 `trash/melee-bow-iterations-20260927/` 对应原路径。作者源、原包备份与回执保留；当前转刀为 V82。

# 近战转刀检视 V80：节奏与握柄配合

当前正式 Inspect 已按用户要求退回 [V82](runesword-inspect-v82-20260926.md)，转刀开发暂停。最终 FBX 位于 `SourceAssets/RuneSword20260913/InspectFollowThroughV82/Final/`；本页保留 V80 制作记录。

2026-09-26。用户要求查看当前转刀内容，针对播放机械感和握柄／手部匹配优化。沿用 V79 的动作家族；本次仅制作并接入 Inspect。

同日后续：用户要求待机持剑向玩家靠拢，已按 [靠近身体的待机姿态](../../SourceAssets/SwordIdleClose20260926/README.md) 调整检视的入场／回待机边界。V80 转刀工作段保留；当前正式资产的可编辑完整 FBX 位于该后续作者目录，重新导入本页旧 ExportV80 会覆盖新的待机衔接。

## 对当前动作的理解

当前两套运行目录使用 V79 的 `A_RuneSword_Inspect`，运行组件按真实秒数采样，没有叠加攻击速度。动作顺序为：右移准备、左手放下、腕带下甩、右手正向一圈、右手回握、左手与整组恢复待机。转剑工作窗为 0.400–0.928 秒；120 Hz 导出实际总长约 1.267 秒。

本轮按用户要求查看了原参考的分解图及 V79 作者动画的第一人称／握柄近景采样。观察使用当前 V7 裸手表面，原始坐标与权重保持；未打开 UE、未运行 PIE。Blender 观察画面用于理解作者动作，不作为游戏验收。

发现的具体问题：

- V79 转角前段推进过快，后段在已经接近回正的位置拖慢。它已有曲线，并非简单匀速，但快慢分布削弱了转柄和接刀的可读性。
- 旧接触选择在所有右臂顶点中取最近点，实际选在武器局部 z≈−9.92 cm 的握柄下部。固定这个点不能代表虎口支撑。
- 腕部限幅会调整最终手朝向；旧版随后只重算武器位置，闭握时没有恢复完整的手—柄相对变换。
- 各指主要按同样的握姿→rest 插值开合，接近完成转动时提前收指；拇指、食指的支撑与其余手指的让位不够明确。

## V80 制作内容

- 保留方向、准备右移 16 cm、起手下甩、0.400–0.928 秒转剑窗与总时长。重新安排转角的加速、顺势旋转与末段制动，避免前段飞快掠过、最后少量角度长时间拖慢。
- 掌向继续沿用 V79 的相位动作。收指跟转角阶段推进，延后到柄回到掌内；中指、无名指、小指依次让位和回握，拇指与食指保留支撑弯曲。手指插值只改旋转，不插值骨段平移或缩放。
- 在 V7 实际蒙皮上选择拇指根部、护手下方的握柄接触（武器局部 z≈−3.70 cm），自由转柄时由该蒙皮顶点驱动接触位置。
- 在腕部限幅和手指姿态完成之后解算武器。回握时逐步恢复完整的 `Hand × inverse(Grip)`，同时对齐位置和方向。
- 回收采用连续加速度的五次曲线。保留原腕部限制、原骨长与零帧／结束待机关系。
- 普通柄、长柄分别从 `RuneSwordWristLocked20260920/Standard` 与 `LongGrip` 的待机源制作，长柄不再直接使用普通柄的同一 FBX。

## 文件与接入

作者目录：`SourceAssets/RuneSword20260913/InspectRhythmContactV80/`。

- `author_inspect_v80.py`：完整作者脚本；追加 `-- --long-grip` 制作长柄。
- `visible_bare.py`：引用认可 V7 表面，不修改共享裸手源。
- `AzureRunesword_InspectRhythmContactV80.blend`、`AzureRunesword_InspectRhythmContactV80_LongGrip.blend`：可编辑源。
- `ExportV80/A_RuneSword_Inspect.fbx`、`ExportV80/LongGrip/A_RuneSword_Inspect.fbx`：两套导出。
- `import_inspect_v80.py`、`run_import.ps1`：仅导入两套 Inspect，使用现有资产互斥；不会关闭或重启应用。
- `BeforeV80/Standard`、`BeforeV80/LongGrip`：导入前原资产副本。
- `import_receipt_v80.json`：实际保存回执；包含路径、时长及导入前后文件散列。

目标资产：

- `/Game/Weapons/AzureRunesword20260913/A_RuneSword_Inspect`
- `/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_Inspect`

运行引用保持原路径，未修改 C++、攻击、格挡、走路触发／打断逻辑或共享手模。无需原生重编译。

## 交付边界

已按要求完成 V79 动画内容查看。V80 两套 Blend／FBX 已制作，2026-09-26 17:25（北京时间）通过后台 commandlet 导入并保存上述两套正式 Inspect，实际片段长度均为 1.26666665 秒，保存回执已落盘；原生代码未变，无需重编译。未启动游戏、未做优化后的运行测试或验收，最终节奏与握柄贴合由用户试玩判定；作者计算值不作为视觉通过结论。原有运行进程未被本任务关闭或重启，已加载动画需用户自行重新加载后使用新版本。
