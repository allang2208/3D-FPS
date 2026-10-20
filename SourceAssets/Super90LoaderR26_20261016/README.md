# Super90LoaderR26_20261016

推进时钟 R26 与左手推进解焊／甩开去僵。说明、数值与恢复边界见 `Docs/Weapons/super90-speedloader-r26-push-flick-20261016.md`。

执行顺序（均为后台；不启动游戏、不渲染、不测试）：

1. `run_ue.ps1 -ScriptName read_inputs.py`：读取已安装的 normal/empty 1–7 与四份握把 Profile → `inputs.json`。
2. `python author_timing.py`：写 `Source/FPSGAME/Weapons/Super90LoaderPushTiming.h` 与 `timing.json`（原头文件备份在 `Before/Source/`）。
3. `python author_r26.py`：生成 `animation_patch.json`、`authoring.json`（左臂链与左手手指；`r26_core.py`、`r26_timing.py` 为共用模块）。
4. `python check_patch.py`：作者侧数据一致性（`patch_check.json`）。`measure.py`、`analyze.py`、`preview.py` 只做量测。
5. `run_ue.ps1 -ScriptName save_assets.py`：保存 14 段动画与四份 Profile，覆盖前的包放到 `Before/Content/`，回执 `save_receipt.json`。
6. Blender 5.1：`blender -b --factory-startup --python save_editable.py` → `Super90_Loader_R26_Editable.blend`。
7. `build_native.ps1 -Targets FPSGAME[,FPSGAMEEditor]`：常规构建，回执 `native-build-receipt.json`。

不要在新的已安装资产上重跑第 3、5 步：`save_assets.py` 会先核对包散列与 `inputs.json` 是否一致，不一致就拒绝写入。

## R26b（已导入，2026-10-16）

R26a 已在 15:50 保存，但回握／撤手大摆提前，跑到脱离原声前面。R26b 只重定时源帧 115–123，数据已生成：`animation_patch.json`，R26a 版本保存在 `*_r26a.json`。`sync_check.py` 用于核对原声对齐，`screen.py` 估算画面可见性。

导入：编辑器空闲、没有 PIE 时运行 `run_ue.ps1 -ScriptName save_assets.py`，再运行 `-ScriptName read_saved.py` 读回核对。保存只接受 R26 前安装版或 R26a（`r26a_saved_sha.json`）两种状态。`run_when_idle.ps1`、`run_after_pie.ps1` 可以自动等待空闲后导入，本次按用户要求没有挂起。
