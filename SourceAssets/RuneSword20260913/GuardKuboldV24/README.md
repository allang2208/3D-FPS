# 双手剑格挡 V24：Kubold 参考 1:49–1:52

用户 2026-11-22 要求按 YouTube `NTrzxPIXer4`（Kubold FPP Melee Animset · Two Handed Sword）1:49–1:52 做新的双手剑格挡，力求还原。替换 V23（张掌推剑，`SwordGuardPalmPush20260926`）的 Guard / GuardHit / GuardBreak，普通柄与长柄各三段。

## 参考取样

- 录像：`F:/FPSGAMEData/ArtProduction/SourceAssets/Weapons/RuneSword20260913/Reference/KuboldTwoHandedNTrzxPIXer4/ref_1080p60.mp4`（1080p60，SHA-256 `8912493d…`，与击倒任务 `Saved/Reference/KnockdownNTrzxPIXer420261114/` 为同一文件）。
- 文件时间：用户的 1:49–1:52 对应格挡举起 110.94–111.40 s 与持守 111.40–113.5 s；同一段落里的受击取 117.64–118.39 s，破防取 119.70–120.15 s（参考没有真正的破防，取被打低的那一下，之后保持低位）。
- `Reference/frames/fNNNNN.jpg`：拆帧，编号 = 秒 × 60。`measure_blade.py` 用霍夫成对边线量剑身角度和宽度（`blade_track.json`），`track_hook.py` 用护手钩模板量持守期的上下起伏（`hold10/hook_track.json`，10 fps），`grid_sheet.py` 出带坐标网格的读数图。
- 持守读数：剑根 (595, 998) px，剑身 42.1°，护手 82°；剑根旁剑宽 84 px，沿剑 800 px 处约 60 px。呼吸周期 2.05 s，钩点上下 40 px、左右 5 px。
- 受击剑宽：117.80 s 剑根旁约 115 px，118.00 s 约 105 px（`Work/width_probe.png`），即剑离镜头约为持守的 0.74–0.78 倍。

## 做法（`author_guard_v24.py`，Blender 5.1 后台）

- 镜头与游戏一致：视模型原点、看 +Y、垂直 FOV 75°、16:9。按参考像素反求剑根射线，剑身沿参考屏幕角，护手对准参考屏幕角。
- 深度取右臂还能保持弯肘（伸展 ≤ 0.93）的最深处：持守 0.28 m。两手保持认可的 WristLocked V4 待机握法，拳绕握把滑转以减小腕折；手臂用 V85 解算器和 V9 前臂扭转。
- 举起 0.46 s：剑身转角和剑根位置的进度曲线取自参考（横向先到，纵向后到，转角过冲 9% 再回）。之后一整个呼吸周期 2.05 s，运行时循环。
- 受击 0.75 s、破防 0.45 s：参考关键帧给出剑根屏幕点、剑身角和深度比，PCHIP 插值剑根路径、深度和相对持守的转动。破防首帧护手沿用持守方向（`guard: carry`），不再重新对准 82°。
- 运行时（`Source/FPSGAME/Weapons/RuneSwordGuard.cpp`、`RuneSwordGuardTuning.h`）：Guard 片段举起后在 [片段长 − 2.05 s, 片段长) 循环；受击结束回到持守起点 0.46 s；收起仍用 0.18 s（从持守起点倒放），呼吸中松开或受击中松开先用 0.12 s 混合到持守起点，受击不再推迟反击；剑的持守镜头静态偏移归零（参考镜头不动），保留受击冲击；破防眩晕结束后 0.32 s 回待机。格挡、弹反、耐力、联机与第三人称计时不变。

## 迭代（定稿 r9 在 `Work/`；r1–r8 已归档）

| 轮 | 改动 | 结论 |
| --- | --- | --- |
| r1–r3 | 求解深度、剑尖出画、预览动作重名修正 | 剑尖露在画面里；同名旧动作被渲染 |
| r4 | 护手正对镜头 | 剑面宽 2.6 倍，护手占满画面 |
| r5 | 刃口朝向镜头（edge-on） | 剑看起来和参考一样细，但举起时 36 cm 护手扫进镜头，左手绕柄 156°，弃用 |
| r6 | 回到护手 82° | 持守贴合；受击剑贴脸（深度比 0.58） |
| r7 | 受击深度比按剑宽重估为 0.74–0.98；拳的滑转每键限 ±48° | 受击手和剑位置接近参考 |
| r8 | 破防首键指定左拳转角 | 无改善，撤回 |
| r9 | 破防首键护手沿用持守方向 | 护手竖起、钩尖露在底边，与参考一致，定稿 |

## 与参考的差别

- 剑型不同：参考是细长剑，我们的符文剑剑面 7–10 cm、护手 36 cm。剑放在参考的同一屏幕位置，剑根旁宽 171 px（参考 85 px）。再往远放右臂会伸直。
- 破防：参考是被打低后马上恢复；我们保持低位直到眩晕结束（1.5 s），之后 0.32 s 回待机。
- 破防 0.05–0.15 s 左前臂扭转从 +5° 到 −95° 再到 +90°，左腕最大 92°，这段左手在画面下沿之外。
- 受击 0.75 s 只有按住格挡时完整播放；第三人称身体仍用原来的格挡动作和 0.20 s 举起。

## 文件

- `keys_guard_v24.json`：所有参考读数与键位；`author_guard_v24.py [--long-grip] [--no-export]`；`authoring_v24[_long_grip].json`：逐帧伸展、腕折、扭转、剑根像素和深度。
- `Export/`、`Export/LongGrip/`：作者 FBX（120 Hz：Guard 301 帧间隔 2.508 s，GuardHit 0.75 s，GuardBreak 0.45 s）。
- `preview_v24.py`、`compare_v24.py`、`Work/run_round.sh <tag>`：游戏镜头预览与参考对比（预览 blend 由作者脚本 `--no-export` 重新生成）。`Work/` 只留 r9 定稿图和被键位引用的两张图。
- 安装：`run_import.ps1` → `import_guard_v24.py`。Guard 只在起手接回各目录现装待机（0.20 s 内淡出），受击、破防不改；`DA_Sword_LongGrip` 已有的对应条目按新资产重烘。改前备份、最终 FBX、起手接回键与回执在 `F:/FPSGAMEData/ArtProduction/RuneSword20260913/GuardKuboldV24/Install-20261122/`。
- 审查图：`F:/FPSGAMEData/ArtReviews/RuneSword20260913/GuardKuboldV24/20261122-r9/`。

## 接入状态

**正式版**：用户 2026-11-22 认可「合格」，作为双手剑正式格挡替换 V23。2026-11-22 21:32 后台导入保存 6 段动画，长柄档案三个条目重烘。散列、时长和起手接回细节见 [说明文档](../../../Docs/Weapons/runesword-guard-v24-20261122.md#状态) 与 F 盘回执 `import_receipt.json`。迭代中间输出已归档到 `trash/runesword-guard-v24-20261122/`，清单在 F 盘批次 `Cleanup-20261122/`；`archive_work.py` 为归档脚本。
