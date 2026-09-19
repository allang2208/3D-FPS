# 蓄力攻击左臂关节：排查与 V43 重分配

2026-09-16。用户反馈「近战武器蓄力攻击左手的手臂关节错误扭曲」。先做只读排查定位阶段与根因，随后按用户选定的方案 A 制作并接入 V43：把左前臂的轴向旋转从前臂骨改到前臂的两条蒙皮辅助骨上，均匀分布。**未修改**骨骼位置、骨骼方向、握点、剑、右臂、材质、网格、代码、时长与时序。

## 一、排查结论

1. **当前蓄力左臂就是 V22 已接受状态。** 用 V22 `diagnose_heavy.py` 的同一机位与材质重渲 650 ms、2000 ms、释放 60/400 ms，与 `../ChargedArmV22/Review_ChargedArmV22/` 逐帧一致；抬剑 0.65 s = 71.4°、蓄满 2.00 s = 14.2°，即 V22 记录的 71.35° / 14.16°。不是被后续版本改坏，而是 V22 覆盖范围之外留着的原作者曲线。
2. **两把双手剑共用同一套动作。** 符文剑与寒晶·双手剑的 `SK_Manny_Arms_Export` 均为 20326 顶点 / 37802 面 / 52 顶点组，`clavicle_l`、`upperarm_l`、`lowerarm_l`、`hand_l` 的 rest 坐标逐位相同；网格与骨架静止姿态一致（全网格边长比 1.0000）。所以不是寒晶剑网格问题，修动作两把剑同时生效。
3. **扭曲集中在抬剑段与释放段。** 左肘轴向差（V22 同一算法）：0.00 s −99.3° → 0.12 s +53.1° → **0.35 s +105.3°（同时屈肘 109.0°）** → 0.65 s +71.4° → 2.00 s +14.2°；释放 0.075 s −77.7° → 0.60 s −125.2° → 0.80 s **−130.0°** → 1.00 s −99.3°。
4. **整条前臂跟着前臂骨刚性拧转。** `lowerarm_twist_01_l` / `lowerarm_twist_02_l` 在整段动作里恒为 0°，而这两条正是前臂皮肤的实际承重骨（近端前臂 988 顶点 → `lowerarm_twist_02_l`，远端 589 顶点 → `lowerarm_twist_01_l`，肘尖 68 顶点 → `lowerarm_l`）。轴向旋转全部压在 `lowerarm_l`，剪切集中在肘缝。
5. 没有突跳：相邻半帧最大转角抬剑锁骨 21.26°、上臂 9.37°、前臂 7.64°，释放上臂 14.46°、前臂 16.19°。
6. 右臂同指标更大（128°–159°）但用户未反馈问题，因此该指标只用于定位，不单独作为“看起来错”的判据。

## 二、V43 改动（方案 A）

每一帧读取原姿态，把前臂骨上的轴向旋转按沿前臂的线性梯度改写到三条骨上，`hand_l` 保持世界朝向不变、按新父级重建局部旋转：

| 骨 | 位置 x | 剩余轴向（作者值 φ → V43） |
| --- | --- | --- |
| `lowerarm_l` | 0.00（肘尖） | φ → 0 |
| `lowerarm_twist_02_l` | 0.286（肘侧前臂） | φ → 0.286 φ |
| `lowerarm_twist_01_l` | 0.859（腕侧前臂） | φ → 0.859 φ |
| `hand_l` | 1.0（手） | 世界朝向不变，局部自动补偿 |

包络（`twist_distribution.py` 的 `envelope`）在两端归零，保证与未改动的 Idle / Slash2 接缝一致：

- `HeavyCharge`：0–0.10 s 渐入，之后保持到 2.00 s。
- `HeavyRelease`：保持到 0.85 s，0.85–1.00 s 渐出（1.00 s 回到待机）。
- `Slash1`：按运行时未蓄满松手的映射（蓄力 0.65 s ↔ Slash1 0.17 s）用同一蓄力时钟渐入，0.65–0.85 s 渐出，首末帧与待机一致。

### 效果（`seam_report.json`）

| 时刻 | 肘缝轴向差（近端前臂 vs 上臂） | 腕缝轴向差 |
| --- | --- | --- |
| 抬剑 0.20 s | 66.5° → 19.0° | 0° → −9.4° |
| 抬剑 0.35 s | **105.3° → 30.1°** | 0° → −14.9° |
| 抬剑 0.65 s | 71.4° → 20.4° | 0° → −10.1° |
| 释放 0.60 s | −125.2° → −35.8° | 0° → 17.7° |
| 释放 0.80 s | **−130.0° → −37.2°** | 0° → 18.3° |
| 释放 1.00 s / 待机接缝 | −99.3° → −99.3°（不变） | 0°（不变） |

### 保持不动的量（`verification.json`，逐帧 480 Hz 全采样）

- 全部 102 根骨的位置差 ≤ 0.0004 mm。
- `hand_l` 世界朝向差 ≤ 0.00006°（握姿逐位不变）。
- 上臂/前臂方向差 0.000000°；骨长差 ≤ 0.00016 mm。
- 导出 FBX 回读（`fbx_readback.json`、`fbx_world_check.json`）：102 骨、四条辅助骨齐全、时长 2.000 / 1.000 / 1.775 s，世界姿态与作者源差 ≤ 0.0001 cm。

## 二·B、V44：把扭转交给肩关节（上一版）

V43 实测“看不出变化”，因为它只重分配了前臂内部、没有动任何骨骼方向。真正决定肘部外观的是**上臂的轴向（肩部内旋）**：握点固定 ⇒ 手与前臂的朝向被锁定 ⇒ 肘缝的轴向差只能由肩关节承担。V44 因此按帧求解一个上臂绕自身长轴的滚转角，把肘缝轴向差压到 0，前臂、手腕、握点、剑、右臂、时长和全部骨骼位置保持作者原样。

求解在 ±95° 内直接最小化肘缝残差（原姿态 ρ=0 在搜索范围内，因此结果**不会比原动作更差**），1° 粗扫 + 黄金分割细化，并按上一帧结果在等优解中做连续性选择。原始版本用 secant 过零点求解，在释放段跳到了另一侧根并从 4 亿度发散，已废弃。

### 效果（`shoulder_report.json`）

| 时刻 | 肘缝轴向差 原 → V44 | 肩缝轴向差 原 → V44 | 上臂滚转 |
| --- | --- | --- | --- |
| 抬剑 0.20 s | 66.5° → **0.0°** | −98.1° → −38.5° | 59.6° |
| 抬剑 0.35 s | 105.3° → **0.0°** | −7.6° → 72.7° | 80.3° |
| 抬剑 0.50 s | 87.4° → **0.0°** | 19.7° → 71.9° | ~73° |
| 抬剑 0.65 s | 71.4° → **0.0°** | 19.8° → 61.0° | 41.1° |
| 蓄满 2.00 s | 14.2° → **0.0°** | 3.8° → 19.9° | 15.0° |
| 释放 0.075 s | −77.7° → −52.8° | −41.2° → −136.2° | −95°（到上限） |
| 释放 0.60 s | −125.2° → −99.6° | 20.7° → 115.7° | 95°（到上限） |
| 释放 0.80 s | −130.0° → −85.5° | 34.2° → 129.2° | 95°（到上限） |
| Slash1 0.35 s | 66.5° → **0.0°** | 16.5° → 55.9° | 55° |
| 待机接缝（0 s / 1.0 s / 0.85 s 之后） | 不变 | 不变 | 0° |

释放段的杠杆效率明显更低（该姿态下每 1° 上臂滚转只能换约 0.36° 肘缝），需要约 −240° 才能归零，超出肩关节活动度，所以封顶 95° 并保留残差；这段是快速挥砍，V22 当时也保留了原曲线。抬剑、蓄满、未蓄满起势这三处正是用户反馈可见的阶段，已归零。

### 保持不动的量（`verification_v44.json`，每 2 帧采样）

- 全部 102 根骨位置差 ≤ 0.0005 mm。
- `hand_l` 世界朝向差 ≤ 0.00008°（握姿逐位不变）。
- 上臂与前臂**方向**差均 0.000000°（只有上臂滚转改变，方向、肘位、腕位不动）。
- 骨长差 ≤ 0.0002 mm。

### 外观

第一人称与关节对比见 `ReviewV44/sheet_fp.png`、`sheet_joint.png`、`sheet_shoulder.png`：抬剑段的肘部折痕消失、前臂表面变顺；上臂网格随肩部滚转整体旋转（这是 B 预期的可见变化），肩口仍是原网格的开放端，没有出现新的穿插或塌陷。

## 二·C、V45：把蓄满握位朝身体收（当前接入版本）

用户 2026-09-16 19:01 看完 V44 后要求「把蓄满握位朝身体收、把左肘弯起来」。V43 只重分配前臂内部、V44 只滚转上臂，两者都没改左臂的伸展程度：蓄满时剑首离左肩 53.2 cm，几乎等于左臂全长 55.0 cm，肘只能接近伸直，所以那一帧看上去仍是直的。V45 把整段握持（剑 + 双手）沿左腕→左肩连线朝身体移 7 cm，两条手臂用两骨 IK 重解并保持作者肘侧（pole）；手的握点与朝向逐位不动，剑柄接触不变。

### 效果（`verification_v45.json`，V44 → V45）

| 时刻 | 左肘 | 左臂伸展 | 握点位移（左 / 右） |
| --- | --- | --- | --- |
| 蓄力 0.35 s | 109.0° → 126.0° | 0.320 → 0.250 m | 0.0001 / 0.0008 mm |
| 蓄力 0.65 s | 95.2° → 113.6° | 0.371 → 0.301 m | 0.0001 / 0.0005 mm |
| 蓄力 2.00 s（蓄满） | **29.4° → 65.7°** | 0.532 → 0.462 m | 0.0003 / 0.0015 mm |
| 释放 0.075 s | 123.9° → 139.8° | 0.259 → 0.189 m | 0.0002 / 0.0011 mm |
| 释放 0.60 s | 123.2° → 139.2° | 0.262 → 0.192 m | 0.0003 / 0.0012 mm |
| 待机接缝 0 s / 1.0 s | 58.8° 不变 | 0.479 m 不变 | ≤ 0.0002 mm |

握点相对剑柄的旋转差 ≤ 0.00005°，即双手在剑柄上的位置与朝向逐位保持。作者源 `AzureRunesword_ChargedHoldV45.blend`；`hold_shift.py` 为位移、IK 与包络（蓄力 0–0.10 s 渐入，释放 0.85–1.00 s 渐出，Slash1 用同一蓄力时钟），`author_charged_hold.py` 制作，`ExportV45/` 为 480 Hz 烘焙 FBX，`compare_v45.py` / `verify_hold.py` 为对比渲染与校验，`ReviewV45/` 下 `sheet_fp.png`、`sheet_joint.png` 是 V44（左列）/ V45（右列）对比图。

### 接入状态：2026-09-16 20:00 已写入

编辑器开着时先试了远程执行，被守卫拒绝（PIE 中：`End the active PIE session before importing charged attack animations.`）。编辑器关闭后改走独立导入进程：`run_import_v45.ps1` 启动 `WeightLeftV5/ImportHost/RuneSwordImport.uproject`（其 `Content` 是指向 FPSGAME `Content` 的 junction）执行 `import_revision_v45.py`。注意 V43 那次独立导入失败过（`Animation save failed`，编辑器占着 `.uasset`），所以这条路线只在编辑器关闭时可用。

结果：退出码 0，`import_v45.log` 有 `RUNESWORD_V45_IMPORT_COMPLETE`，`import_console_v45.log` 无 Python 错误；三个资产 19:59:59–20:00:01 写入，`import_receipt_v45.json` 记录时长 2.0 / 1.0 / 1.775 s（480 Hz 采样、`BC_M4Viewmodel` 压缩设置），V44 原件已备份到 `BeforeV44/`。

V45 的 FBX 还没做 `verify_fbx.py` / `verify_fbx_world.py` 回读（V44 做过），接入回执只记录时长；编辑器重开后实际手感由用户试玩验收。

## 三、交付与接入

- **当前接入的是 V45**（2026-09-16 20:00 写入 `Content/Weapons/AzureRunesword20260913/`，V44 已退回为上一版）。V44 作者源 `AzureRunesword_ChargedShoulderV44.blend`（保留 `REF_V44_*` 原动作）；`shoulder_transport.py` 为滚转求解与包络；`author_charged_shoulder.py` 制作；`ExportV44/` 为 480 Hz 烘焙 FBX；`compare_v44.py`、`verify_shoulder.py`、`report_shoulder.py` 为对比渲染与校验。
- V43 保留为上一版：作者源 `AzureRunesword_ChargedErgoV43.blend`、`twist_distribution.py`、`author_charged_twist.py`、`Export/`。
- 接入回执：`import_receipt_v45.json`（V45，2026-09-16 20:00）、`import_receipt_v44.json`（V44，18:43）、`import_receipt.json`（V43，18:22），均写入 `/Game/Weapons/AzureRunesword20260913/A_RuneSword_HeavyCharge|HeavyRelease|Slash1`。
- 回退：`Before/` 是 V22 基线，`BeforeV43/` 是 V43，`BeforeV44/` 是 V44；把对应三个 `.uasset` 复制回 `Content/Weapons/AzureRunesword20260913/` 即可。
- 接入入口：`import_revision_v45.py` + `run_import_v45.ps1`（编辑器关闭时的独立 ImportHost 路线，V45 走这条）；`import_live_editor_v45.py` / `import_live_editor_v44.py` / `import_live_editor.py`（编辑器开着时走 `Tools/AssetPipeline/ue_python_exec.py` 远程执行，V43、V44 走的这条）；`import_revision_v44.py` / `import_revision.py` 为对应版本的导入体。

本次只替换三个动画资源，没有原生代码改动。按用户规则未运行游戏、PIE、渲染或玩法回归，实际手感由用户试玩决定。

## 四、方案 B（未做，需要时再走）

固定肩位与握点、骨长不变，把左臂当两骨链重解：肘部在肩—腕轴圆周上按自然 pole 小幅摆动，前臂回到纯摆动（该指标 0°），轴向差交给肩部内旋并分布到上臂辅助骨，腕补偿限制在约 25° 内。会改变抬剑中段剪影，需要重新确认。

## 五、文件清单

- 排查：`probe_source.py`、`diagnose_left_arm.py`、`compare_arms.py`、`measure_twist_bones.py`、`measure_steps.py`、`probe_bind.py`、`measure_skin_distortion.py`、`probe_twist_weights.py`。
- 制作：`twist_distribution.py`、`author_charged_twist.py`、`preview_twist.py`。
- 校验：`verify_twist.py`、`verify_fbx.py`、`verify_fbx_world.py`、`report_seams.py`、`inspect_actions.py`。
- 渲染：`render_left_arm.py`、`render_fp_sequence.py`、`render_left_only.py`、`render_fp_large.py` 及 `Review*/` 图片与拼图。
- 数据：`left_arm_timeline.json`、`compare_arms.json`、`twist_bones.json`、`left_arm_steps.json`、`twist_weights.json`、`skin_distortion.json`、`seam_report.json`、`verification.json`、`fbx_readback.json`、`fbx_world_check.json`、`authoring.json`、`import_receipt.json`。
