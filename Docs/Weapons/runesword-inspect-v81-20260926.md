> 2026-09-27 归档：本版旧 Export 和已完成的一次性保存助手（如有）移入 `trash/melee-bow-iterations-20260927/` 对应原路径。作者源、原包备份与回执保留；当前转刀为 V82。

# 近战检视 V81：下甩发力与转刀加速

当前正式 Inspect 已按用户要求退回 [V82](runesword-inspect-v82-20260926.md)，转刀开发暂停。转刀仍保留加速 25% 的设置；最终 FBX 位于 `SourceAssets/RuneSword20260913/InspectFollowThroughV82/Final/`。本页保留 V81 制作记录。

2026-09-26。用户在下甩姿态诊断后要求调整优化，并将转刀加速 25%。普通柄与长柄两套正式 Inspect 已导入并保存。

## 制作内容

- 增大手部向前下方的发力轨迹，并让低位延续到旋转起段，避免最低点一闪而过。
- 发力段增加最高 22° 的前倾，由前臂、手和剑共同完成。重解肘肩支撑，保留上臂、前臂长度；共同旋转不改变手相对前臂的腕部姿态。
- 发力末段保留握柄，延后中指、无名指、小指的大幅张开，再按转角逐步让位。最终手指姿态与手表面接触解算之后更新剑的持握位置。
- 转刀工作窗由 V80 的 0.400–0.928 秒缩短为 0.400–0.8224 秒，即工作段速度乘 1.25。准备段、回收段与末尾停留的设计时长保留。没有额外叠加运行时播放倍率。
- 普通柄、长柄各自制作。导入后，以各自当前 Idle 重做靠近身体的入场／回待机衔接，首尾编辑骨轨道取各自当前待机锚点。

两套正式动画均为 120 Hz、139 个帧间隔，实际总长约 1.158333 秒。时间落在导出采样网格上，因此总长与连续作者曲线的 1.1624 秒存在取整差异。

## 正式资产与可编辑源

目标引用路径保持不变：

- `/Game/Weapons/AzureRunesword20260913/A_RuneSword_Inspect`
- `/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_Inspect`

作者目录：`SourceAssets/RuneSword20260913/InspectDownstrokeV81/`。

- `author_inspect_v81.py`、两个 `AzureRunesword_InspectDownstrokeV81*.blend`：下甩、转刀、手指与接触作者源，沿用认可的 V7 裸手表面。
- `ExportV81/`：上述作者动画的中间 FBX，尚未叠加当前靠近身体的待机衔接。
- `Final/Standard/A_RuneSword_Inspect.fbx`、`Final/LongGrip/A_RuneSword_Inspect.fbx`：含当前待机衔接的完整最终 FBX；正式资产的导入来源已指向这里。后续直接重导应使用这些文件。
- `Final/*/Inspect_idle_handoff_keys.json`：首尾衔接的编辑骨逐帧轨道。
- `import_inspect_v81.py`：仅替换两套 Inspect，保留压缩设置，并在导入后生成最终衔接及完整 FBX。
- `BeforeV81/*`：本次接入前正式包备份。
- `import_receipt_v81.json`：两套正式资产的实际保存回执、时长、作者源和文件散列。

## 保存与交付范围

本次沿用已运行编辑器及现有 MCP 批次互斥。编辑器处于试玩状态，通用 EditorAssetLibrary 保存接口拒绝保存；改用引擎公开的包保存接口，只保存本次两个目标包，没有中断试玩、关闭或重启编辑器。首次普通柄导入已经完成的内存修改，通过 `finish_pending_standard.py` 接续落盘；没有用旧包覆盖内存。

本批次不依赖 PIE 下不可用的资产元数据接口记录版本；版本及制作来源以本目录回执、最终 FBX 和资产导入文件路径为准。

没有 C++ 修改，无需原生编译。未追加运行测试、截图或渲染；下甩的实际观感、加速后的接刀可读性及手柄贴合由用户试玩确认。此前衔接检查的范围与仍保留的瞬发反击硬切问题，仍见 `sword-idle-handoff-review-20260926.md`。
