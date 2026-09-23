# 停 PIE 时触发 GPU 崩溃（2026-09-22 22:31:35）

## 现场

本次会话为让"枪械详细介绍"的显示文案同步跑起来，用 MCP 的
`EditorToolset.EditorAppToolset.StartPIE` 启动了一次 PIE（`DayNight_Lighting`），
迁移成功写盘后，用 `StopPIE` 停止会话时编辑器崩溃。

崩溃转储：`Saved/Crashes/UECC-Windows-70952E054E8CDB40239453846792D44E_0000/`，
已归档到本目录 `trash/` 之外的原位保留，另见本文件所在诊断目录。

## 证据与归因

| 项 | 值 |
| --- | --- |
| `ErrorMessage` | `GPU Crash dump Triggered` |
| `CrashType` | `GPUCrash` |
| GPU 转储 | `D3D12.0.2026.09.22-22.31.31.nv-gpudmp` |
| 崩溃时刻 | 22:31:35（GPU 转储 22:31:31） |
| 调用栈 | 全部为 `UnrealEditor_D3D12RHI` ×5，然后是 `UnrealEditor_Core`、`kernel32`、`ntdll` |

调用栈中**没有任何 FPSGAME 模块帧**，异常点是 D3D12 RHI 的 GPU 崩溃路径。
本次改动是存档 JSON 的字符串同步（`ColdSteelProfileRuntime.cpp`）与物品文案数据，
不涉及渲染、材质或 RHI 资源，因此**不把这次崩溃归因于本次改动**。

同日前例可对照：`Saved/Diagnostics/MeleeRuneCrash20260922/` 记录过另一起
热补丁相关的访问违例；本机在 PIE 启停与 GPU 负载下出现崩溃并非首次。
本次没有 GPU 转储分析工具可用，**不声称已定位到具体驱动或引擎缺陷**。

## 数据完整性

崩溃发生在迁移完成之后，存档未受影响：

| 文件 | 时间 | 新文案 | 旧文案 |
| --- | --- | --- | --- |
| `ColdSteelPlayer_A.sav` | 22:31:20（135203 → 崩溃前写入） | M4A1 1 处、PKM 1 处 | 0 |
| `ColdSteelPlayer_B.sav` | 22:31:20 | M4A1 1 处、PKM 1 处 | 0 |

两槽均已是新文案，A/B 校验事务的两份文件完整。

## 未做

- 没有重新启动编辑器复现，也没有分析 minidump 的 GPU 侧内容。
- 没有为此关闭或调整任何渲染设置。
- 未把这次崩溃写成"已修复"：它没有可复现的最小条件，也没有定位到代码缺陷。

## 后续对照（同日 22:37）

同一会话稍后再走一次相同路径（重启编辑器 → MCP `StartPIE` → 迁移写盘 → MCP `StopPIE`），
**没有再出现崩溃**：编辑器进程存活，`Saved/Crashes` 未产生新目录。
因此本次 GPU 崩溃**不是确定性可复现的**，与"停 PIE"这一步没有稳定因果关系。
既不改写前述归因，也不把它当作已解决——只记录一次成功对照。
