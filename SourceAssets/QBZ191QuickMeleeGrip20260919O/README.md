# QBZ191 快速近战 O：后握把接触修复

> 收尾（2026-09-19）：用户在后续 recover 修正后确认成功结束。以下为制作时记录；最新版本、有效依赖与归档位置见 [发布与恢复](../../Docs/Weapons/quick-melee-publication-20260919.md)。


用户反馈快速近战中右手与后握把不匹配，要求排查并修复。本次覆盖 Base、Angled、Vertical、Canted、Prism；运行时弹鼓继续使用 Base。

## 原因

上一版 `RifleQuickMelee20260919/author_rifles.py` 将 M4 N 的握把转轴表达在手掌空间后迁移到 QBZ191，再执行整手换向。虽然手指局部姿态保持，但手掌相对枪根发生大幅旋转和平移。Base 源动作第 12 帧偏移 9.97 cm / 78.44°，接触帧 20 偏移 9.18 cm / 71.25°，因此整组手指会偏离后握把并穿入枪体。

直接取消整手换向且保留原持枪方向、肩位时，接触帧最小可达腕轴折角仍为 91.61°。因此不能只把手平移回去而保留全部旧约束。

## 修复

- 以每个分支自身的已接入待机为后握把基准，锁住 `WPN_root^-1 * hand_r` 以及五指局部姿态；左手也维持自身配件抓握。
- 共同调整整枪与双手的挥击方向、位置，重建肩肘和前臂扭转分布，保留骨段长度与后方肩位。
- 枪械中段更接近横向持握。此修复改变了中段持枪角度与枪托路径；不是仅移动右手。枪托命中探针已经随枪根运动，无需更改其本地点。
- 维持 0.9 s 总时长、1/6 s 命中时刻及原待机起止；不改变玩法时钟。
- 120 Hz 求运动调整，连续平滑后按 480 Hz 重建和导出整条骨链，减少高速插值造成的握点漂移。FBX/UE 的导入采样同为 480 Hz。

## 文件和接入

- `author.py` / `grip_solver.py`：本版作者入口；依赖前版保留的 Blend、K 的 `arm_support.py` 与 N 的 `natural_wrist.py`。本版覆盖 `target()` 固定手掌，不再绕握把单独旋手。
- 五个分支目录：可编辑 Blend 与 `Animations/*.fbx`。
- `authoring.json`：作者参数、动作路径、腕部指标及相对旧版的枪托轨迹变化。
- `import_assets.py` / `import.json`：覆盖保存现有 QBZ191 五个运行资产，路径保持 `/Game/Weapons/RifleQuickMelee20260919/QBZ191/<Profile>/A_QBZ191_QuickCombat_<Profile>`。
- 替换前五条 `.uasset` 已归档到项目 `trash/quick-melee-retired-20260919/SourceAssets/QBZ191QuickMeleeGrip20260919O/Before/`；探索用 `probe_bearing.py` 及其输出也在此归档。旧 N 源仍作为本版制作输入保留；本版不覆盖 M4/AKM/ASH-12。

本次纯动画资产修改，不需要 C++ 构建。首次编辑器内保存被正在进行的游戏预览阻止；编辑器随后退出，改用既有最小导入宿主完成五条资产保存。

## 本次明确要求的排查

- `diagnose.py` / `diagnosis.json`：旧版握点偏移与固定原握姿的腕轴可达性。
- `check_source.py` / `source_checks.json`：每分支 865 个采样，含 480 Hz 关键帧间点。源握点漂移最大约 0.114 mm；五指局部矩阵误差小于 0.000001；骨段长度误差小于 0.001 mm。
- 原本完全由右掌/手指骨驱动的 5570 个手部顶点，相对握把的采样漂移最大约 0.123 mm。该指标证明动作中保持原抓握形状，不代表所有改造后握把均重新做过全表面相交检测。
- `render_review.py` / `Review/*_comparison.jpg`：基础分支第 0、12、20、60 帧的近景和第一人称源模型对比。左 N、右 O；不是游戏截图。
- `readback_ue.py` / `ue_readback.json`：同求值模式下对照当前待机和新动作。RAW 关闭额外 retarget，COMPRESSED 开启运行时 retarget；此私有武器骨架两种路径的枪根空间不同，不能混用基准。COMPRESSED 运行姿态的握点漂移最大约 0.110 mm，方向漂移约 0.020°；五指局部位置保持、旋转差约 0.000003°。
- 本次没有启动 PIE，也没有进行游戏输入与手感验收，最终手感由用户试用。
