---
name: ue5-cpp-gameplay
description: UE5.6-UE5.8 gameplay C++ implementation for Actors, Components, DataAssets, and gameplay logic. Use when requests ask to write .h/.cpp pairs, expose UPROPERTY/UFUNCTION to Blueprint, use GameplayTags, or build reusable component-based systems.
---

# 共用规则入口

**第一条（FPSGAME）　文件位置与引用路径。** 从当前工程的[制作目录与功能索引](../../Docs/Production/README.md)和[存储规则第 4.1 节](../../WORKFLOW.md#41-存储分配与文件操作边界)查找对应功能。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

共用流程读取仓库发布快照：[ue5-cpp-gameplay](../_shared/ue5-cpp-gameplay/SKILL.md)，不要叠加旧镜像流程。 为什么：共用流程只维护一个来源，避免工程镜像与个人版本给出相互冲突的步骤。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。 为什么：当前用户授权决定操作范围，历史测试与协调记录不能自动成为新任务授权。

本入口随仓库提供共用规则快照；日常修订仍回到个人维护源，发布时更新快照。 为什么：相对链接支持换机阅读，单一维护源避免两套规则分叉。

- F6 面板固定动作观察镜头：[固定第三人称观察](references/fixed-third-person-observation.md)。 为什么：「固定第三人称观察」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 已支付工件、评分品质与联机结算：[工件品质契约](references/paid-workpiece-quality.md)。 为什么：「工件品质契约」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- FPSGAME 联机归属、事务中断与重连／重生／换图：[生命周期与覆盖记录](references/multiplayer-lifecycle-and-coverage.md)。 为什么：「生命周期与覆盖记录」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- [升级奖励与公开镜像](references/profile-progress-publication.md)：2026-10-18 本轮实现经验与恢复边界，按问题读取；不授权自动测试。 为什么：「升级奖励与公开镜像」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- [装备套装效果的三层数据](references/equipment-set-effect-layers.md)：`items.json`／`source-combat-items` 覆盖层／`SetEffect()` 各拥有什么；覆盖层只补缺失字段、套装识别只认三槽、单件属性与五件套效果的分界、新增比例词条的加减乘口径。 为什么：「装备套装效果的三层数据」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。
- 原生身体/性别变体、MetaHuman 头发装配、换装与家具相机：[身体变体工作流](references/native-body-variants.md)。 为什么：「身体变体工作流」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 人物冷加载缺头、整人隐藏及衣物晚到：读取 [首次外观就绪](references/initial-appearance-readiness.md)。 为什么：「首次外观就绪」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

- 消耗品的双手互斥、左键取消、普通面板与工作台待机见[交互动作占用](references/consumable-action-ownership.md)。 为什么：「交互动作占用」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。

铁匠和木匠共用身体、独立头与工装的装配见[Jason R4 工匠身体](references/native-body-variants.md#铁匠与木匠共用-jason-r4)。
