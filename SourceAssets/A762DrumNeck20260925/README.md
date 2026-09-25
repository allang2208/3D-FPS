# A762 大弹鼓供弹塔与弹仓衔接（2026-09-25）

用户问"A762 大弹鼓跟弹仓衔接的部分扭曲了，是当时处理模型没做好还是有意这么设计的"，确认后重做了供弹塔并重导静态网格。

## 结论：是有意做的套壳，但不是设计造型

A762 大弹鼓沿用 **AKM 大弹鼓**（`LargeDrumUpgrade20260920/Export/SM_AKM_LargeDrum_Upgrade.fbx`），接 A762 井口时把塔身 z=45→75 mm 做了一次 **smoothstep 渐变的仿射重映射**（`A762Meshy20260920/Accessories05/author_geometry.py` 第 63–70 行）。这段渐变让塔身中心线成 S 形（折角/棱线），并把 67 mm 深的塔身压到 58 mm，而 A762 原厂弹匣在该高度是 72–75 mm——既折角又塞不满井口。

结论、量测表、重建做法与风险见 [A762 大弹鼓供弹塔修复](../../Docs/Weapons/a762-drum-neck-20260925.md)；可复用经验沉淀在 [跨枪套用供弹塔](../../skills/asset-model-workflow/references/modular-part-interfaces.md#跨枪套用供弹塔用线性过渡不要-smoothstep-仿射a762-大弹鼓-2026-09-25)。

## 重建后

| 位置 | 出货塔身 | 重建塔身 | A762 原厂弹匣 |
| --- | --- | --- | --- |
| z=60 mm 中心 / 前后深 | 40.2 / 62.2 | 33.4 / 62.7 | 41.3 / 74.3 |
| z=80 mm 中心 / 前后深 | 58.2 / 58.4 | 47.9 / 64.7 | 44.8 / 71.6 |
| 对机匣净空 z 55–65 | 最深 −1.64 mm | **−1.64 mm（不变）** | −14.3 mm（原厂弹匣自身） |
| 对机匣净空 z 75–90 | −2.59 mm | **−0.18 mm** | — |

塔身 z<45 mm 与鼓体逐点不动；渐变改成线性，所以没有折角。前表面钳制在"不比出货件更靠前"，装配净空与原状一致，不引入新穿透。

## 入口

- 诊断：`audit_drum.py`、`audit_well.py`、`audit_well2.py`、`audit_donor_fit.py`、`audit_collar.py`、`audit_cant.py`
- 重建：`author_drum.py` → `Exports/SM_A762_drum.fbx`、`SM_A762_drum.blend`、`authoring.json`
- 验证/渲染：`verify_drum.py`、`render_drum.py`、`render_assembled.py`
- 导入：`install.py`、`run_import.ps1`、`install_receipt.json`、`ue-import.log`；覆盖前副本 `Before/`

## 未覆盖

- 未启动游戏、未跑 PIE、未做真机截图。
- 只改静态网格（槽位 `A762_drum_0/1/2` 与材质原样回绑），未改动画、材质、C++、图标。
- 更彻底的解是整体后移鼓体让塔身完全竖直，但会改变换弹动画里手握鼓的位置，本轮未做。
