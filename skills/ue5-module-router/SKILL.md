---
name: ue5-module-router
description: UE5.6-UE5.8 module-name inventory for this project. Maps UE module names (RenderCore, AIModule, AssetRegistry) and Build.cs paths to the area that owns them. The authoritative skill list and routing live in the repository-root AGENTS.md; this table is a lookup index, not a routing authority.
---

## UE5 默认开发方式（用户确定，2026-09-23）

后台优先：不主动启动 UE 编辑器；不主动检查、测试、启动 PIE、截图或验收渲染；不向其他对话/任务发协调消息。完整规则与「按改动选执行方式」表见仓库根 `AGENTS.md` 和 [后台开发与编辑器使用条件](../ue5-auto-assistant/references/editor-open-development.md)。

# 用途

把 UE 模块名 / `Build.cs` 路径解析到本项目负责该领域的技能。

**技能清单与分流以仓库根 `AGENTS.md` 为准**，本表只做「模块名 → 领域」查表。命中本表后仍按 `AGENTS.md` 点名的技能进入。

# 查表

- 表：`references/ue5-module-routing-table-final.csv`（755 行）。
  该表约 46k token，**必须用 grep/筛选查，不要整篇读进上下文**。
- 列：`ModuleName, Layer, TargetSkill, SecondarySkill, RouteConfidence, RouteReason, PrimaryAliases, ExcludeTerms, RelativeBuildCsPath`
- 匹配优先级：① `ModuleName` 精确匹配 ② `RelativeBuildCsPath` 段匹配 ③ `PrimaryAliases` 关键词重叠 ④ 领域兜底。
- `ExcludeTerms` 命中即判为不相关（例如 `email`、`translation`、`copywriting` 对 `AITestSuite`）。

# 表内已知失效（2026-09-23 核对）

| `TargetSkill` | 行数 | 状态 |
| --- | ---: | --- |
| `ue5-architecture` | 532 | **技能不存在** |
| `ue5-save-load-replication` | 40 | **技能不存在** |
| `ue5-cpp-gameplay`、`ue5-performance-packaging`、`ue5-ui-umg-slate`、`ue5-world-interaction` | 183 | 存在 |

命中前两者时**不要跳转**——按 `AGENTS.md` 的技能清单人工判断，模块边界/设计类问题落到 `ue5-cpp-gameplay`。
重生成脚本引用的 `ue5-architecture/scripts/generate_module_index_v2.py` 同样不存在，该路径已失效。

# 工具口径

`references/routing-policy.md` 里的「Tool Priority Matrix」描述的是**另一套 MCP 工具**
（`blueprint_feature_build`、`spawn_actor`、`character_data`、`execute_script`、`task_*`），**不是本项目的桥**。

本项目实际走 `Tools/AssetPipeline/mcp_call_codex.ps1`：工具集形如 `Vibe3D.ModelingService`、
`EditorToolset.EditorAppToolset`、`LiveCodingToolset.LiveCodingToolset`；`call_tool` 用
`toolset_name` + 裸 `tool_name`；编辑器内 Python 走 `-PythonScript`。**以 `-ListToolsets` 的实时结果为准**，
不要按上述旧矩阵去找不存在的工具。

# 维护

本表是本机 UE 源码的模块清单，不是项目资产。技能改名或新增时同步更新上表；
不要依赖 `*_draft.deprecated.csv`（2026-09-23 已移除）。
