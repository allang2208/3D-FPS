---
name: ue5-world-interaction
description: UE5.6-UE5.8 world interaction systems for pickups, spawners, overlap/trace checks, and visual feedback. Use when requests involve interactive world actors, spawn logic, pickup behavior, interaction radius checks, success/failure feedback, and actor lifecycle control.
---

# 共用规则入口

共用流程读取仓库发布快照：[ue5-world-interaction](../_shared/ue5-world-interaction/SKILL.md)，不要叠加旧镜像流程。 为什么：共用流程只维护一个来源，避免工程镜像与个人版本给出相互冲突的步骤。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。 为什么：当前用户授权决定操作范围，历史测试与协调记录不能自动成为新任务授权。

本入口随仓库提供共用规则快照；日常修订仍回到个人维护源，发布时更新快照。 为什么：相对链接支持换机阅读，单一维护源避免两套规则分叉。

涉及设施搜索柜、掉落池、共享取物与旧档迁移时，读取本项目镜像 [搜索容器合同](references/facility-search-containers.md)。个人维护源保留同名参考。 为什么：「搜索容器合同」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- FPSGAME 炼药台的器具命中、金色悬停提示、捕获搅拌、旋钮、温度计和装瓶液体，读取 [炼药台交互](references/alchemy-tabletop-interaction.md)。 为什么：「炼药台交互」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- [生活区收集品与排水工具箱](references/staff-living-collectibles.md)：2026-10-18 本轮实现经验与恢复边界，按问题读取；不授权自动测试。 为什么：「生活区收集品与排水工具箱」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 椅子、沙发、床铺的占位、范围内上床与 SAN 恢复，读取 [家具坐卧交互](references/furniture-rest.md)。 为什么：「家具坐卧交互」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。
