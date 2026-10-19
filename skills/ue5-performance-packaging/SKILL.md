---
name: ue5-performance-packaging
description: UE5.6-UE5.8 performance budgeting, regression diagnosis, and packaging readiness. Use for FPSGAME hot-path, HUD, asset or streaming performance constraints, frame-time analysis, PIE performance work, and packaging readiness.
---

# 本机维护源入口

本机共用流程统一读取[ue5-performance-packaging](C:/Users/allan/.codex/skills/ue5-performance-packaging/SKILL.md)，不要叠加旧镜像流程。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。

此入口依赖本机个人目录；跨机器交付需另行导出所需维护源和引用。

## 怪群 GPU 与区域提前准备

同量蒙皮计算突然变慢、玩家装备随怪群变慢或 F6 驻留采集，读 [共享输出缓冲归因](references/shared-skinning-buffer-diagnosis.md)。提前分摊区域刷怪初始化、控制准备池内存和主客机生命周期，读 [区域提前准备](references/area-spawn-preparation.md)。
