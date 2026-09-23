---
name: ue5-auto-assistant
description: UE5.6-UE5.8 automatic assistant entry for beginners. Use when users ask Unreal questions without naming a specific skill. Auto-route to the most precise UE5 skill and recommend dedicated MCP tools.
---

## UE5 默认开发方式（用户确定，2026-09-23）

后台优先：不主动启动 UE 编辑器；不主动检查、测试、启动 PIE、截图或验收渲染；不向其他对话/任务发协调消息。完整规则与「按改动选执行方式」表见仓库根 `AGENTS.md` 和 [后台开发与编辑器使用条件](references/editor-open-development.md)。

- **MCP 效率约定（2026-09-20）**：复用本任务已读 schema；已知操作批量执行，动态依赖优先编辑器内脚本；桥接输出使用唯一新 OutputFile 配合 MaxOutputChars 3000，按需读取完整结果。具体参数、失败边界与兼容性见 [开发规则](references/editor-open-development.md#mcp-效率与-token-约定2026-09-20)。

# Quick Start
- Treat this as the default entry for UE5.6-UE5.8 requests.
- Parse user intent first without requiring module names.
- Route to `ue5-module-router` when module-level precision is needed.

# Workflow
- Detect request type: Blueprint, C++, UI, save/load, networking, world interaction, PCG/procedural generation, debugging, performance, packaging.
- If module names appear, delegate routing to `ue5-module-router`.
- If module names do not appear, route by intent:
  - Monster generation, topology, custom rig, creature animation, ragdoll or monster combat/spawning -> `ue5-monster-workflow`
  - First-person arms, grip, reload, equip, charge, slap or MAT animation -> `ue5-fps-arms-animation`
  - Weapon import, gunsmith, attachments, ADS, action audio or weapon integration -> `ue5-weapon-workflow`
  - Blueprint -> `ue5-blueprint-workflow`
  - C++ gameplay -> `ue5-cpp-gameplay`
  - UI/UMG/Slate -> `ue5-ui-umg-slate`
  - save/load/replication -> `ue5-save-load-replication`
  - pickup/spawner/world interaction -> `ue5-world-interaction`
  - PCG/procedural building/shape grammar -> `ue5-pcg-building`
  - perf/packaging -> `ue5-performance-packaging`
  - debugging/validation -> `ue5-debug-validation`
  - architecture/refactor -> `ue5-architecture`
- Return one primary skill and optional secondary skill for cross-domain requests.
- Return routing payload fields:
  - `primary_skill`
  - `secondary_skill`
  - `recommended_mcp_tools[]`
  - `route_confidence`
  - `route_reason`

# Natural Language To Skill And Tools
- Blueprint requests:
  - target skill: `ue5-blueprint-workflow`
  - recommended tools: `blueprint_feature_build`, `blueprint_modify`, `blueprint_query`
- C++ gameplay/system requests:
  - target skill: `ue5-cpp-gameplay`
  - recommended tools: `blueprint_query`, `asset_search`, `get_output_log`
- UI/UMG/Slate requests:
  - target skill: `ue5-ui-umg-slate`
  - recommended tools: `blueprint_query`, `blueprint_modify`, `capture_viewport`
- Save/load/replication requests:
  - target skill: `ue5-save-load-replication`
  - recommended tools: `character_data`, `blueprint_query`, `get_output_log`
- World interaction/pickup/spawner requests:
  - target skill: `ue5-world-interaction`
  - recommended tools: `spawn_actor`, `get_level_actors`, `set_property`, `move_actor`
- PCG/procedural building requests:
  - target skill: `ue5-pcg-building`
  - recommended tools: `asset_search`, `blueprint_query`, `get_output_log`, `capture_viewport`
- Performance/packaging requests:
  - target skill: `ue5-performance-packaging`
  - recommended tools: `run_console_command`, `get_output_log`, `capture_viewport`, `open_level`
- Debug/validation requests:
  - target skill: `ue5-debug-validation`
  - recommended tools: `get_output_log`, `asset_search`, `blueprint_query`, `task_list`
- Architecture/module-boundary requests:
  - target skill: `ue5-architecture`
  - recommended tools: `asset_search`, `asset_dependencies`, `asset_referencers`

# Constraints
- Do not require users to know skill names.
- Prefer deterministic routing with explicit reason.
- Keep fallback behavior explicit when confidence is low.
- Prefer dedicated MCP tools before `execute_script`.

# Failure Handling
- If intent is ambiguous, return top 2 route candidates and ask one short clarification.
- If request spans many systems, split into staged route steps.
- Clarification template:
  - `Quick check: do you want A(<candidate_1>) or B(<candidate_2>)?`
  - ask once, then continue.

# Escalation
- Escalate when query depends on plugin/engine source outside indexed scope.
- Escalate when org-level coding standards are required but not available in repo.

## Vibe3D 模型任务分流（2026-09-19）

规则几何建模、建筑模块/道具本体、机械零件及网格后处理 → [asset-model-workflow](../asset-model-workflow/SKILL.md) 的 [Vibe3D 分支](../asset-model-workflow/references/vibe3d-workflow.md)，推荐工具集 Vibe3D.ModelingService。PCG 排布仍走 ue5-pcg-building；动画、UI、玩法与存档保留各自工具集。实际调用前按需读取当前 schema，历史连接成功不作为在线证明。默认不追加连接测试、建模样例或验收。

## 编辑器内脚本纪律（2026-09-23）

要写"改关卡／生成 actor／批量改组件"的编辑器内脚本时，先读
[编辑器内脚本的写法与排障纪律](references/editor-script-discipline.md)。
覆盖：护栏顺序（world/PIE/目标地图/脏包/锚点）、**安全切图并切回**的既有做法、
先探 API 再写批次、会静默失败的 setter 必须读回、给自产 actor 打标签的幂等约定，
以及桥的两个坑（6776 按需监听；不要用变量接收桥的输出）。
