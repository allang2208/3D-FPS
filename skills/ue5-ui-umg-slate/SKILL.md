---

name: ue5-ui-umg-slate

description: Plan and implement UE5.6-UE5.8 panels, tabs, sections, cards and popups using UMG and Slate. Use for new UI or UI upgrades, FPSGAME Cold Steel design rules, panel/column workflows, Widget Blueprint setup, lifecycle binding, data visibility, input/focus, tooltips and viewport layout.

---

# 本机维护源入口

本机共用流程统一读取[ue5-ui-umg-slate](C:/Users/allan/.codex/skills/ue5-ui-umg-slate/SKILL.md)，不要叠加旧镜像流程。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。

此入口依赖本机个人目录；跨机器交付需另行导出所需维护源和引用。

- 锻造/炼药成品预览、配方切换和异步进入状态，读取 [成品参数与准备提示](references/product-preview-readiness.md)。

物理书本、纸面文字/图片、长按拖动与书签跳转，读取 [物理书本阅读器](references/physical-book-reader.md)。

装备缩略浮窗的增益/减益分组、金/黑语义色与中性细线，读取 [装备浮窗增益/减益分组](references/equipment-tooltip-tone.md)。

装备缩略浮窗的套装进度段（件数 `（4/5）`、凑齐后属性、未凑齐降色）及其三个实现坑（分组分支提前 return、行不要进 RowViews、耗时类要显示负号），读取 [装备浮窗套装进度](references/equipment-set-progress.md)。

暴击类词条的三个口径（倍率 `1.80x`／伤害加成 `+25%`／点数 `+10%`）与浮窗映射写法，读取 [暴击相关术语](references/critical-damage-wording.md)。

- 玻璃容器式能量条顶部补全、上下端帽对称及魔法漂浮光粒，读取 [浮动能量条端帽](references/energy-vessel-caps.md)，使用实际布局反射并保留版本间制作输入。
