# Inspect Reverse V85 / R6

BV1hCJFzQEyR `#10 绕手`（文件 76.000–76.300 s）逐帧倒放成逆时针起手，再与 V82 的掌心托剑拼成完整转刀（R6）。正式版为 R6b：按 V82 的时间表播放，L 键检视。说明见 [V85 制作记录](../../../Docs/Weapons/runesword-inspect-v85-20261031.md)。

## 作者入口

- `author_inspect_r6.py`：**正式版作者入口**（R6/R6b 拼接版）。
  `blender -b --factory-startup --python author_inspect_r6.py -- [--long-grip] [--no-export] [--diag]`
- `author_inspect_v85.py`：R5 单版作者入口（V85 手势全程，放慢 20%），保留供回查。
- `extract_v82_poses.py`：把 V82 作者 Blend 烘焙成逐帧骨骼矩阵 `Work/v82_poses_<variant>.npz`，R6 拼接时按剑转角对齐取样；换了 V82 源或骨架后先重跑它。
- `keys_v85.json`：R5 的九个关键帧 N0–N8（参考 f2288→f2280 倒放），R6 的起手与收尾手势仍取自这里；改手势、衔接改这个文件。
- `v85_keys.py`（关键帧插值、转角时钟、通道柔化）、`v85_solve.py`（逐帧求解）、`v85_frame.py`、`v85_arm.py`、`v85_hand.py`、`v85_setup.py`：R6 复用同一套求解器；手臂摆角、上臂滚转、腕部裁量、清隙搜索均带逐帧限速。
- `fit_v82_keys.py`：把 V82 掌形量成 V85 关键帧通道的测量脚本（R6 设计参考，未直接参与烘焙）。

## 制作与接入

- `ExportV85/`：作者 FBX（当前为 R6b）；`Final/<variant>/`：接入时生成的完整 FBX，含首尾待机衔接。
- `BeforeV85/`：V85 接入前的 V82 正式包，逐字节原始备份。
- `import_inspect_v85.py`、`run_import.ps1`：只替换两套 Inspect，带并行修改散列保护。
- `import_receipt_v85.json`：当前正式保存回执。
- **长柄档案**：长柄播放普通柄 Inspect 加 `DA_Sword_LongGrip` 的稀疏左臂差值。重导 Inspect 后必须用 `bake_clip(普通柄, 长柄)` 重烘该条目，否则长柄会用旧时间轴的左臂修正。做法见 `Docs/Weapons/runesword-inspect-v85-20261031.md` 的 R5/R6 段。

## 检查（作者源，不是游戏验收）

- `motion_profile.py <blend|fbx> <out.json>` + `plot_profiles.py <out.png> 标签=json …`：剑身画面转速与手速的逐帧曲线，节奏是否停顿/倒转先看这个。
- `smoothness.py <blend> <out.json>`：逐帧单帧跳变检测。
- `preview.sh <tag>`（R5 单版）、`render_review.py`、`sheet.py`、`compare_v85.py`：作者相机预览、拼图与参考对照。
- `Work/` 是迭代预览与日志，不入库；`Work/v82_poses_*.npz` 是 R6 的必需输入，可由 `extract_v82_poses.py` 重新生成。
- `archive_retired.py`：本轮退役文件的归档脚本（已执行），清单在 `trash/runesword-inspect-v85-20261102/archive-manifest.json`。

## 回退

用 `BeforeV85/<variant>/A_RuneSword_Inspect.uasset` 覆盖对应正式包（编辑器关闭时），并重烘长柄档案条目。
