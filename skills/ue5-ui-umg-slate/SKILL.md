---

name: ue5-ui-umg-slate

description: Plan and implement UE5.6-UE5.8 panels, tabs, sections, cards and popups using UMG and Slate. Use for new UI or UI upgrades, FPSGAME Cold Steel design rules, panel/column workflows, Widget Blueprint setup, lifecycle binding, data visibility, input/focus, tooltips and viewport layout.

---

**第一条（FPSGAME）　文件位置与引用路径。** 从当前工程的[制作目录与功能索引](../../Docs/Production/README.md)和[存储规则第 4.1 节](../../WORKFLOW.md#41-存储分配与文件操作边界)查找对应功能。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

- **2026-10-27 优先规则**：浮窗、改造栏与数值交付统一写 `暴击率+10%`、`暴击伤害+10%`，不用中文百分比单位；按[百分比显示规则](references/percentage-display.md)执行，覆盖旧显示写法，保留实际公式。 为什么：统一显示单位可避免将倍率、百分比加成和百分点误读为不同的实际数值。



# 共用规则入口

共用流程读取仓库发布快照：[ue5-ui-umg-slate](../_shared/ue5-ui-umg-slate/SKILL.md)，不要叠加旧镜像流程。 为什么：共用流程只维护一个来源，避免工程镜像与个人版本给出相互冲突的步骤。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。 为什么：当前用户授权决定操作范围，历史测试与协调记录不能自动成为新任务授权。

本入口随仓库提供共用规则快照；日常修订仍回到个人维护源，发布时更新快照。 为什么：相对链接支持换机阅读，单一维护源避免两套规则分叉。

- 锻造/炼药成品预览、配方切换和异步进入状态，读取 [成品参数与准备提示](references/product-preview-readiness.md)。 为什么：「成品参数与准备提示」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

物理书本、纸面文字/图片、长按拖动与书签跳转，读取 [物理书本阅读器](references/physical-book-reader.md)。 为什么：「物理书本阅读器」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

装备缩略浮窗的增益/减益分组、金/黑语义色与中性细线，读取 [装备浮窗增益/减益分组](references/equipment-tooltip-tone.md)。 为什么：「装备浮窗增益/减益分组」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

装备缩略浮窗的套装进度段（件数 `（4/5）`、凑齐后属性、未凑齐降色）及其三个实现坑（分组分支提前 return、行不要进 RowViews、耗时类要显示负号），读取 [装备浮窗套装进度](references/equipment-set-progress.md)。 为什么：「装备浮窗套装进度」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

暴击类词条的三个口径（倍率 `1.80x`／伤害加成 `+25%`／点数 `+10%`）与浮窗映射写法，读取 [暴击相关术语](references/critical-damage-wording.md)。 为什么：「暴击相关术语」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 玻璃容器式能量条顶部补全、上下端帽对称及魔法漂浮光粒，读取 [浮动能量条端帽](references/energy-vessel-caps.md)，使用实际布局反射并保留版本间制作输入。 为什么：「浮动能量条端帽」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 世界工作台拖动卡片、场景命中坐标及四位置种植布局，读取 [工作台拖动与四位置种植](references/world-workbench-drag-and-four-plots.md)。 为什么：「工作台拖动与四位置种植」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 全屏技能树（P）、game-dev 科技树网格连线的 C++ 移植与 game-dev 金色顶部提示，读取 [技能树与子专精](../ue5-skill-magic-workflow/references/skill-tree-and-specializations.md) 与 接入规划（本机资料：`Docs/UI/skill-tree-plan-20261115.md`，不随本次发布）。 为什么：「技能树与子专精」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

地图系统的实景底图、输入焦点和冷钢标记表现，读取 [实景底图、地图输入与标记表现](references/world-map-navigation.md)。

新增村民对话、货架详情或排查无 RHI 的目录图标时，读[村民对话与商店预览](references/resident-dialogue-and-shop-previews.md)。
