# 穿心箭图标与技能数据

2026-10-27 更新：当前采用 CrimsonV2 赤红贯穿版，完整新图与提示词位于 `CrimsonV2/`，上一版图保留为 `CrimsonV2/reference-previous.png`。上级 `Selected/` 和正式 PNG 已同步到新版；同名 Texture2D 由 `CrimsonV2/import_icon.py` 重导保存。满弓进入穿心箭判定后，整条光晕、边框及流光也切换为红色。以下为最初接入记录。

- 技能 ID：`heartPiercingArrow`，中文名称：穿心箭。
- `Selected/heart_piercing_arrow_cold_steel.png` 是本次采用的生成结果，已复制到 `Content/ColdSteelData/Skills/`。
- 风格参考：项目当前弓精通图标，1254×1254 RGBA；内置图像生成工具以该图片为编辑参考。
- `prompt.txt` 保存完整生成提示词；`skill-definition.json` 保存本次交付的技能参数快照。
- `restore_icon.py` 从选定源恢复正式 PNG 及 skills.json 中该技能的图标路径，不覆盖平衡参数。
- 图标通过现有 FImageUtils PNG 加载入口供技能列表、详情和升级提示共享，无新增 uasset 导入步骤。
- 技能设计和 20 级成长表：`Docs/UI/heart-piercing-arrow-plan-20261026.md`。
- 生成结果展示与源码编译均不代表游戏视觉或战斗验收；本次未运行验收。
