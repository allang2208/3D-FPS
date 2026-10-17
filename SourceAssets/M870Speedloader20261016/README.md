# M870 快速装填（2026-10-16）

记录：`Docs/Weapons/m870-speedloader-20261016.md`。

1. `run_ue.ps1 -ScriptName read_inputs.py`：读取两把枪的骨架、R27 装填片段与 M870 片段，输出 `inputs.json`；读取枪体表面、SUPER90 导向件和道具，输出 `geometry.json`。
2. `analyze.py`、`analyze_port.py`、`analyze_guide.py`、`check_continuity.py`：对照骨架是否一致、装填口位置、机匣底面和端点衔接（只读）。
3. `python author_clips.py`：生成 14 段动作 `clips.json`；`python check_clips.py` 做作者侧检查，结果写入 `clip_checks.json`。
4. `python author_guide.py`：生成导向件 `guide.json`。
5. `blender -b --factory-startup --python author_loader_profiles.py`：生成四类前握把姿态层 `Profiles/*.json`。
6. `run_ue.ps1 -ScriptName install.py`：在 UE 关闭时用后台批处理保存，回执 `install_receipt.json`；编辑器开着时用 `run_bridge.ps1` 走批次互斥。
7. `run_ue.ps1 -ScriptName read_saved.py`：读回核对，结果写入 `saved_readback.json`。
8. `build_native.ps1`：构建 Editor 和 Game，回执 `native-build-receipt.json`。

不运行游戏、不渲染、不测试。
