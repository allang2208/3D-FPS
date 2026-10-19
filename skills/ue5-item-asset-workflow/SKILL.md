---
name: ue5-item-asset-workflow
description: 为 FPSGAME 制作非枪械物品：写实图标、按形态分流的模型制作、PBR 材质、稀有度掉落光效与接入验收。用于药水、材料、弹药包装和卷轴；枪体、配件和手臂走专用技能。
---

# 本机维护源入口

本机共用流程统一读取[ue5-item-asset-workflow](C:/Users/allan/.codex/skills/ue5-item-asset-workflow/SKILL.md)，不要叠加旧镜像流程。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。

此入口依赖本机个人目录；跨机器交付需另行导出所需维护源和引用。

制作文件、检修材料、服务器硬件或调整收集物图标时，读取本项目镜像 [搜索收集物资产](references/search-collectible-assets.md)。个人维护源保留同名参考。

护甲/手套/鞋靴/裤装的 `bonusStats`、套装、百分比语义与联机目标取值，读取 [装备属性词条、套装与联机取值](references/equipment-stat-effects.md)。

- 头部装备、第一人称视野层与背包图标完整接入：[头部装备、第一人称视野层与背包图标完整接入](references/head-equipment-and-inventory-icons.md)。按问题读取，历史证据不授权自动重测。
