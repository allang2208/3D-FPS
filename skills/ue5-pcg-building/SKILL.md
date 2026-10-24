---
name: ue5-pcg-building
description: UE5.6-UE5.8 PCG generation and runtime-heightfield ground workflow for modular buildings, blockouts, facade rules, runtime generation, and layered terrain ground materials. Use when requests involve Procedural Content Generation (PCG), Shape Grammar, lot-based building spawn, deterministic random seeds, density/filter pipelines, converting designer constraints into reusable PCG graphs, or the detail/layering of a streamed non-Landscape ground surface.
---

# 本机维护源入口

本机共用流程统一读取[ue5-pcg-building](C:/Users/allan/.codex/skills/ue5-pcg-building/SKILL.md)，不要叠加旧镜像流程。

工程专属规则以当前 AGENTS.md、WORKFLOW.md 和本次用户要求为准。维护源不可用或需要查找未合入的工程经验时，读取[整理前工程资料](LOCAL-HISTORY.md)及原 references；其中历史测试与协调条款不构成执行授权。

此入口依赖本机个人目录；跨机器交付需另行导出所需维护源和引用。

## 场景光源与最低照明

制作或调整室内灯具、吊灯方向、廊下和暗角照明时，读取 [灯具与照明层次标准](references/fixture-lighting-standard.md)。向下灯不得向上直射天花板；保留已认可主灯，按实际楼层补光。

## 固定观景点的城市远景与栏杆

公寓海湾建筑分层、办公条形窗灯、动态广告/水面反射、侧挡板替换玻璃栏杆及增量重建，读取 [远景与栏杆制作](references/layered-harbor-and-balcony.md)。保留当前天气和共享资产，版本编号不作为退役依据。
