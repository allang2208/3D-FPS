# UE Python 远程执行通道（2026-09-15）

把引擎的 Python 远程执行打开，作为比"每次工具调用走一次 HTTP 桥"更快的通道：一次连接执行**整段脚本**，适合多步建模流程（建体 → 布尔 → UV → 烘焙 → 碰撞 → 存盘）。

## 改动

`Config/DefaultEngine.ini`：

```ini
[/Script/PythonScriptPlugin.PythonScriptPluginSettings]
bRemoteExecution=True
```

该设置带 `ConfigRestartRequired`，**引擎下一次启动才生效**。

默认端点（未改动，均为本机回环）：

| 项 | 默认值 |
| --- | --- |
| 组播发现 | `239.0.0.1:6766` |
| 组播绑定地址 | `127.0.0.1` |
| 命令端点 | `127.0.0.1:6776` |

## 安全边界

远程执行会在编辑器内开放一个**本地 TCP 执行入口**：任何能在本机执行代码的进程都可以借此在编辑器上下文里运行 Python（包括读写资产、执行控制台命令）。默认只绑 `127.0.0.1`，不对局域网开放。按用户 2026-09-15 的决定启用；如需收紧，可在 Project Settings → Plugins → Python → Remote Execution 临时关闭，或停止编辑器时即自动关闭。

## 客户端

`Tools/AssetPipeline/ue_python_exec.py`（本工程自建）。它复用引擎自带的官方客户端
`Engine/Plugins/Experimental/PythonScriptPlugin/Content/Python/remote_execution.py`（纯标准库，不依赖 UE 的 Python 环境），因此不需要自己实现发现/报文协议。用本机 CPython 3.11 运行。

```powershell
# 发现可连接的编辑器节点（列出 node_id / 引擎版本 / 工程 / 命令端点）
python Tools/AssetPipeline/ue_python_exec.py --list

# 在编辑器里执行一个脚本文件（可多语句）
python Tools/AssetPipeline/ue_python_exec.py --script path/to/script.py

# 执行单条语句 / 求值一个表达式
python Tools/AssetPipeline/ue_python_exec.py --statement "import unreal; print(unreal.SystemLibrary.get_engine_version())"
python Tools/AssetPipeline/ue_python_exec.py --eval "1+1"
```

多节点时按 `project_name` 含 `FPSGAME` 优先选择，否则要求 `--node` 指定。退出码：0 成功、1 远端执行失败、2 找不到官方客户端、3 未发现节点、4 节点不唯一。

## 与 MCP 桥的分工

| 场景 | 通道 |
| --- | --- |
| 单次工具集调用、列工具集、读引擎日志 | `Tools/AssetPipeline/mcp_call_codex.ps1`（MCP over HTTP，v2 支持会话复用与批量） |
| 多步建模、批量生成、需要在编辑器上下文里跑整段逻辑 | 本文的远程执行通道 |

两者可并存：MCP 负责"按工具粒度操作"，远程执行负责"按任务粒度跑脚本"。

## 状态

- 配置已改；客户端已通过 AST 语法检查。
- `--list` 冒烟：编辑器未运行时正确报"没有发现可连接的编辑器节点"并返回退出码 3——说明客户端加载、参数解析与发现循环都走到了。
- **尚未做**：编辑器重启后的真实连接与执行验证（编辑器当前未运行），以及 Vibe3D 建模脚本的实跑。
