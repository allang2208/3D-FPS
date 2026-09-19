# V42 · 检视中途左手保持画外

2026-09-15。用户要求检视时另一只手不要进入画面。依据 V41 已有连续画面，删除约 1.7–1.8 秒左手从画面右侧重新伸入的动作。

**已制作、导出并保存到现有 F 键 Inspect。此版未新做播放、渲染或审计，由用户测试。V41 的检查结果不视为 V42 已通过测试。**

## 修改

- 母版为 V41，右臂和剑的动画曲线直接复制，不重新制作转剑方向或腕指配合。
- 使用 V41 在 1.20 秒已有的左臂画外姿态，完整处理锁骨、上臂、前臂、twist 辅助骨和手指。
- 0.85–1.20 秒平滑进入画外保持，1.20–2.35 秒保持该姿态，2.35–2.55 秒平滑交回原收势轨道。移除检视中途的左手伸入及随后收回动作。
- 保留原起势松手、末尾回握和双手待机。完整检视仍为 2.90 秒，120 Hz；右臂的 V41 肩口修正保留。
- 在左臂轨道修改边界统一四元数符号，避免与复制的原轨道插值时绕远路。

## 文件

- `author_offscreen_left.py`：读取 V41 并制作新左臂轨道。
- `AzureRunesword_OffscreenLeftInspectV42.blend`：可编辑源，保留 V41 Action。
- `Export/A_RuneSword_Inspect.fbx`：本版引擎导出。
- `run_import.ps1` / `import_upgrade.py`：导入已有符文剑 Inspect。
- `authoring.json`：修改骨骼与衔接时间。
- `import_receipt.json`：已保存至 `/Game/Weapons/AzureRunesword20260913/A_RuneSword_Inspect`，时长 2.900000095 秒。
- `Before/A_RuneSword_Inspect.uasset`：替换前 V41。

只修改检视动画；网格、材质、原生代码、攻击与其他武器资源保持原有内容。二进制及原始素材留本机，未提交或推送。
