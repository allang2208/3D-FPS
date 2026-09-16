# Vibe3D 插件登记（2026-09-15）

用户从 Fab 下载的编辑器插件，用于把 Modeling Mode 的算子作为 AI 工具集挂到引擎原生 MCP 端点。本文记录来源、许可、兼容性证据与启用状态；不构成运行验收。

## 来源与许可

| 项 | 内容 |
| --- | --- |
| 名称 / 版本 | Vibe3D，`VersionName 1.0`（`Version 1`） |
| 作者 | Buckley Builds LLC，<https://www.vibeue.com> |
| 文档 | <https://www.vibeue.com/vibe3d>；支持 <https://www.vibeue.com/support> |
| 许可 | 版权声明为 "Copyright Buckley Builds LLC 2026. All rights reserved."——第三方闭源授权，非开源 |
| 安装位置 | `E:\Program Files (x86)\UE_5.8\Engine\Plugins\Marketplace\Vibe3Dd7b2fe90b7d0V1\`（引擎级 Marketplace，位于仓库之外，不进入版本管理） |
| Fab 库条目 | `D:\FPS3D\VaultCache\FabLibrary\Vibe3D-2755c4ae`（仅 manifest） |

## 兼容性证据

| 检查项 | 结果 |
| --- | --- |
| `.uplugin` EngineVersion | `5.8.0`；本机引擎 5.8.2（Changelist 56702186） |
| 模块 | 单模块 `Vibe3D`，**Type = Editor**，LoadingPhase = Default，平台 Win64/Linux/Mac |
| 预编译二进制 | `Binaries/Win64/UnrealEditor-Vibe3D.dll`（790 KB）随包提供 |
| BuildId 匹配 | 插件 `UnrealEditor.modules` 的 `BuildId = 55116800`，等于引擎 `Build.version` 的 `CompatibleChangelist = 55116800`，故免重编译 |
| 依赖插件 | GeometryScripting、GeometryProcessing、MeshModelingToolset、ToolsetRegistry、PythonScriptPlugin、EditorScriptingUtilities（均为引擎自带，由插件声明自动启用） |
| 运行影响 | Editor-only，不参与打包与 Cook |

## 它提供什么

- 工具集：`Vibe3D.ModelingService`，挂在引擎原生 MCP 端点（与 `ModelContextProtocol`、`AllToolsets` 同一服务）。源码头文件 `Public/Vibe3D/UModelingService.h` 中共 **121 个 UFUNCTION**。
- 能力覆盖：基础体与放样（AppendBox / AppendSphere / AppendLoft / AppendSweepPolyline / AppendCurvedStairs…）、布尔（Boolean）、多边形编辑（BevelPolygroups / ComputePolygroups / InsetFaces / ExtrudeFaces）、变形（Bend…）、UV（AutoUV）、烘焙（BakeTextures / BakeTextureTransfer）、绑骨（BindSelectionToBone）、碰撞（ConvexDecomposition）、LOD、保存为静态网格。
- 网格以整数句柄形式驻留编辑器会话，包装 `UDynamicMesh`；`get_dynamic_mesh(handle)` 可转交任意 `GeometryScript_*`。
- 附带 skill `modeling`（`Content/Skills/modeling/SKILL.md`，28.8 KB），编辑器启动时由 `Content/Python/init_unreal.py` 注册为原生 AgentSkill，可通过 `ToolsetRegistry.AgentSkillToolset` 读取；控制台 `Vibe3D.ReloadSkills` 重载。
- Python 等价入口：`unreal.ModelingService.<snake_case>(...)`。

## 启用状态

已在 `FPSGAME.uproject` 的 `Plugins` 数组中加入：

```json
{ "Name": "Vibe3D", "Enabled": true }
```

JSON 校验通过（13 个插件条目）。因为改动 `.uproject`，**需要重启编辑器才会加载**；引擎级插件本身对所有工程可见。

## 注意事项

- 控制台命令 `Vibe3D.GenerateAgentConfig [Codex|…]` 会**写入工程文件**：把一段 `<!-- BEGIN Vibe3D -->…<!-- END Vibe3D -->` 块写进 `AGENTS.md`（或 `CLAUDE.md` / `GEMINI.md`）。本工程有既定的 AGENTS.md 规则且存在并行会话，**尚未执行该命令**。
- 自动化测试 `Automation RunTests Vibe3D.Modeling` 要求编辑器处于前台交互帧率，按用户规则未运行。
- 插件随包提供源码；若日后升级引擎小版本导致 BuildId 不再匹配，需要本地重编译。

## 待完成

重启编辑器后，用 `Tools/AssetPipeline/mcp_call_codex.ps1` 执行 `list_toolsets`，确认出现 `Vibe3D.ModelingService`，再以 `describe_toolset` 拉取工具清单与参数，作为实际挂载证据。当前本机编辑器未运行、8000 端口未监听，该验证尚未进行。
