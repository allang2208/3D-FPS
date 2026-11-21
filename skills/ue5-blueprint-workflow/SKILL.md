---
name: ue5-blueprint-workflow
description: UE5.6-UE5.8 Blueprint graph workflow for feature implementation, input events, node wiring, and graph validation. Use when requests involve adding Blueprint logic, keyboard input behavior, function chains, event graph edits, or pin-level connection guidance.
---

# 蓝图编辑工作流

**第一条（FPSGAME）　文件位置与引用路径。** 从当前工程的[制作目录与功能索引](../../Docs/Production/README.md)和[存储规则第 4.1 节](../../WORKFLOW.md#41-存储分配与文件操作边界)查找对应功能。先确定制作源、正式资产和输出目录，再创建或引入文件。工程 Content 资产用 `/Game/...` 包名引用，制作脚本从工程根或已配置的制作源根解析相对路径。交付时在同一功能条目登记实际位置、引用及备份状态。

领域流程见仓库内的[共用技能快照](../_shared/ue5-blueprint-workflow/SKILL.md)。
