# M870 装填：重新采用原始 Blend 右手动作

用户再次否定 `M870ReloadWrist20261016` 的右手处理。本批从原始参考重新采样，普通、空仓两条装填已制作、导出，并在用户退出游戏后通过后台 commandlet 导入和保存。实际保存状态见本目录 `install_receipt.json`（`completed=true`，两条动画）。

## 后续持枪修订

用户另行指出起止持枪时食指未触及扳机。后续 `../M870TriggerGrip20261016/` 采用同一原始 M870 的 Idle 握姿，保留本目录的活动取弹／推弹轨道，只衔接新的离枪／回握姿态。后续持枪与左肘／腕部修订已随 `../M870LeftArm20261016/` 组合批次保存，本目录的活动取弹／推弹段作为输入保留。完整重制链最后执行组合修订层。

## 参考与修订

参考源为 `../M870UrbanAnimations20261015/Original/870/Renmington 870 unfucked.blend`，使用原始 `gmod_arms` 求值后的 `reloadstart`、`reloadinsert`、`reloadend`、`reloadendCycle`。`reference_poses.json` 保留原始骨骼采样，`reference_surfaces.json` 保留参考表面；原 Blend 未改写。来源与本地使用记录沿用该目录的 `CREDITS.md`。

旧接触层固定了某一帧持弹手型，上一腕臂层还另作了松指和回收轨迹，未保留原动作的手指变化。本批直接使用原始 Blend 中每个阶段的手指旋转、臂段方向及 Forearm／Ulna／Wrist 辅助骨参考。原 SMD 导出与原 Blend 的绑定及求值姿态有差异，本批右手不再从该 SMD 取得姿态。

- 用固定的逐骨解剖轴映射适配 Valve 与 V7 的不同参考姿态，保持目标原生骨长和手指根部位置。手指随原取弹、推弹、释放动作变化。
- 按原辅助骨分配前臂轴向旋转；将目标各辅助站的形变轴保持在实际前臂轴线上，避免把肘部摆动带入中段造成鼓包。
- 接触微调仅调整整手刚体变换；五个持弹校准点连续插值，不逐关节追着弹壳扭转。原帧中拇指离开弹壳的阶段予以保留。
- 原释放路径保留，以原手部行程重新分配其 16 帧采样，改善旧时钟压缩在最后几帧的突跳；未新造回收路径。尾段按源动作的取弹姿态衔接原枪托握点。
- 输入为 SUPER90 冲刺版；保留已获指定的 AKM 左手、枪和弹药轨迹、七次入弹点、闭锁和库存时钟、三条冲刺及通用瞄具。

只导出、导入 `A_M870_reload_continuous` 和 `A_M870_reload_full`；60 Hz，分别 400／425 个姿态，时长 6.65／7.066667 秒。未改共享裸手网格、蒙皮、骨架、C++ 或其他动画。

## 本次排查记录

按用户要求对照原始参考，并查看原生 V7 表面的离线近景。`reference_insert_*.png` 是原参考；`candidate_reload_*.png` 是适配到游戏原生网格的制作源预览，简化材质、非游戏截图。关键帧表面距离记录在 `candidate_contact.json`，仅是局部接触参考，不是全帧无穿模证明。

`source_review.json` 覆盖 825 个源姿态：左臂／枪／弹药等保护轨道最大矩阵误差约 0.000001，原生段长误差小于 0.001 mm，起止握姿保留。源表面与动作仍需用户在游戏中确认，不能用这些数值代替自然度验收。

首次保存请求因 PIE 运行而延期；用户退出游戏后，已执行后台导入并保存普通／空仓两条动画，进程退出码 0。原包已备份至 `Before/Animations`。保存后另一次后台读回确认两条动画的 `M870ReloadSource20261016` 版本标记、FBX SHA-256 和时长均对应当前导出，见 `saved_animations.json`。未主动启动或停止图形编辑器，未运行游戏、声音或联机测试；没有另行编译需求。

## 制作与保存

- 可编辑源：`M870_ReloadSource_Editable.blend`。
- 制作参数：`author_source_reload.py`、`contact_curve.json`、`reference_poses.json`。
- `rebuild.ps1` 制作并导入；已导出后可直接执行 `install.ps1`，不必重算。
- 全套入口仍为 `../M870AKMArmSupport20261016/rebuild.ps1`，顺序：基础 → 接触输入 → SUPER90 冲刺 → 本原始参考修订。
- `install.ps1` 沿用现有 MCP 批次互斥；已有编辑器播放或目标资产未保存时延期。成功时原包备份至 `Before/Animations`，真实保存记入 `install_receipt.json`。
- `read_saved.ps1` 仅用于本次必要的保存版本读回；拟合、诊断、渲染脚本不随默认重制执行。
