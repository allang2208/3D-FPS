---
name: ue5-auto-assistant
description: UE5 任务入口。用户未指定技能或涉及引擎模块时，选择对应领域流程；已有明确领域技能时直接使用，不重复路由。
---

# UE5 任务入口

遵守用户全局规则：默认后台制作、必要构建与落盘；不主动测试或跨对话协调。构建和资产操作按需读取[后台开发与接入规则](references/editor-open-development.md)，同一任务不重复读取。 原因：制作授权不包含额外运行或验收，交付应保留未测试的实际状态。

按实际目标选择一个主要技能，跨领域时补充确有必要的参考，不向用户输出路由 JSON 或要求用户记住技能名。 原因：用户给的是任务目标，内部技能路由应减少操作负担而非成为额外输入格式。

| 任务 | 技能 |
| --- | --- |
| 枪械、近战、枪匠、ADS | [武器](../ue5-weapon-workflow/SKILL.md) |
| 第一人称动作、抓握、手套衣袖 | [手臂动画](../ue5-fps-arms-animation/SKILL.md) |
| 玩家服装、上衣裤装衔接、扎腰与裤靴搭配 | [服装](../ue5-clothing-workflow/SKILL.md) |
| 怪物、骨架、AI、布娃娃 | [怪物](../ue5-monster-workflow/SKILL.md) |
| 生成或制作模型、精确机械接口 | [模型制作](../asset-model-workflow/SKILL.md) |
| 药水、材料、包装、图标 | [物品](../ue5-item-asset-workflow/SKILL.md) |
| 技能、施法、修炼 | [魔法](../ue5-skill-magic-workflow/SKILL.md) |
| 烟火、水花、毒血、冷雾 | [流体特效](../ue5-fluid-vfx-workflow/SKILL.md) |
| 天气与昼夜 | [天气](../ue5-weather-workflow/SKILL.md) |
| 冷钢 UI、UMG、Slate | [UI](../ue5-ui-umg-slate/SKILL.md) |
| C++ 玩法 / Blueprint 图 | [C++](../ue5-cpp-gameplay/SKILL.md) / [蓝图](../ue5-blueprint-workflow/SKILL.md) |
| 存档、网络复制 | [存档与复制](../ue5-save-load-replication/SKILL.md) |
| 拾取、生成、交互 | [世界交互](../ue5-world-interaction/SKILL.md) |
| PCG、建筑、地面 | [建筑](../ue5-pcg-building/SKILL.md) |
| 模块边界 / 故障排查 / 性能与打包 | [架构](../ue5-architecture/SKILL.md) / [调试](../ue5-debug-validation/SKILL.md) / [性能](../ue5-performance-packaging/SKILL.md) |

- 需要按 RenderCore、AIModule、AssetRegistry 等模块精确查找时，读取[模块映射规则](../ue5-module-router/ROUTING.md)和其中 CSV；没有模块名时无需加载整表。 原因：「模块映射规则」记录该任务的专属入口和边界，按主题引用可避免另写一套相互冲突的步骤。
- FPSGAME 功能涉及 HUD、属性读取、灯光、模型或纹理加载时，读取[性能开发约束](../ue5-performance-packaging/references/fpsgame-performance-development.md)。这不授权额外采样或测试。
- 专用工具能完成任务就直接使用；只有动态依赖、批处理或专用工具不足时才组合脚本。工具名和参数以当次可用 schema 为准。

维护技能或引用历史参数时，读取[维护源与历史资料约定](references/skill-maintenance.md)。

修改 FPSGAME 共用 `player_body.json`，或恢复/发布第三人称动作、身体和头部装备时，读取[共享玩家配置与发布](references/shared-body-config-publication.md)。保留其他动作入口，区分本地接入与 Git 推送。 原因：重建需要真实的上游输入及先后顺序，仅保留最终输出无法恢复可编辑制作链。

- 涉及编辑器内脚本的写法与排障纪律（2026-09-23）时，读取[编辑器内脚本的写法与排障纪律（2026-09-23）](references/editor-script-discipline.md)。

- FPSGAME 的 SSD、DDC、Content 联接与恢复留存整理，读取 [项目存储与目录联接](references/project-storage-junctions.md)。
