# CompactRecoveryV8 — 缩短定剑与连贯回握

2026-09-14，按用户要求保留 V7 蓄势动作和抬剑速度，将到位后停顿由 0.500 s 改为 0.200 s；随后直接进入原有 0.115 s 快速斜劈。两段攻击共用此节奏。

## 基础攻速时间

| 阶段 | V8 时间 | 调整 |
| --- | --- | --- |
| 抬剑蓄势 | 0–0.650 s | 沿用 V7 完整源时间曲线，动作和速度不变 |
| 到位定剑 | 0.650–0.850 s | 停顿 0.200 s 后直接释放 |
| 快速斜劈 | 0.850–0.965 s | 保留既有剑路和 0.115 s 快斩速度 |
| 顺势卸力 | 0.965–1.115 s | 0.150 s 逐渐制动，保留过刃方向 |
| 停重 | 1.115–1.140 s | 由 60 ms 缩至 25 ms，更快接上回握 |
| 侧向拖回 | 1.140–1.440 s | 0.300 s，前段更早发力，不长时间悬停 |
| 回握落稳 | 1.440–1.775 s | 0.335 s，末段减速回到原待机姿态 |

收势总长由 0.985 s 调为 0.810 s。完整攻击总长 1.775 s，接触窗 0.850–0.965 s；继续按攻击开始时的既有攻速快照缩放，与音效、剑气和扫掠伤害使用同一时钟。

镜头在符文剑反馈输出处统一乘 1.5：前后、横向、竖向位移，以及俯仰、偏航、侧倾和命中冲击幅度均提高 50%。其他武器与移动镜头参数保持现有配置。

## 制作与接入

- `rhythm_clock.py` 定义源时间映射；`write_timing_header.py` 将相同映射写入 `Source/FPSGAME/Weapons/RuneSwordRhythm.h`。
- `retime_animations.py` 继续从 V6 已接受的完整骨骼姿态采样，沿用 V7 的抬剑时间曲线，只压缩定剑和调整回握节奏；不重新解算手腕或肘部。
- `AzureRunesword_Manny_Editable.blend` 为 V8 可编辑源，`Export/` 为两段 240 Hz 挥砍 FBX，源中保留 V6 参考动作。
- `import_revision.py` / `run_import.ps1` 更新原游戏路径 `/Game/Weapons/AzureRunesword20260913/A_RuneSword_Slash1` 和 `A_RuneSword_Slash2`，导入前将旧资源保存到 `Before/`。
- `build_install.ps1` 完成必要 Editor 构建，并保留 `NativeBuildSnapshot/`。
- `Before/Source/` 保留本次修改前的组件与时间映射头文件。

原模型、材质、待机剑面和握姿沿用现有版本。物品定义的攻击时长和命中窗同步更新，既有存档继续使用同一路径资源。

按用户全局规则，未运行游戏、自动测试、截图或验收渲染；由用户重新打开工程后自行测试节奏和镜头强度。制作、导入、构建结果以本目录日志记录。

## 制作与构建记录

Blender 已导出两段 FBX 并保存可编辑源，`author.log` 中记录 `RUNESWORD_V8_AUTHORED`，退出码 0。Editor 必要构建已完成，退出码 0，`build.log` 记录 `Result: Succeeded`；三个相关模块统一使用 `49148` 后缀，输出已保存到 `NativeBuildSnapshot/`，未关闭用户编辑器。

第一次导入遇到动画资源短暂文件占用，自动保存阶段报错，随后显式保存恢复；该次 commandlet 仍以代码 1 退出，日志保留在 `import_first_attempt*.log`。将导入改为设置压缩参数后只保存一次，并要求保存成功后再记录回执；重新导入已完成，最终退出码 0。最终日志为 `import.log`、`import_console.log`，回执为 `import_receipt.json`。
