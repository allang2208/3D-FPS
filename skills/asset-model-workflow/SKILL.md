---
name: asset-model-workflow
description: 使用参考图、三视图和 5080 管线生成游戏模型，完成候选迭代、高低模、PBR、真实接口适配及引擎交付。用于配件、枪械、怪物、道具和建材的模型制作；动画、战斗、枪匠和建筑放置继续使用对应领域技能。
---

# 本机维护源入口

本机共用流程统一读取[asset-model-workflow](C:/Users/allan/.codex/skills/asset-model-workflow/SKILL.md)，不要叠加旧镜像流程。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。

此入口依赖本机个人目录；跨机器交付需另行导出所需维护源和引用。

- 连续靴体、脚踝断面、渲染 LOD 及旧装备实例外观：读取[连续长靴与渲染 LOD](references/continuous-boots-and-render-lods.md)。保留近景与原生权重，区分几何检查、联网检查和帧率实测。
