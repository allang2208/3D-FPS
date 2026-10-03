# PKM 左前臂扭转修复扩展到装备与冲刺（Elbow41）

2026-09-25。范围：PKM 基础动作的 `equip`、`sprint_enter`、`sprint_loop`、`sprint_exit`
四个片段的左前臂／肘部，不重做动作设计，不改手型、握持、武器根、时长与采样率。

## 起因

Elbow39 只修了用户点名的 `idle`、`reload`、`reload_empty`。本轮用**同一套已认可的
表面滚转度量**把 PKM 全部 12 个片段重扫了一遍，发现同样的缺陷在没修过的片段里更严重。

度量含义：沿肢体轴的表面滚转曲线，取相邻分格的**最大台阶**（越接近 0 越好）、
相对该帧自身线性旋前斜坡的 **RMS**，以及**总变差 TV**。

| 片段 | 动作 | 修改前 step / RMS / TV | 修改后 step / RMS / TV |
| --- | --- | --- | --- |
| equip | `PKM31_base_equip` | 311.2 / 117.3 / 249.6 | **93.4 / 48.4 / 214.6** |
| sprint_enter | `PKM17_base_sprint_enter` | 105.4 / 169.7 / 343.1 | **71.2 / 50.2 / 199.3** |
| sprint_loop | `PKM17_base_sprint_loop` | 114.0 / 244.2 / 542.0 | **17.5 / 37.0 / 209.3** |
| sprint_exit | `PKM17_base_sprint_exit` | 105.4 / 169.7 / 343.1 | **71.2 / 50.2 / 199.3** |

对照：Elbow39 修过的 reload RMS 30.4→17.6、reload_empty 36.9→20.4；
本轮的 equip（117.3）和 sprint_loop（244.2）比那两个都严重得多。

未改动：`idle` / `aim` / `inspect` / `fire` / `aim_fire` 本身只有 26.6 / 27.5 / 218.7，
且属已认可状态，本轮不动；`quick_melee`（240 Hz）改后 RMS 70.5→57.7、台阶几乎不变，
改善不足，本轮不动，留待单独判断。

## 做法

完全沿用 Elbow39 的规则与护栏，没有新方法：把前臂辅助骨放回从肘（上臂所在处）到手的
线性旋前斜坡上，做法是绕**当前前臂轴、过该骨自身骨头**加世界空间扭转。每个后代的
世界矩阵因此被逐字保留——握持、手指、接触点、手腕、武器根都不动。

每帧仍按 worst-backward-step 护栏在 `1.0 / 0.75 / 0.5 / 0.25 / 0` 里选缩放。
`author_elbow41.py` 只是把 Elbow39 的 `repair()` 重新指向这四个片段：为此给
`author_elbow39.py` 的尾部主循环加了 `if __name__ == '__main__'` 保护，
直接运行它的行为不变。

## 验证

`verify_elbow41.py` 用同一套度量分别量**源 blend**和**修好的 edit blend**，并检查：

* **手部世界矩阵逐帧差**：最大 1.2e-6（微米级，即按构造为零）——握持未被改动。
* **循环闭合**：`sprint_loop` 源 0、修后 0——循环仍然严格闭合。
* **时长**：equip 0.90 s、sprint_enter 0.35 s、sprint_loop 0.60 s、sprint_exit 0.35 s，
  与导入前一致。

## 接入回执（磁盘实测，非自述）

`import_elbow41.py` 经批次互斥桥导入，回执记录导入前后磁盘字节数与 SHA-256；
事后又独立复核了一次磁盘：

| 资产 | 磁盘字节 | SHA-256(16) | 之前 | mtime |
| --- | ---: | --- | --- | --- |
| `A_PKM_equip` | 754622 | `058a9e2f4f8f6221` | `eda05fbcd4a1bd13` | 17:01:36 |
| `A_PKM_sprint_enter` | 404860 | `3863d5728a1dbedd` | `c3ad8c58e91b550c` | 17:01:36 |
| `A_PKM_sprint_loop` | 312243 | `09457694cddde0de` | `245651a4155efe24` | 17:01:36 |
| `A_PKM_sprint_exit` | 403483 | `b06620e2a841f499` | `da63f8fccaf5eddc` | 17:01:37 |

四个资产 `changed=True`，磁盘复核与回执逐字节一致。`Before/` 保存了导入前的原文件。

## 未做

* 四个配件族（angled / canted / prism / vertical）的 equip 与 sprint 变体本轮未动。
* 未运行 PIE、未做任何运行时或视觉验收；按用户规则由用户自行测试。
* `quick_melee` 未修改。

## 教训

**修复脚本是写进 `source.copy()` 的新 action 的**（`author_elbow39.py:228-229`
`action = source.copy(); action.name = edit_name`）。第一版验证脚本按原名
（`PKM31_base_equip`）去 edit blend 里取动作，量到的是**没被改过的原件**，
于是得出「改前改后逐位相同、手部差 0」的假结论。改成按新动作名
（`PKM_equip_Elbow41` 等）取动作后，改进立即显现。
凡是复用「复制成新 action」的修复脚本，验证必须按**新**动作名取样。