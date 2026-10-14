---
name: ue5-monster-workflow
description: 制作与接入 UE5 怪物，支持 Meshy 已蒙皮绑骨的人形模型复用成熟动作，以及三视图与 5080/用户指定模型、本地拓扑绑骨、Behavior Tree、受击、布娃娃和刷怪。用于原创怪物、现有怪物迭代和 AI 开发；第一人称手臂使用专用手臂技能。
---

# 本机维护源入口

本机共用流程统一读取[ue5-monster-workflow](C:/Users/allan/.codex/skills/ue5-monster-workflow/SKILL.md)，不要叠加旧镜像流程。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。

此入口依赖本机个人目录；跨机器交付需另行导出所需维护源和引用。

鼓囊 M-09 的原骨架动作、单时钟抛射、屏边爆炸方向提示、事件音效和混合版本恢复读 [鼓囊与爆炸物提示](references/bellow-sac-lobber.md)。其制作与构建状态不代表游戏验收；逐足地形适配继续看 [M 系列移动与动作时钟](references/m-series-locomotion.md)。

根冠的原生动画图、攻击时钟、地雷命中和混合版本恢复读 [根冠接入经验](references/root-crown-native-animation.md)；园艺师实体服装见 [无面职员衣物](references/faceless-staff-clothing.md)。
