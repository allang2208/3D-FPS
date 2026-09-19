# M4 快速近战 N：先解决腕部折弯，再分配前臂扭转

> 收尾（2026-09-19）：用户在后续 recover 修正后确认成功结束。以下为制作时记录；最新版本、有效依赖与归档位置见 [发布与恢复](../../Docs/Weapons/quick-melee-publication-20260919.md)。


## 用户反馈与根因

用户反馈 M 右腕仍像直角弯折，明确要求检查并重新理解衔接。M 未被接受。本轮从 K 作者源继续，先检查实际 rest、肩肘腕位置和手掌方向，查看本地参考 `BV13K421e7Rw` 66.30–66.57 s 抽帧与 M 作者源模型。

M 的 Base 接触帧（20 / 120 s），前臂方向与手掌按 rest 推导的自然延伸方向相差约 104.84°。固定肩、手腕位置及手掌方向时，双骨链肘部圆上的理论最小折角仍为 96.65°。因此 M 的 ±10° 肘部绕转及额外 twist 补偿无法消除折弯；输入角度限制也不能当成最终腕角。诊断见 `diagnosis_M.json`。

## N 的做法

- **放开挥击中右手相对后握把的朝向**。整手绕实际握把轴线换向，保留五指相对手掌的原抓握曲线。Base 接触时相对 K 约转 -75.63°，最大约 -87.66°；这是握持朝向的实质调整，不是原握姿不变的小幅腕部补偿。
- 枢轴在枪根空间 `(0, 0.025, -0.045) m`，轴为归一化 `(0, -0.48, 0.877)`，依据现有后握把源网格的斜向结构确定。
- 根据新的手掌方向与腕位，重新求右肘的位置；肩位置和大小臂长度保持。腕部折弯优先于保留不可能的旧掌面方向。
- 右侧大小臂完整骨段保持同一弯曲平面，前臂剩余轴向转动沿辅助骨分配。辅助骨的位置随所属骨段运动，不再独立锁到手掌。
- 起势与收势平滑进入和退出，辅助骨的蒙皮朝向同样渐变。末帧回到 K 原待机；右手 IK 目标随掌面更新。
- 枪械、左侧手臂、手指局部曲线和业务时序保留：六套均为 0.9 s，接触 0.1667 s。

## 本次明确授权的检查

1. `check_source.py`：六套各 217 个样本（含半帧），比较 K/N 的保留轨道、骨段长度、手指局部曲线、起止姿态与腕轴折角。最大腕轴折角 23.406°，接触处约 18.08°；保留轨道位置差在浮点误差内，手指局部曲线差为 0，骨段长度差小于 0.001 mm，起止姿态一致。
2. `check_contact.py`：Base 九个姿态，按实际后握把源网格检查右手表面邻近关系。挥击关键帧有 563–622 个采样顶点距握把 2 mm 内；这只说明接触邻近，不证明全枪无穿插。最近面法线的有符号距离不作为实体穿插结论。
3. `render_review.py`：第一人称、腕背近景、六套接触姿态及 Base 30 fps 动作预览。近裁剪设置为 1 mm，避免预览相机默认 10 cm 切穿近处手掌。预览为作者源网格，不是 UE 游戏截图；作者源外观中的配件也不是当前游戏枪匠组合的替代证据。
4. `readback_ue.py`：当前编辑器中六套 UE 动画各 109 帧的 RAW/COMPRESSED 姿态。压缩后最大腕轴折角 23.405°；RAW/COMPRESSED 腕位差小于 0.004 mm，折角差小于 0.0005°。

腕轴折角是同一骨架的几何对比指标，不是人体医学关节角或独立视觉验收标准。DeepSeek 辅助读图对 M/N 的描述与本次几何及直接画面对比不一致，未将该接口输出作为通过依据。最终游戏观感由用户试用；本轮没有启动 PIE 或执行其它玩法回归。

## 交付、运行引用与恢复

- `natural_wrist.py`：整手绕握把换向及整臂求解。
- `author_natural.py`：六套作者动画，读取 K，输出 `M4_QuickCombatRefineN_<Profile>`。
- `<Profile>/M4_QuickCombat_<Profile>_Editable.blend` 与 `<Profile>/Animations/A_M4_QuickCombat_<Profile>.fbx`：可编辑源及 120 Hz FBX。
- `import_replica.py`：导入现有 `/Game/Weapons/M4QuickMeleeReplica20260919/<Profile>/A_M4_QuickCombat_<Profile>`。
- `Review/before_after.jpg`、`Review/six_profiles.jpg`、`Review/timeline.jpg`、`Review/N_motion.gif`：源模型对比与预览。
- `source_checks.json`、`contact_checks.json`、`ue_readback.json`、`import.json`：对应检查与导入结果。
- M 作者源与导入前 M 资源已移到项目 `trash/quick-melee-retired-20260919/SourceAssets/M4QuickMeleeRefine20260919M/` 和同归档中的 `M4QuickMeleeRefine20260919N/BaselineM/`。K 保留为有效依赖；历史诊断／对比脚本已改读归档路径。

六套 N 动画已通过当前 FPSGAME 编辑器的 Python 通道导入保存，无需退出或重启编辑器。无 C++ 修改，不需要编译 DLL。等待用户游戏内反馈。
