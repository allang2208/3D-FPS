---
name: ue5-auto-assistant
description: UE5.6-UE5.8 automatic assistant entry for beginners. Use when users ask Unreal questions without naming a specific skill. Auto-route to the most precise UE5 skill and recommend dedicated MCP tools.
---

# 共用规则入口

**第一条（FPSGAME）　文件位置与引用路径。** 从当前工程的[制作目录与功能索引](../../Docs/Production/README.md)和[存储规则第 4.1 节](../../WORKFLOW.md#41-存储分配与文件操作边界)查找对应功能。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

共用流程读取仓库发布快照：[ue5-auto-assistant](../_shared/ue5-auto-assistant/SKILL.md)，不要叠加旧镜像流程。 为什么：共用流程只维护一个来源，避免工程镜像与个人版本给出相互冲突的步骤。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。 为什么：当前用户授权决定操作范围，历史测试与协调记录不能自动成为新任务授权。

涉及 `player_body.json` 的修改、恢复或发布，读取工程的 [共享配置写入与发布](../../Docs/Workflow/player-body-config-publication.md)；旧配置与暂存副本不能覆盖工作文件。 为什么：该文件由多个动作与装备共用，按字段写入才能保留其他未提交内容。

本入口随仓库提供共用规则快照；日常修订仍回到个人维护源，发布时更新快照。 为什么：相对链接支持换机阅读，单一维护源避免两套规则分叉。

- FPSGAME 的 SSD、DDC、Content 联接与恢复留存整理，读取 [项目存储与目录联接](references/project-storage-junctions.md)。 为什么：目录联接可能指向活动资产或独有源文件，路径用途决定保留边界。
- 多会话共用脏工作区、只能按功能切片发布共享宿主时，读取 [并行脏工作区的 Integration 补丁切片](references/integration-patch-slicing.md)。 为什么：「并行脏工作区的 Integration 补丁切片」已有专属约束与实现入口，集中查阅可避免复制另一套不一致的处理方法。
