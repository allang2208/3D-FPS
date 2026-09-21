# 弹药袋概念预览 · 2026-09-21

本目录为用户要求的规划预览，不是游戏截图或已接入UI。图片由内置 imagegen 生成；普通弹以外的弹种及数量为界面示例，未定义伤害倍率。修订2按用户反馈将战斗选择改为圆形轮盘。

- `01-ammo-pouch-page.png`：推荐的背包弹药袋子页，按兼容组折叠，显示数值余额。
- `02-inline-ammo-pouch.png`：装备页内嵌区的备选布局；A762缩略图修订为当前工程图标参考。
- `04-hold-r-radial-v2.png`：当前方案，长按R打开圆形轮盘，移动鼠标选扇区，松开R换弹；回到中心或Esc取消。预选目标尚未确认，因此右下HUD仍显示普通弹。
- 历史 `03-hold-r-selector.png` 已被圆形轮盘替代，移至本机 `trash/a762-ammo-publication-20260921/Concepts/`；原始横排生成图一并归档，映射见 [归档清单](../../../AssetArchives/a762-ammo-publication-20260921.json)。

推荐组合为独立袋页＋圆形战斗轮盘，装备首页仅保留紧凑摘要。内嵌图为布局取舍参考，并不要求替换现有完整装备槽。

风格依据为工程 `Docs/UI/ui-cold-steel-design-system.md` 2.18，以及实际旧截图 `Saved/WarehouseColdGlass20260912/warehouse-equipment-1920.png`。武器参考来自 `Content/ColdSteelData/Icons/ue_a762.png`。概念中的关卡背景及第一人称视图由生成工具绘制，不作为真实资产或接入证明。

原始生成记录（最终采用图保留；旧横排源图已按清单归档）：

- 独立页：`C:/Users/allan/.codex/generated_images/01a0bebc-64ab-7000-83fd-e3871844b41d/exec-a18ac440-e09c-41b6-ab92-7fdf848e451a.png`
- 内嵌区最终修订：`C:/Users/allan/.codex/generated_images/01a0bebc-64ab-7000-83fd-e3871844b41d/exec-a63c98e9-b230-4079-a447-4994ed6bc7d9.png`
- 战斗浮层：`C:/Users/allan/.codex/generated_images/01a0bebc-64ab-7000-83fd-e3871844b41d/exec-9d0dd4ce-fc72-4d74-a2eb-240fdb2f4cd1.png`
- 圆形轮盘修订2：`C:/Users/allan/.codex/generated_images/01a0bebc-64ab-7000-83fd-e3871844b41d/exec-48993889-9bc1-4124-9c1f-3f18852c7979.png`

修订2使用内置 imagegen 编辑旧战斗浮层图。生成要求：保留原场景、枪械与底部HUD，将横排矩形面板替换为居中的圆形环状菜单；普通弹在上、穿甲弹在右下并高亮、燃烧弹在左下灰显；中心显示目标弹种与松R换弹提示；显示鼠标指针，移回中心取消；移除旧滚轮提示并隐藏准星。图中尚未确认选择，因此HUD不提前更新弹种。

完整交互、存档迁移与实施阶段见 [弹药袋方案](../../ammo-pouch-plan-20260921.md)。本页描述最初规划阶段；后续实现及构建范围见 [实施记录](../../ammo-pouch-implementation-20260921.md)。概念 PNG 留本机，不在公共源码包内。
