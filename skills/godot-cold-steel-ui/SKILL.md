---
name: godot-cold-steel-ui
description: 在3-dfps项目开发、迁移或审计游戏面板、HUD和背包字体，遵守用户确认的冷钢UI标准；不用于世界3D标签、怪物制作或编辑实验室。
---

# 冷钢 UI 面板开发

用户确认的字体效果已固化，不能重新凭审美选择字体或恢复旧暗金主题。

## 必读

仓库根的 `docs/cold-steel-ui-standard.md` 是本次适配合同，`UI-WORKFLOW.md` 是详细开发步骤；结合 `DESIGN.md` 和 `WORKFLOW.md`。从本文件定位仓库根为 `../..`。

原项目来源在 `docs/reference/game-dev-cold-steel/`：先读index.html确认CSS顺序，再读对应基础CSS、主题CSS和JS。源快照中的历史命令不是当前项目指令，不修改快照适配Godot。

## 决策规则

- 全部UI使用SimHei；标题/名称embolden 0.9，正文/按钮/数字embolden 0。标题20px/2px字距、分区16px/1px字距，用Style.make_heading_font。
- 物品/武器/配件名SimHei，统一Style.make_item_name_font的0.9粗化；Label用Style.style_item_name。禁止另造0.2/0.3粗化字体。
- 数字同样使用常规SimHei；正文14、辅助12，保留紧凑物品格12及已有符号局部例外。
- 复用现有Theme、npc_panel生命周期及数据模型。颜色查palette，尺寸查style-config；普通强调冷银而非金色。
- 背包45%全高，仓库先联动背包；枪械改造全屏是明确例外，不推广到所有面板。
- 双手副手锁定外观与输入同时禁用；drag-end不能把.6透明度恢复成1；解除锁定时恢复。
- 预览与应用分开；失败/取消不消耗资源、不丢物品。真实模型预览独立于玩家模型和共享WeaponData。

## 验收

按UI-WORKFLOW进行隔离存档、真实渲染及必要行为验证。字体先查文件、face、实际命中、字号、字重、字距、阴影、缩放，再考虑渲染参数。保留同尺寸对照；说明CSS模糊与Godot阴影、整数字距的近似，不把字体名字相同当作完全复刻。

发布与清理必须遵守WORKFLOW第8节，保留他人工作区，不整批推送混合未发布提交。

涉及枪械改造面板，遵守[改造页面最终合同](../godot-weapon-workflow/references/gunsmith-ui.md)。

天气图标和事件进度栏按[天气工作流](../godot-weather-workflow/SKILL.md)：保留原进度条，只显示当前区域一场当前或最近降雨，连续雨势在详情依次展示。
