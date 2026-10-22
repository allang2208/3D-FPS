---
name: ue5-fluid-vfx-workflow
description: 为 FPSGAME 制作和优化 UE5 流体特效，包括枪口烟、火焰与爆燃余烟、水花与涟漪、毒液与毒池、血液及冰系冷雾；贯通 Mantaflow 烘焙、Niagara、材质、SVT 和运行时性能预算。用于同类效果新增、自然度和可见性调整、透明方块修复及全水体接入；技能数值、枪械动作和怪物 AI 仍走对应领域技能。
---

# 本机维护源入口

本机共用流程统一读取[ue5-fluid-vfx-workflow](C:/Users/allan/.codex/skills/ue5-fluid-vfx-workflow/SKILL.md)，不要叠加旧镜像流程。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。

此入口依赖本机个人目录；跨机器交付需另行导出所需维护源和引用。

## 遮住出怪设施内部

需要黑色门腔、隐藏刷怪细节和低成本雾幕时，读取 [黑色遮蔽与雾幕](references/transparency-and-visibility.md#出怪门内的黑色遮蔽与廉价雾幕)。持续遮挡与雾气装饰分别保留，远距关闭装饰不能露出内部。

## 龙息体积喷流

持续喷火、三维温度场、喷射坐标、主体过白和旧 Sprite 方案归档时，读取 [龙息体积喷流制作与失败经验](references/dragon-volume-production.md)。

- [武器附着火焰与脚下火环](references/attached-flame-and-fire-ring.md)：2026-10-18 本轮实现经验与恢复边界，按问题读取；不授权自动测试。

## 地面火场与撞击

陨星式爆燃、火环或火焰高度整齐、碎石抢主体时，读取 [地面火场与撞击层次](references/meteor-ground-impact.md)，保留当前制作供体与服务器阶段时钟。
