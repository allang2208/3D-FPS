# Super90 待机左手对齐移动持枪（2026-10-08）

用户认可移动状态的左手持枪，要求仅调整待机。快速装填重做仍暂停。

- 读取实际安装的 `A_Super90_walk` 压缩姿势作为移动持枪来源；沿 `clavicle_l` 子树迁移 26 根骨骼，包含肘腕、辅助／扭转骨和全部手指。
- 以 `WPN_root` 为参照，把左臂的持枪关系带入原待机的 180 个采样点，保留原待机时长、枪械机械骨与右臂。
- 四个前握把 profile 的待机条目采用各自现有 walk 姿势；其他条目与 retained 引用保留。vertical 配置继续涵盖 tactical_vertical。
- 未采用快速装填暂停现场中的拟合候选。未修改移动、ADS、战术冲刺、换弹或镜头 C++。

## 制作与保存

`read_inputs.py` → `inputs.json` 保存制作输入；`prepare_idle.py` → `idle_patch.json` 生成左臂关键帧和握把差量；`apply_idle.py` 写入并保存一个 idle 动画和四个 profile。

当前：五项资产已通过无界面 Python commandlet 实际保存，记录为 `save_receipt.json`（`completed: true`）；保存输出为 `save_commandlet_console.log`。最初的桥接写入因 PIE 未停止而被拦下，没有修改资产；用户随后关闭编辑器，最终改为后台保存。保存完成不代表运行测试通过。

编辑器运行时通过 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript` 的批次互斥执行。只结束必要的 PIE，不启动、关闭或重启编辑器。本次保存已完成，未重开编辑器。

未启动游戏、截图、离线渲染或运行测试；由用户体验待机／移动衔接。将来若恢复快速装填制作，不要用旧作者脚本覆盖本次独立修正的 idle；恢复入口和授权边界仍见 `Docs/Weapons/super90-speedloader-paused-20261008.md`。
