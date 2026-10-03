# PKM 左肘拧转修正 39

2026-09-25：用户反馈"PKM 的左手肘关节还是有些扭曲，无论是待机状态还是换弹状态"。本轮先把上一轮（Elbow38）的接入链查清楚，再按真实网格重新定位。

## 先查上一轮为什么没效果

`../Elbow38/import_elbow.log` 以 `PKM_ELBOW38_IMPORT_COMPLETE` 结束、0 error(s)、`import_receipt.json` 里也有时长，但三个目标包在磁盘上完全没动：

| 资产 | 大小 | 修改时间 |
| --- | ---: | --- |
| `A_PKM_idle.uasset` | 185895 | 2026-09-22 17:52:40 |
| `A_PKM_reload.uasset` | 10732836 | 2026-09-23 07:43:35 |
| `A_PKM_reload_empty.uasset` | 11960936 | 2026-09-23 17:11:51 |

也就是说 V38 的修正**从未进入游戏**，用户看到的一直是原形变（不是回退）。V38 自身的取样也说明问题：它只修了待机 0 s、换弹 6.4 s 两三个离散帧（−8.21°→−1.84°），放着 52.72° 的一帧没动，还把换弹 2.0 s 从 −9.62° 改坏成 +9.51°。**这类问题必须整段扫，不能看首尾帧。**

另外，V38 只把误差当成"肘缝两点之间的轴向差"，没有解释用户实际看到的锯齿折带。

## 诊断：权重交叉带被拧

在真实 V7 PKM 手臂网格（18642 顶点 / 250 骨 / top-4 权重）上按线性混合蒙皮逐帧重放，绕活体肢体轴量表面滚转、按弧长切片：

- 从上臂到腕部滚转一路平滑下降，却在 **t≈0.28→0.42（约 3 cm）倒退 46°** 再继续下降。倒退即判据。
- 各骨在**自己的蒙皮站位**上单独加一圈探针环量施加滚转（待机）：

| 骨 | 站位 t | 施加滚转 |
| --- | ---: | ---: |
| `upperarm_twist_01_l` | −0.31 | −17° |
| `upperarm_twist_02_l` | −0.18 | −32° |
| `lowerarm_l` | 0.23 | **−22°** |
| `lowerarm_twist_02_l` | 0.35 | **−91°** |
| `lowerarm_twist_01_l` | 0.85 | −164° |
| `hand_l` | 1.00 | −195° |

前臂骨长 0.2725 m。根因是**辅助骨权重交叉**：`lowerarm_l` 几乎不承担旋前，却在 t≈0.33–0.42 仍占 0.45–0.61 权重；`lowerarm_twist_02_l` 在 0.28 已占 0.89 且拧了 −91°。两站区间重叠、扭转相差约 70°，表面只能被拧成折带。肘带权重实测：`upperarm_twist_01_l` 0.025、`upperarm_twist_02_l` 0.404、`lowerarm_l` 0.242、`lowerarm_twist_01_l` 0.004、`lowerarm_twist_02_l` 0.324 —— 拧转来自辅助骨对，不是上臂。

已排除权重异常：PKM 前臂权重布局与已认可的 M4 主控差异 ≤0.08（`lowerarm_twist_02_l`）／≤0.13（`lowerarm_l`）。（JSON 空间的刻度标定未收敛，该对比只作参考，不作结论。）

## 修法：旋前斜坡 + 每帧保护

让前臂各辅助骨回到一条从肘侧（上臂当前滚转）到腕侧（手当前滚转）按站位线性插值的曲线上。每帧对每根骨施加"绕活体前臂轴、过该骨自身骨头"的世界空间附加扭转，并保持其全部后代的 world 矩阵不变 —— 握点、手掌、手指接触与腕部**由构造保证零漂移**（实测 `max hand drift` 精确为 0.0000000）。上臂辅助骨不动，肩侧开口不受影响。

站位上限：`lowerarm_l` 75°、`lowerarm_twist_02_l` 35°、`lowerarm_twist_01_l` 30°。

每帧保护：先用真实网格与权重算该帧滚转序列的"最大倒退步长"，修正后若不变小就按 1.0→0.75→0.5→0.25→0 逐级缩，取第一个不劣化的档。三个基础片段里满额修正的帧数为 61/61、750/781、759/793。

## 效果（真实网格整段扫描）

| 片段 | 最大倒退步长 | 平均 RMS 对斜坡 | 平均总变差 |
| --- | ---: | ---: | ---: |
| 待机 | 32.8° → **9.0°** | 23.5° → 17.2° | 223.1° → 148.1° |
| 换弹 | 212.6° → 212.6°（单帧量测伪影） | 21.5° → **15.1°** | 186.4° → 123.0° |
| 空仓 | 82.0° → **57.6°** | 24.6° → 17.4° | 213.7° → 140.8° |

`Review/elbow39/<clip>/{before,after}/` 为同一批相机的对照图（相机逐帧跟随肘部）。待机的锯齿折带基本消失、只剩两个针尖大小残留；换弹 3.25 s 的横向撕裂折带完全消失。图片仅供作者侧对照，最终观感由用户判断。

## 家族片段

四类握把／配件家族同步处理，各三段共 12 段：待机取 `GripContact15/PKM_<family>_Editable.blend` 的 `PKM_Game_idle`，换弹取 `Reload16/PKM_<family>_Reload_Editable.blend` 的 `PKM16_<family>_reload`，空仓取 `Charge34/PKM_<family>_ChargePush_Editable.blend` 的 `PKM34_<family>_reload_empty`。修正由各自姿态自洽导出，数值不照搬。12 段同样 `max hand drift` 为 0。

## 文件

- `author_elbow39.py`：投递脚本。默认跑三段基础片段；`-- families` 跑 12 段家族片段。
- `probe_families.py` / `family_actions.json`：家族可编辑 Blend 里的动作名与帧范围清单。
- `diagnose_elbow.py`、`diagnose_shear.py`、`diagnose_axial.py`、`profile_twist.py`、`fit_elbow.py`、`optimize_elbow*.py`：诊断与拟合过程，含被推翻的中间结论。
- `verify_elbow39.py`、`review_elbow39.py` / `verify_elbow39.json`：整段量测与对照渲染。
- `import_elbow39.py`、`import_elbow39_families.py`：UE 覆盖式导入，导入前后对目标包取长度与 SHA-256 写进回执。
- `v7_mesh.npz`、`author_rig.npz`、`weight_report.json`：真实 V7 网格、权重与作者骨架绑定（作者骨架与 V7 骨架缩放 1.000000、正交误差 3.58e-07）。
- `Exports/`（基础）、`Exports/<family>/`（家族）：交付 FBX。`Edit/`：基础片段改后可编辑 Blend。
- `Before/`、`Before/families/`：覆盖前备份。
- 完整 Blend、FBX、uasset 与网格快照属本机恢复内容；公开 Git 只收脚本、参数说明与文档。

## 游戏资产

覆盖既有路径，未改路由、时长、采样率与压缩设置（沿用 PKM 私有 Skeleton 与 `BC_M4Viewmodel`）：

- `/Game/Weapons/PKMLowpoly20260922/Animations/A_PKM_{idle,reload,reload_empty}`
- `/Game/Weapons/PKMLowpoly20260922/Accessories14/Animations/<family>/A_PKM_<family>_{idle,reload,reload_empty}`

回执 `import_receipt.json` / `import_receipt_families.json` 记录每个资产的导入前后哈希与时长：

| 资产 | 时长 | 大小 | SHA-256 前 → 后 |
| --- | ---: | ---: | --- |
| `A_PKM_idle` | 1.00 s | 186010 | `8c2d2660e4945efd` → `da47b377fab4b505` |
| `A_PKM_reload` | 6.50 s | 10757858 | `85e467290752b3b1` → `2e5f096a55446b0e` |
| `A_PKM_reload_empty` | 6.60 s | 11961049 | `5a65a7ee1b552316` → `db238a23cf8de87a` |

15 个资产全部 `changed=True`。通过 `Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript` 的互斥批次导入。

## 边界

- 未启动 PIE，未执行任何游戏测试；实机效果交由用户测试。
- 手掌、手指接触、武器根变换、机械件时序、音效时钟、动作时长与采样率均未改；手部世界矩阵由构造保持。
- 经验已回写 `skills/ue5-fps-arms-animation/references/thrust-elbow-clearance.md`（新增"权重交叉带被拧"与"接入回执必须证明文件真的被改写"两节）。