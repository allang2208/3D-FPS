# Beginner Smoke Prompts (UE5.6-UE5.8 MCP + Skill)

这些提示仅在用户明确要求检查技能分流时使用，不在普通任务开始时执行。原因：案例需要实际发起另一组任务，不能因文档列出提示就自动测试。

## How To Use
- 使用用户指定的检查环境，不自动新建其他对话。原因：测试环境和对话创建分别需要对应的用户请求。
- 一次采用一个指定案例。原因：混合多个意图无法判断分流是否来自该案例。
- 检查自然语言分流时不在提示中指定技能名。原因：预先写出目标技能会绕过本来要观察的意图识别。
- 只记录本次指定案例的分流和实际可用工具。原因：历史工具名称不保证仍被当前桥暴露。

## Case 1: Save/Load
Prompt: `Inventory is empty after load. Where should I debug first?`
Expected:
- primary skill: `ue5-save-load-replication`
- recommended tools include `get_output_log`, `blueprint_query`

## Case 2: Module-Specific
Prompt: `How do I debug material compile stalls in RenderCore?`
Expected:
- routed by `ue5-auto-assistant` using the module mapping reference
- high confidence when exact module match exists

## Case 3: Blueprint Hotkey
Prompt: `In Blueprint, press key 2 to jump and print a log. How do I wire this?`
Expected:
- primary skill: `ue5-blueprint-workflow`
- fast-path for keyboard input （按当前工具 schema 选择可用输入节点操作）

## Case 4: World Interaction
Prompt: `I want pickup items that auto-collect when player enters range.`
Expected:
- primary skill: `ue5-world-interaction`
- tools include `spawn_actor`, `get_level_actors`, `set_property`

## Case 5: UI
Prompt: `My tooltip is clipped at viewport edges. How should I clamp it?`
Expected:
- primary skill: `ue5-ui-umg-slate`
- tools include `blueprint_query`, `blueprint_modify`, `capture_viewport`

## Case 6: Performance/Packaging
Prompt: `Give me a pre-package checklist and profiling order.`
Expected:
- primary skill: `ue5-performance-packaging`
- tools include `run_console_command`, `get_output_log`

## Case 7: PCG Building
Prompt: `Generate deterministic modular buildings from lot splines with Shape Grammar.`
Expected:
- primary skill: `ue5-pcg-building`
- tools include `asset_search`, `blueprint_query`, `get_output_log`

## Pass Criteria
- correct routing for each prompt
- 工具选择依据当前 schema 及操作依赖；不强制优先某个旧工具名。原因：批处理脚本与专用工具各自适用于不同依赖关系。
- 只有缺失信息影响执行时才澄清。原因：已有上下文足够时不应把置信度标签变成固定提问步骤。
