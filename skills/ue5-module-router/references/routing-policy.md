# Routing Policy (UE5.6-UE5.8)

> **2026-09-23 更正：本文件下方的「Tool Priority Matrix」描述的是另一套 MCP 工具**
> （`blueprint_feature_build`、`spawn_actor`、`character_data`、`execute_script`、`task_*`），
> **不是本项目的桥**。本项目实际走 `Tools/AssetPipeline/mcp_call_codex.ps1`：工具集形如
> `Vibe3D.ModelingService`、`EditorToolset.EditorAppToolset`、`LiveCodingToolset.LiveCodingToolset`；
> `call_tool` 用 `toolset_name` + 裸 `tool_name`；编辑器内 Python 走 `-PythonScript`。
> 工具可用性一律以 `-ListToolsets` 的实时结果为准。
>
> 技能分流以仓库根 `AGENTS.md` 为准；本目录只做「模块名 → 领域」查表。
> 表内 `TargetSkill` 为 `ue5-architecture`（532 行）与 `ue5-save-load-replication`（40 行）的行已失效，
> 不要按它们跳转。

## Priority Order
1. Exact module name match in routing table.
2. Exact Build.cs path segment match.
3. Alias/keyword match from routing table.
4. Domain fallback from module index v2.

## Confidence Levels
- High: `route_reason=module_override` or exact module hit with stable mapping.
- Medium: `route_reason=domain_mapping` with non-`General` domain.
- Low: fallback on `General` domain + weak alias evidence.

## Output Contract
- `primary_skill`
- `secondary_skill` (if present)
- `recommended_mcp_tools[]`
- `matched_modules[]`
- `route_reason`
- `route_confidence`

## Tool Priority Matrix
- Blueprint requests:
  - Prefer: `blueprint_feature_build`, `blueprint_modify`, `blueprint_query`
  - Then: `enhanced_input`, `get_output_log`
  - Last resort: `execute_script`
- World interaction requests:
  - Prefer: `spawn_actor`, `get_level_actors`, `set_property`, `move_actor`, `delete_actors`, `open_level`
  - Then: `capture_viewport`, `get_output_log`
  - Last resort: `execute_script`
- Save/load/network requests:
  - Prefer: `character_data`, `blueprint_query`, `blueprint_modify`, `asset`, `asset_search`
  - Then: `get_output_log`, `task_*`
  - Last resort: `execute_script`
- Performance/packaging requests:
  - Prefer: `run_console_command`, `get_output_log`, `capture_viewport`, `open_level`, `asset_dependencies`, `asset_referencers`
  - Then: `task_*`
  - Last resort: `execute_script`
- Debug/validation requests:
  - Prefer: `get_output_log`, `asset_search`, `blueprint_query`, `get_level_actors`, `task_list`, `task_status`, `task_result`
  - Then: `capture_viewport`
  - Last resort: `execute_script`

## execute_script Fallback Conditions
Use `execute_script` only when all conditions are met:
1. No dedicated tool supports the required operation.
2. The request cannot be decomposed into existing MCP tool calls.
3. The reason is explicitly stated in the response.
4. Script scope is minimal and reversible where possible.
