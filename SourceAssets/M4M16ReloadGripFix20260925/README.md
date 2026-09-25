# M4 / M16 换弹左手抓握精度修复（2026-09-25）

用户反馈：M4 与 M16 换弹时，插入弹匣的左手"还是没有精准抓握弹夹"。本轮按 [ue5-fps-arms-animation](../../skills/ue5-fps-arms-animation/SKILL.md) 的 [先量后写](../../skills/ue5-fps-arms-animation/references/measure-before-writing.md) 与 [异形弹匣自然抓握](../../skills/ue5-fps-arms-animation/references/irregular-magazine-grip.md) 方法排查，并把结论沉淀为 [弹匣抓握跨枪配准](../../skills/ue5-fps-arms-animation/references/magazine-grip-registration.md)。

## 量化结果（每根手骨到弹匣壳的中位间隙，mm）

以用户已认可的 AKM 包握（`AKMReloadPolish20260911/base/A_AKM_reload.blend` 第 148 帧）为基准。同一套量测下 M4 与 AKM 只差几毫米，M16 明显走形：

| 部位 | AKM（认可基准） | M4 修复前 | M16 修复前 | M16 修复后 |
| --- | --- | --- | --- | --- |
| index_01 | 20.9 | 15.8 | **-0.5** | 22.3 |
| middle_01 | 10.1 | 8.2 | **-3.5** | 11.3 |
| ring_01 | -1.1 | 4.4 | -2.8 | 0.7 |
| pinky_02 | 14.9 | 18.1 | **31.0** | 8.6 |
| pinky_03 | 8.7 | 11.8 | **29.3** | 1.8 |
| thumb_02 | 1.3 | 5.5 | **14.9** | 4.5 |
| thumb_03 | 23.8 | 26.6 | **36.7** | 25.8 |

M16 的食指近节整整 21 mm 埋进弹匣、小指却浮在壳外 16–20 mm；对认可基准的剖面误差平方和为 **2530 → 269**（十条 clip 一致）。

## 根因

- **M16**：`M16M4Insert20260920/transplant.py` 用武器空间里一个手估的固定平移（`contact_shift = (-12.1, -9.6, -20) mm`）把 M4 的左手接到 M16 上。两枪弹匣的壳相对挂点位置本来就不同，一个常量既表达不了"握在弹匣哪一段"，也表达不了"壳的截面在哪"，于是食指被推进壳里、小指被推离壳外。`M16RemovalMelee20260920/author.py` 沿用同一个常量。
- **M4**：现有左手已经来自已认可的 AKM 手型，只在弹匣自身截面系里偏了几毫米（并且拇指在压实末段插进机匣 19.6 mm）。属于可用但有残差的姿态，不是错误手型。

## 做法

1. **把抓握存成弹匣自己的关系**：`R = (MagDeform @ ShellFrame)^-1 @ hand_world`。`ShellFrame` 由弹匣自身网格求出：长轴按弹匣脊线拟合、并按该 clip 的插入方向定向（底盖 → 供弹口），薄轴指向掌侧，原点取握持高度处的壳包围盒中心。高度以"距底盖"计。
2. **M4 用有界刚体校正**：在弹匣截面系里搜索 6 个自由度（≤10 mm / ≤12°），目标是对齐 AKM 剖面，并计入"压实末段拇指不得插进机匣"的项。搜索时手网格只求值一次、每个候选按刚体移动，因此很便宜。结果：剖面误差 232.6 → 约 220，机匣穿透 19.6 / 17.5 → 3.5 / 3.5 mm。
3. **M16 换成弹匣系配准**：把修好的 M4 关系按"距底盖同样高度"重建到 M16 弹匣的截面系上（两条候选高度都算一遍，按对 AKM 剖面的误差自动选；"距供弹口等高"的方案误差 3475，被否）。枪弹匣轨道、右手、枪根与全部 cue 不动，只重写左手链与肩肘，按 clip 自己的握持权重进出。
4. **导入**：12 条换弹（M4 普通/空仓 + M16 五握把 × 普通/空仓）经无界面 `UnrealEditor-Cmd -run=pythonscript` 覆盖导入并保存，导入前逐个备份到 `Before/`。

## 交付与入口

| 内容 | 路径 |
| --- | --- |
| 量测与搜索 | `audit2.py`（剖面）、`refine.py`（M4 有界校正搜索）、`grip_lib.py`（壳坐标系与整臂求解） |
| 归一化对比渲染 | `render_cmp.py`（M4 前/后/AKM）、`render_cmp_m16.py`（M16 前/后）、`render_game.py`（游戏相机锚点） |
| M4 作者输出 | `M4Animations/A_M4_ExtContact_reload[_empty].blend` + `_GripPrecise.fbx`（动作名 `A_M4_ExtContact_reload[_empty]_GripPrecise`） |
| M16 作者输出 | `m16_cache/<握把>/A_M16_[<握把>_]reload[_empty].blend` + `_GripPrecise.fbx` |
| 验证 | `verify_m4.py`、`verify_m16.py` → `verify_m4.json`、`verify_m16.json`；M16 剖面误差 2530 → 269，机匣穿透 1.62 → 2.08 mm |
| 导入 | `install.py`、`run_import.ps1`、`install_receipt.json`、`ue-import.log`；覆盖前副本 `Before/` |
| 参数 | `grip_fix.json`（M4 校正矩阵与剖面）、`refine.json`、`m16_grip_authoring.json`（每条 clip 的握持高度与两套候选） |

## 未覆盖

- 未启动游戏、未跑 PIE、未做真机截图；观感与手感由用户实机判读。
- M4 的环指/小指仍比 AKM 基准松 3–6 mm（刚体校正修不动关节弯曲量）；AKM 基准自身在小指中节也有约 15 mm 间隙，未再叠加逐指搜索。
- M16 的快速近战、装备、检弹等共用 M4 供体的片段本轮未改。M16 弹鼓没有换弹片段，不在范围内。
- 未改 C++、音效时钟、枪体/弹匣通道、模型、材质与蒙皮。
