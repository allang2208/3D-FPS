# 近战检视 V82：接刀让力、分步回握与接触迁移

当前正式 Inspect 已按用户要求从 V83 退回本版，转刀开发暂停。两套正式包均从 V83 接入前备份精确恢复，回执见 `SourceAssets/SwordGuardLeftRepair20260926/inspect_rollback_v82.json`。可重导的最终 FBX 位于 `SourceAssets/RuneSword20260913/InspectFollowThroughV82/Final/`。

用户于 2026-09-26 要求按上一轮四项建议全面优化。以 V81 为基础，只制作普通柄、长柄两套 Inspect；继续采用认可的 V7 裸手表面和各自原生握距。

**接入已完成**：当前 MCP 批次返回普通柄、长柄均已保存；两套正式包、最终 FBX、衔接编辑键与保存回执均已落盘。

## 动作编排

1. **右手接刀与让力**：在约 0.782 秒、旋转进入 353° 后逐渐承接剑的惯性；0.8504 秒达到一次让力峰值，0.9804 秒归零。手、前臂和剑共同转动最多 4.2°，手位向下 9 mm、向玩家方向 3.5 mm；按既有臂长重解肩肘。没有添加往复抖动或停帧。
2. **左手分步回握**：0.8424 秒开始返回，0.9774 秒掌根到位。掌向与位置逐渐跟随右手接刀解算后的实际剑根，而非仅回到一个独立的待机目标。食指、中指、无名指、小指按各自时钟收拢，拇指最后压稳；近端关节稍早、末节稍晚，最晚约 1.1074 秒收完。保持手指局部平移、缩放与骨长。
3. **转柄接触迁移**：从 V7 虎口和食指近端表面选取两个真实蒙皮支撑点，并分别对应附近握柄表面。转动中连续混合两侧接触，限制手部接触迁移不超过 4 mm、握柄侧不超过 3 mm；接刀前回到虎口支撑，持握时仍恢复完整手—柄相对变换。没有新增运行时追踪或实时 IK。
4. **下甩接起转**：肘臂前倾从 0.245 秒开始蓄力，早于手的最低点；下甩保留约 7 cm 的作者位移幅度，让手在初始旋转中继续处于低位，前臂随转角推进卸力。手、前臂与剑共同支撑，避免把更大姿态差强塞进腕关节。

## 保留的节奏与衔接

- 转刀曲线与 V81 一致，工作窗仍为 **0.400–0.8224 秒**，保留相对 V80 加速 25% 的设置，不叠加新的播放倍率。
- 作者总长、准备段与回收时长保持 V81；左手最后的闭合在原有末尾留白内完成。120 Hz 导出为 139 个帧间隔，正式片段约 1.158333 秒。
- 导入后按普通柄、长柄各自当前 Idle，重做靠近身体的起止衔接，保留首尾待机锚点和当前握距。
- 不修改攻击、格挡、移动触发、状态切换或伤害时钟；此次没有 C++ 修改，无需原生编译。

## 可编辑源与接入

作者目录：`SourceAssets/RuneSword20260913/InspectFollowThroughV82/`。

- `author_inspect_v82.py`、`visible_bare.py`：作者脚本与 V7 表面入口；长柄追加 `-- --long-grip`。
- `AzureRunesword_InspectFollowThroughV82.blend`、`AzureRunesword_InspectFollowThroughV82_LongGrip.blend`：两套完整可编辑作者源。
- `ExportV82/`：作者中间 FBX，尚未叠加当前靠近身体的待机偏移。
- `Final/Standard/A_RuneSword_Inspect.fbx`、`Final/LongGrip/A_RuneSword_Inspect.fbx`：导入阶段制作的完整最终 FBX，包含当前待机衔接；后续直接重导使用这些文件。
- `Final/*/Inspect_idle_handoff_keys.json`：首尾衔接编辑键。
- `import_inspect_v82.py`：仅接入两套 Inspect，以 V81 保存散列保护并行修改，沿用现有压缩设置。
- `BeforeV82/*`：接入前包备份；`import_receipt_v82.json`：正式保存回执。

目标引用保持：

- `/Game/Weapons/AzureRunesword20260913/A_RuneSword_Inspect`
- `/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_Inspect`

已有编辑器通过当前 MCP 桥的批次互斥接入，只保存上述目标包；没有打开、重启编辑器或启动游戏。未追加测试、截图、渲染或验收，最终观感由用户试玩确认。

作者记录中的 `primary_anchor_motion_m` 是原始虎口锚点的运动量，包含本版有意制作的接触迁移，不能当成新的接触误差验收值；作者生成记录也不代表运行视觉通过。
