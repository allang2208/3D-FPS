# 猎手刀身 — 2026-10-27

尼泊尔弯刀专属特殊刀身，选项 ID `hunter_blade`，位于刀身改造栏。

## 数值

- 攻击距离+25%：`range_mult = 1.25`
- 物理伤害+10%：`physical_damage_mult = 1.10`
- 攻击体力消耗+25%：`stamina_mult = 1.25`

沿用现有单刀数值结算。双持两把刀各自读取本刀改造；攻击体力消耗继续应用于普通攻击及武技。没有新增攻速修正。外观长度不再次乘入攻击距离。

## 模型与材质

以百炼均衡刃为基础，只延长外露刀身，6.6 cm 以下的握柄接口保持原位。外露纵向长度由 19.6906 cm 变为 29.5359 cm，即现有长度的 1.5 倍。可编辑文件为 `Kukri_Hunter_Editable.blend`，导出网格为 `Export/SM_Kukri_Blade_Hunter.fbx`。

独立烘焙 2048 BaseColor、ORM 和切线空间 Normal，采用石墨灰缎面钢、银色刃口与细向磨纹。法线导入 UE 时翻转绿色通道。三款符文为新刀身独立烘焙，继承现有浮雕材质，不通过整体拉伸旧贴图适配。

刀尖场景接触位置按各手当前网格的模块数据读取；敌人命中距离仍由该刀的攻击距离数值决定。

## 图标

`Icons/ue_kukri_blade_1_hunter_blade.png` 由 image_gen 单独生成，输入为本刀身模型参考图与既有钢框样式参考。生成提示保存在 `Icons/generation-prompt.txt`。采用中性灰、四角铆钉钢框、银色内圆、暗色底板和透明外缘。

生成原件：`C:/Users/allan/.codex/generated_images/01a17715-3312-74c2-a3a3-318b877cf0ca/exec-af7b18e4-9fc7-423e-8f69-b7f306e687e3.png`。运行时 PNG 和 UE UI 纹理均已落盘。

## 接入与交付

- 原生模块：`FPSGAMEEditor Win64 Development` 后台构建成功，耗时 47.87 秒，记录见 `build-editor.log`。
- 资源：无界面 Python commandlet 完成导入并保存 13 个 UE 资产，记录见 `import-receipt.json` 和 `import-commandlet.log`。
- 数据：运行时及现有制作源的 `kukri-gunsmith.json`、`kukri-modules.json` 已增量写入；旧文件保存在 `Before/`，发布记录见 `publication-receipt.json`。
- 未打开交互式 UE 编辑器，未运行游戏、回归或验收，由用户在游戏内测试。

重做顺序：`author_hunter.py` → `bake_hunter_runes.py` → 单独生成图标 → `import_hunter.py` → `publish_hunter.py`。必要的源码构建可用 `build-editor.ps1`。
