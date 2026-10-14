---
name: ue5-skill-magic-workflow
description: 开发和迁移 FPSGAME 的主动、被动技能与魔法，贯通技能数据、修炼存档、快捷栏、动作占用、施法手势和 Niagara 特效。火球 V3 是已获用户认可的左手施法基线；手臂蒙皮细节转手臂技能，面板细节转冷钢 UI 技能。
---

# 本机维护源入口

范围、连锁技能被栏杆或镂空障碍误挡时，读取[范围与连锁遮挡](references/area-skill-occlusion.md)。

本机共用流程统一读取[ue5-skill-magic-workflow](C:/Users/allan/.codex/skills/ue5-skill-magic-workflow/SKILL.md)，不要叠加旧镜像流程。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。

此入口依赖本机个人目录；跨机器交付需另行导出所需维护源和引用。

- 雷暴领域当前法杖门槛、等级范围、室内落雷与密云作者见 [领域落雷与蓄力贯穿](references/electric-magic-migration.md) 顶部2026-10-12规则；覆盖旧的空手释放说明。

## 魔法书专注与施法快照

- 法杖＋副手书的施法加速、减耗、受击扣魔及影子档案事务，读取[副手魔法书](../ue5-weapon-workflow/references/spellbook-focus-and-publication.md)。派生电系法术只应用一次专注；客户端反应与服务器扣魔通过轮次和累计记录衔接。

## 持续魔法联机

龙息、雷暴领域和暴风雪的施法编号、预测回执、异步表现、奖励档案及离场结算，读取 [持续魔法的联机状态与收尾](references/persistent-magic-network.md)。
