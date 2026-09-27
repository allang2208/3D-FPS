> 已撤回：V83 全部源与产物现位于 `trash/melee-bow-iterations-20260927/SourceAssets/RuneSword20260913/InspectHandLeadV83/`；保留 V82，转刀开发暂停。下文仅为历史制作记录。

# 近战检视 V83：由手驱动的蓄势与下压

**已撤回**：用户反馈本版不符合预期，2026-09-26 已将普通柄、长柄正式 Inspect 精确恢复到 [V82](runesword-inspect-v82-20260926.md)，并暂停转刀开发。本页以下为历史制作记录；不要将本版重新接入。恢复回执位于 `SourceAssets/SwordGuardLeftRepair20260926/inspect_rollback_v82.json`。

2026-09-26。用户反馈 V82 的蓄势和向下发力手部姿势仍不明显，要求继续优化。制作范围仍为普通柄、长柄两套 Inspect，使用各自原生握距与认可的 V7 裸手表面。

**接入已完成**：2026-09-26 19:28（北京时间）后台 commandlet 导入并保存普通柄、长柄两套正式资产，最终 FBX、衔接编辑键和保存回执均已落盘。两套片段均为 139 个帧间隔、约 1.158333 秒。

## 修改内容

- 为蓄势和下压分别制作手掌朝向与有正负方向的腕部折角。手掌相对展示基准的俯仰目标为 +14°／−12°，腕部折角目标为 +12°／−10°。这些是作者控制参数，不是屏幕投影角度或实机验收结果。
- 手部目标在 0.10–0.21 秒渐进接管，在蓄势／下压阶段完整保留，到 0.418–0.492 秒交还自由转柄。持握阶段按 `Weapon = Hand × inverse(Grip)` 让剑跟随手，避免强握柄权重把作者手姿覆盖回剑的姿态。
- 从目标手姿向前臂、肘和肩解算支撑，保持原上臂／前臂长度。过渡时若腕部折角超出原有 22° 包络，调整前臂方向支撑目标手姿；不放宽全局腕部限位。手驱动阶段取代旧的整臂统一下倾叠加。
- 0.235–0.290 秒为蓄势高点的 55 ms 可读窗口，随后约 90 ms 下甩，0.380–0.430 秒为低点的 50 ms 可读窗口。位移保留细微变化，没有插入静止帧。
- 高点手位作者偏移约 +3.6 cm，低点约 −6.6 cm；准备时稍向画面内侧收回，最大向前送手由 V82 的 5.5 cm 降至 2.4 cm，突出上下变化。
- 四指保持闭握到下甩末段，再跟随旋转逐渐让位。保留 V82 后续的转柄接触迁移、接刀让力与左手分步回握。

## 保留项

转刀时钟仍为 **0.400–0.8224 秒**，保留此前相对 V80 加速 25% 的设置；没有增加播放倍率或延长片段。120 Hz 作者导出为 139 个帧间隔。普通柄与长柄导入后分别接回当前靠近身体的 Idle，首尾锚点及各自握距沿用现有资产。

没有修改 C++、输入、攻击／格挡／移动状态或伤害时钟，无需原生编译。

## 文件与接入

作者目录：`SourceAssets/RuneSword20260913/InspectHandLeadV83/`。

- `author_inspect_v83.py`、`visible_bare.py`：本版作者脚本及认可手模入口；长柄追加 `-- --long-grip`。
- 两个 `AzureRunesword_InspectHandLeadV83*.blend`：完整可编辑作者源。
- `ExportV83/`：作者中间 FBX，尚未叠加当前待机靠近身体的衔接。
- `Final/Standard/A_RuneSword_Inspect.fbx`、`Final/LongGrip/A_RuneSword_Inspect.fbx`：接入阶段生成的最终完整 FBX，直接重导应使用这里。
- `Final/*/Inspect_idle_handoff_keys.json`：待机衔接编辑键。
- `import_inspect_v83.py`、`BeforeV83/*`、`import_receipt_v83.json`：两目标的接入脚本、原包备份与实际保存回执。

正式引用路径：

- `/Game/Weapons/AzureRunesword20260913/A_RuneSword_Inspect`
- `/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_Inspect`

本次原有编辑器在提交导入前已从外部退出，MCP 未发现节点、没有执行导入；随后改用无界面 commandlet，并沿用同一资产批次互斥完成接入。不打开或重启编辑器界面，不启动游戏。未追加测试、截图或渲染，具体观感由用户试玩确认。
