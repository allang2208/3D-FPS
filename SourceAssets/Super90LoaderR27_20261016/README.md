# Super90LoaderR27_20261016

R25 的对准段原样保留，推入段重做为单调加速；R26b 左手层按新时钟重新采样。说明见 `Docs/Weapons/super90-speedloader-r27-align-drive-20261016.md`。

1. `python compare_timing.py`：R25／R26／R27 的时钟斜率与推杆感知速度对比 → `timing_comparison.json`。
2. `python author_timing.py`：写 `Super90LoaderPushTiming.h` 与 `timing.json`；原头文件备份在 `Before/Source/`。
3. `python author_r27.py`：调用 `../Super90LoaderR26_20261016/author_r26.py`，底稿为 R26 的 `inputs.json`（R26 前安装版）→ `animation_patch.json`、`authoring.json`。
4. `run_ue.ps1 -ScriptName save_assets.py`：只覆盖 `r26b_saved_sha.json` 记录的 R26b 包；覆盖前的包在 `Before/Content/`，回执 `save_receipt.json`。`run_after_pie.ps1` 和 `run_when_idle.ps1` 会等 PIE、构建或批次门空闲后再写，期间不改资产。
5. `run_ue.ps1 -ScriptName read_saved.py`：读回核对 → `saved_readback.json`。
6. `build_native.ps1 -Targets FPSGAME[,FPSGAMEEditor]`。

不运行游戏、不渲染、不测试。
