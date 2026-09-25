# 野外手套皮革与猎装外形

2026-09-25 两件手套物品：黑色 `ue_field_gloves_black` 保持贴合薄皮，棕色 `ue_field_gloves` 独立成猎装短手套。未做运行验收。

## 款式必须分家族

同一套网格换色可以共享 `FittedFieldGlovesV1`。要改棕色外形时，不能重跑 `import_fitted_field_gloves.py` 覆盖黑色。棕色走 `HuntFieldGlovesV1`，只更新 `ue_field_gloves` 的 `rig_meshes`，不要改 `profile.gloves`（那是黑色与无配方时的回退）。弓要单独 rebound 成 `SK_Bow_HuntFieldGloves`，不能覆盖 `SK_Bow_FieldGloves`。

## 第一人称要能读出体积

沿法线偏移 0.5 mm 在近景里几乎看不见。薄皮背侧约 0.70 mm、掌心 0.15 mm；猎装要把体积放在手背：背侧约 3.2 mm、四颗 MCP 衬垫约 5.5 mm（按指节权重取 max，避开 PIP）、腕口卷边约 4.5 mm 加束带脊。腕口边界仍零位移。掌心、指腹、虎口保持接触包络。护板避开指缝与弯折。过薄的第一版已被加厚版取代，不要退回 1.2 mm 背侧。

## 皮革材质

Manny 独特 UV 拉伸，不能把扫描颗粒烘到 UV0。用 rest-pose 三平面（`PreSkinnedPosition` / `PreSkinnedNormal`），约 25 cm Quixel 顶层棕革，左右手相位错开。OpenGL 法线在 UE 翻绿；金属 0，高光中心约 0.35。不要把 Height 当法线（会读成毛），也不要再接 Gloss（与粗糙度重复）。颗粒背侧约 0.36、mip 约 1.1；收到 0.28 + mip 2.0 会重新变成橡胶。磨损只加深、加糙、压平颗粒。组件把物品的一份材质盖到该部件各槽。

## 制作入口

| 家族 | 作者 | 导入 | 物品 |
| --- | --- | --- | --- |
| 贴合薄皮 | `author_fitted_field_gloves.py` | `import_fitted_field_gloves.py`（只发布黑色） | `ue_field_gloves_black` |
| 猎装短手套 | `author_hunt_field_gloves.py`、`hunt_glove_thickness.py` | `import_hunt_field_gloves.py` | `ue_field_gloves` |
| Body | `author_body_field_gloves.py` / `author_body_hunt_field_gloves.py` | 对应 import | 按物品 |
| 弓 | `rebind_bow_field_gloves.py` / `rebind_bow_hunt_field_gloves.py` | 各自网格 | 按物品 |

皮革构建 `build_field_glove_leather.py`，磨损遮罩 `bake_field_glove_wear.py`。图标 `render_field_glove_icons.py` / `export_hunt_glove_presentation.py`；猎装俯视看不出垫时用 `render_hunt_glove_icon_tilt.py`。库存图标 PNG 按仓库忽略规则留本机。

防御与 5% 近战攻速 / 5% 换弹写在 `source-combat-items.json` 的 `bonusStats`。近战攻速走 `EquipmentBonus("meleeAttackSpeed")`，换弹走独立的 `reloadSpeed` 乘区，不能合成一个敏捷值。目录 `name`/`desc` 是实例快照，旧存档要进一次游玩才同步。

确认退役的皮革中间验证与一次性 MCP 日志按清单在本机 `trash/field-glove-superseded-20260925/`；公开记录 `Docs/Characters/field-glove-retired-manifest-20260925.json`。保留 `verify-v7.json`、`ue-cmd-v7.log`、猎装正式 Blend 与各 profile 回执。
