# M4 腰射构图调整 — 2026-09-09

依据 Godot 当前 `weapon_data/infima_ar.tres`、`scripts/gun.gd`、实际 Gun/Infima 模型渲染和 UE M4 实机画面调整。Godot 文件只读，运行使用独立 INVENTORY_SAVE_PATH / GAME_SETTINGS_PATH。

## 结果

- 两边垂直 FOV 均为 75°。保持世界相机视野和瞄准校准，以持枪相对位置匹配原版的构图。
- M4 腰射相对位置从 UE `(10, 0, -5)` cm 改为 `(0, 7, -7)` cm：向镜头靠近 10 cm、向右 7 cm、向下 2 cm。枪托移出主要画面，突出机匣、护木和左手。
- 装备/换弹保留原来的 `(10, 0, -5)` cm 空间，通过指数平滑过渡，避免直接使用近距离腰射位置裁掉双手、弹匣。
- ADS 使用原有独立瞄具校准位置；骨架、网格、动画、弹道及 FOV 未修改。
- 可调属性：`M4HipViewmodelLocation`、`M4ActionViewmodelLocation`。改动仅位于 `FPSGAMECharacter.h/.cpp` 的 M4 构图分支；其他任务的角色/背包接入保留。

## 对比与量化依据

`hip_framing_comparison.png`：Godot 原版、UE 修改前、UE 修改后。画面来自两引擎实际渲染，Godot 与 UE 的武器/材质不同，对比目标是构图。

Godot 默认 Infima AR 的实际 Gun 位置约 `(0.12, -0.027753, -0.10)` m（含轻微待机起伏），16:9，垂直 FOV 75°。实测屏幕归一化位置：

| 标记 | Godot 原版 | UE 修改前估算 | UE 修改后估算 |
| --- | --- | --- | --- |
| 前准星 | (0.588, 0.547) | (0.529, 0.518) | (0.586, 0.548) |
| 照门 | (0.748, 0.632) | (0.561, 0.537) | (0.738, 0.630) |

UE 表中数值由上轮已读取的 V4 Idle 第 0 帧组件空间姿态投影计算，不包含每帧待机起伏；实际画面用于最终核对。没有把 Godot 序列化偏移不加适配地直接复制到不同枪模。

## 验证

- `build_final.log`：UE Editor 编译成功。并行任务也在生成模块，实际启动加载模块以运行日志为准。
- `godot_reference.log/json`：Godot 当前默认步枪的渲染、相机和骨骼投影回读，`GODOT_HIP_REFERENCE_PASS`。
- `Saved/GunplayUpgrade/m4-hip-final60`：D3D12 实机完整动作序列、截图、39 项通过、5 项失败。
- 通过项包括两瞄具中心对齐、开火、冲刺/滑铲/跳跃与换弹共存、恢复，以及 1,792 次骨架刚性部件稳定性采样。
- 5 项失败均为弹药测试合同：normal_reload_settlement、reload_settles_once、empty_reload_in_progress、insufficient_reserve_conserved、held_trigger_resumes_after_empty_reload。当前 `FinishReload()` 调用背包 Profile->ConsumeAmmo；旧审计仍直接写角色 MagazineAmmo/ReserveAmmo。例如审计期望剩余 5 发，但真实独立背包的 90 发经换弹剩余 75 发。该回归套件尚未适配新的背包数据来源，不能宣称完整回归通过。此任务没有修改背包或弹药逻辑。
- 实际审查了最终腰射、ADS、换弹中段和恢复姿态。视频捕获为 10 Hz，不能作为实际 FPS 基准。

实机视频：`Saved/GunplayUpgrade/m4-hip-final60/Preview/gunplay_preview.mp4`。

## 使用与回退

保存当前编辑器工作，重启项目后加载新构图。无需重新导入模型。

修复前快照在 `trash/M4HipFraming-before-20260909`。回退只逆向恢复本次构图属性与 UpdateViewmodel 的相关行；不要整文件覆盖并行任务的新改动。Godot 参考中第二把 HK416 的早期截图不是本次校准依据，最终脚本和 JSON 只保留默认 Infima AR 的有效测量。
