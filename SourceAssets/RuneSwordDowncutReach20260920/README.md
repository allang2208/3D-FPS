# 冲刺下砍中段伸展 V5 · 2026-09-20

用户提供实机截图，要求排查下砍中段接近直角的双肘，并优化为自然伸展。此次只替换普通柄、长柄的 `A_RuneSword_Overhead`；其他动作继续使用原来的腕部 V4。

## 原因

当前安装版本确认为 `WristLockedV4`。它修正近肘轴向支撑，但刻意保留了 ImpactV2 的肩、肘、腕位置，因此也保留了下砍轨迹中的收臂。

读取实际安装轨道发现，举顶和落点虽较直，约 1.24–1.28 秒的双手经过肩高阶段仍离身体太近：普通柄双肘最小内角为左 101.60°、右 112.19°；长柄为左 100.05°、右 114.62°。参考矿镐的下砸贝塞尔控制点前伸不足，旧 `fit_group` 只处理超出最大臂展，没有处理下砍途中臂展不足。当前运行代码没有在此动作上再次添加双臂 IK。

## 制作

- 基于当前实际 V4 的逐帧姿态修正，不回用用户否定的 V3 下沉肘位。
- 剑、双手和手指作为持握整体向前展开；最大位移普通柄 11.83 cm、长柄 11.68 cm。保留手腕世界朝向、掌指相对剑的姿态与握距。
- 目标肘内角 160°，即保留约 20° 的软屈曲。1.02–1.11 秒平滑进入，完整保持至 1.50 秒，之后至 1.95 秒平滑退出；不是只修正最弯的一帧。
- 根据两手在柄上的不同深度分别支撑肩位，最大肩随动普通柄 1.99 cm、长柄 2.65 cm。用原肘弯曲平面重新解两段臂长，整段搬运上臂和前臂辅助骨，不拉长骨骼或重置前臂轴向滚转。
- 因伸展需要改变前臂方向，V5 保留的是手腕朝向和握姿，不声称同时锁定 V4 的前臂接入方向。
- 保留 2.60 秒、120 Hz、1.22–1.40 秒命中窗，以及竖直扰动、镜头、挥动音、落点停顿与战斗数值。没有 C++ 改动，不需要原生编译。

## 文件与接入

- `Standard_input.json` / `LongGrip_input.json`：编辑器读取的修改前完整姿态与目标 SHA256。
- `reach_solver.py` / `author_downcut.py`：持握整体前送、双臂等长求解、17 条父子补偿轨道。
- `Standard/`、`LongGrip/`：可编辑 Blend、局部轨道 JSON、从已接入资产导出的完整 FBX。
- `apply_downcut.py` / `import_receipt.json`：两条实际运行资产均已在当前编辑器保存。修改前检查目标散列和未保存状态；旧 V4 包留在 `Before/`。
- 修改目标为 `/Game/Weapons/AzureRunesword20260913/A_RuneSword_Overhead` 及 `/Game/Weapons/FrostCrystalSword20260915/Grips20260919/LongGripAnimations/A_RuneSword_Overhead`。

首次导入因 PIE 正在运行而未写入；仅结束该次试玩后完成两条动画保存，编辑器保持打开。

## 本次排查范围

根据本轮明确的排查要求，读取了两支动画全部 313 个采样点的源与压缩骨姿态，并在同一模型上绘制下砍关键帧，未启动新的 PIE 或全套玩法回归。

`installed_downcut_diagnosis.json`：已保存压缩姿态在 1.11–1.50 秒双肘最小内角约 160°；手与全部手指的剑局部位置误差小于 0.000624 cm，手腕世界朝向误差小于 0.000638°，骨长误差小于 0.000285 cm。该数值是姿态读取结果，不代表实机自然程度或手感验收。

`before_fp_fold.png` / `after_fp_fold.png` 为 1.2667 秒同机位模型对照，`after_side_fold.png` 为侧面诊断。读图定性结果记录于 `after-fold-vision.txt`：未见明显直角折叠、脱手或皮肤破洞。实机效果由用户试玩确认。

整理记录：本文的 `Before/` 旧覆盖快照已移至 `trash/dual-melee-overhead-retired-20260920/SourceAssets/RuneSwordDowncutReach20260920/Before/`；恢复以 `Docs/Rejected/dual-melee-overhead-retired-20260920.json` 为准。保留源与最新安装顺序见 `Docs/Weapons/dual-melee-overhead-publication-20260920.md`。历史回执不改写为本次测试结果。
