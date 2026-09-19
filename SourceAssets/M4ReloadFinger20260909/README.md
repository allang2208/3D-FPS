# M4 换弹右手食指自然弯曲 — 2026-09-09

普通换弹与空仓换弹中的右手食指改为放松的弯曲姿态。基于原 M4 Rig V4 的实际握枪姿态，调整 index_01_r、index_02_r、index_03_r 的局部旋转；保持手掌、其他手指、枪械和弹匣运动。

## 动作处理

- 先读取并渲染原 Idle 与 Reload，确认 Reload 中段食指第二、第三节接近伸直。
- 使用 Idle 的根指节方向作为参考，中节和末节形成自然弧度。原片段首尾姿态保留，前 12 帧、末 18 帧平滑进入/退出弯曲中段。
- 保留 189 帧、60 Hz、3.133333 秒源动画长度；运行时普通/空仓换弹时长沿用角色原逻辑。
- 未修改开火、Idle、ADS、装备动画，也未修改网格或骨架。

## 文件与接入

- `M4_Reload_FingerCurl.blend`：可编辑动作源，包含原动作与 M4_reload_FingerCurl / M4_reload_empty_FingerCurl。
- `build_finger.py`：从 M4 Rig V4 源文件生成两个新 FBX。
- `import_validate.py`：导入并校验 `/Game/Weapons/M4InfimaRigV4/ReloadFinger/A_AKM_reload` 和 `A_AKM_reload_empty`，复用原 Skeleton 与专用压缩设置。
- `FPSGAMECharacter.cpp::LoadAKMAnimation` 只将 M4 的两个换弹引用切到 ReloadFinger 子目录。
- 原动画保留；源码前置快照位于 `trash/M4ReloadFinger-before-20260909`。回退仅恢复 LoadAKMAnimation 中的换弹目录选择，不整文件覆盖其他任务的改动。

## 验证结果

- Blender 两个片段全部 189 帧回读：未修改骨骼的局部矩阵误差 0，首末帧矩阵最大误差约 5.96e-8。
- UE 两个片段各 377 个时刻、120 Hz 回读：已检查的手腕、左手、机匣、扳机、弹匣位置与旋转未改变；新片段最大压缩位置误差 0.00733 cm（约 0.0733 mm）。
- UE 编译：`build_cpp_final.log`，Succeeded。
- D3D12 实机：`Saved/GunplayUpgrade/m4-finger-final60/result.json`，44 项通过、0 失败、进程退出 0。日志明确记录两个 ReloadFinger 资源已加载。
- 1,792 次游戏姿态采样通过刚性部件稳定性检查；已检查普通/空仓换弹截图与修复前后食指近景。
- 10 Hz 实机视频保存在 `Saved/GunplayUpgrade/m4-finger-final60/Preview/gunplay_preview.mp4`，视频不作为 FPS 基准。
- 导入命令行仍有项目原有 GameFeatureData 警告/错误，导入完成依据为专属 PASS 标记、姿态回读和后续实机加载；没有将该命令行退出码当成干净通过。

`finger_comparison.png` 是实际 Blender 蒙皮模型的同角度近景对比；实机截图位于上述 Saved 目录。

保存当前编辑器工作后重启项目，以加载新源码与动画引用。
