**用户规则（2026-09-20）：禁止主动向其他对话/任务发送协调消息。** 不调用 send_message_to_thread 或跨任务消息工具询问占用、请求让位、通知释放、协商编译/重启；不通过轮询其他对话或共享留言板变相协调。接入等待交由桥的批次互斥处理，期间继续独立制作。真实文件/资产归属冲突或无法安全执行的编译/重启，保留现场，仅在当前对话向用户简要说明阻塞；不联系其他对话。此规则覆盖旧文中的“定向协调/集中协调”等要求；只有用户明确另行要求发送指定消息时才执行。

# UE5 后台开发与编辑器使用条件（用户确定，2026-09-23）

**默认后台制作、编译与落盘（用户确定，2026-09-23）。** 不主动启动 UE 编辑器。源码、配置、文档、外部模型/贴图/动画，以及可在后台完成的构建、导入和保存，优先通过文件、命令行或适用的 commandlet 完成。只有用户明确要求打开，或必要操作确实无法在后台完成、只能在编辑器中进行时，才打开 UE；仅剩必要编辑器操作时使用短批次接入。

## 默认后台执行与打开条件

- 源码、配置、文档、建模/动画源文件和导出脚本直接在编辑器外完成。C++ 优先通过 UBT/Build.bat 完成必要的常规 Editor/Game 目标构建与二进制落盘；Editor 构建目标不表示需要启动编辑器。
- 导入、重导入、材质/蓝图/地图/动画资产制作与保存，优先使用适用的后台脚本或无界面 commandlet。已有脚本调用 LevelEditorSubsystem 等交互编辑器 API，不足以证明操作只能在编辑器中完成；先判断能否使用对应后台资产/包接口。只把脚本写好但未执行，仍属于待接入。
- 只有用户明确要求打开 UE，或已确定具体必要操作没有适用的后台方式、只能在交互编辑器中完成时，才打开。后者先在当前对话说明具体操作及后台方式不能完成的原因，然后按已有授权执行，不额外重复请示。
- 不为开始任务、连接 MCP、触发 Live Coding、查看编译结果或习惯性收尾而打开 UE。后台构建和保存完成后直接交付，不自动打开、重启、启动 PIE 或运行游戏。
- 已经运行的编辑器不因本规则主动关闭。要修改其已加载资产，沿用当前进程与 MCP 批次互斥；不要另起编辑器或 commandlet 覆盖同一包。必要关闭仍保护未保存内容，完成后台构建后默认保持关闭。
- 本节覆盖旧流程中无条件“打开编辑器”“构建后重新打开”“编辑器内优先”的条款。历史 API、资产约束及来源记录保留；后台执行同样遵守不主动测试、预览或验收的用户规则。

## 并行制作与短时接入（2026-09-20）

本节替代旧版“全程 MCP 制作”和逐条询问会话占用的默认要求。允许多会话开发，不表示一个编辑器能并行执行工具。

1. 制作开始按源码文件、源素材目录及目标资产划分归属；已有明确分工不反复确认。源码、外部模型、贴图、动画源文件、生成脚本和导入参数独立制作。不要把彼此独立的准备工作放进编辑器接入窗口。
2. 本任务准备好一段可执行的修改/导入/保存操作后，提交一次 BatchFile；依赖动态返回值的操作尽量合成一次编辑器内脚本调用。批次写明目标路径，不依赖其他任务可能改变的当前选择。业务错误在脚本内按工具契约停止。
3. 所有本工作流的编辑器调用（含只读）统一通过 Tools/AssetPipeline/mcp_call_codex.ps1。桥从连接前到整批结束持有同一 Windows 登录会话、同一端口的命名互斥锁。批次之间可以轮换；单次脚本内不得递归调用该桥。各任务不得绕过桥直接 HTTP 请求来插队。
4. QueueWaitSeconds 默认 60 秒；竞争时只向 stderr 提示一次，然后工具内部等待，不唤醒模型反复协调。超时退出码 75，本次没有发送请求；保留批次，继续独立制作，稍后再提交一次，不循环快速重试。长等待可在后台 exec 会话运行，但轮询不应成为主要工作。互斥锁不保证 FIFO 公平顺序。
5. 一个批次完成必要操作和保存即释放，不持锁做外部模型生成、长时间思考或等待用户。耗时制作按可保存的阶段拆分；必须在 UE 内完成的 Vibe3D 制作仍可占用接入窗口。其他会话继续编辑器外工作。
6. 锁只协调使用此桥的调用，不隔离用户手动操作、旧桥、其他客户端、外部 UBT 或已经异步启动的引擎任务。工具返回“已启动”不代表完成：同一批次必须用工具支持的等待/完成接口结束操作后再保存释放；没有此能力时，针对该长任务安排独占接入，不宣称锁覆盖其完整生命周期。异常退出后不假定 UE 已停止操作，不盲重放写入。
7. 同一文件/资产归属冲突、编辑器手动改动、共享原生编译和必要重启受阻时，保留现场并仅向当前用户报告；不得联系其他对话。锁不能自动合并改动。Live Coding/UBT 与重启集中在需要它们的接入阶段；不能让所有任务每改几行就要求编译或重启。
8. 保留会话复用、schema 按需读取、输出限长与完整结果落盘。一次接入返回资产路径、保存结果、必要 handle 和错误；不汇报每次锁等待、不逐条读取其他对话。未接入的源文件不能称为游戏已完成集成；无其他可做工作时如实报告接入仍待完成。

并行制作与短批次互斥继续适用，但接入前先遵守上方后台优先和打开条件。用户未明确要求时不运行 PIE、探针、截图或回归。

## 按改动选择执行方式

| 改动 | 默认方式 | 编辑器状态 |
| --- | --- | --- |
| 文档、配置、脚本与外部模型/动画源文件 | 文件编辑、后台制作与导出 | 不启动 |
| 现有 C++ 函数内部逻辑 | 后台常规 Editor/Game 目标构建；已有会话中才按需使用 Live Coding | 不为编译启动，完成后不自动打开 |
| 大幅修改类/结构体布局、继承、属性类型、默认组件结构 | 后台常规 Editor 目标构建 | 涉及已加载 DLL/旧实例时按必要关闭规则处理，构建后默认保持关闭 |
| FPSGAME 带资产引用的 USTRUCT 变化；新增 C++ 类即将写进关卡或资产 | 先后台常规构建基础 DLL，再用适用的后台接口编辑/保存依赖资产 | 只有后续必要资产操作确实只能在编辑器完成时才打开 |
| 关卡、材质、蓝图、UMG、动画资产、导入/重导入 | 优先后台资产脚本/commandlet；已加载包在其当前编辑器内处理 | 不把资产类别本身视为启动条件 |
| 几何、UV、烘焙、碰撞、LOD、模型保存 | 优先适用的后台建模工具；已有编辑器可使用 Vibe3D | 指定或必须使用的编辑器能力无法后台执行时才打开 |
| 完整构建要覆盖已加载 DLL；不可动态重载的原生模块更换；引擎切换 | 正常退出占用二进制的编辑器后，后台构建/更新 | 不自动重新打开 |

“常规 Editor 目标构建”可以由 UBT 增量完成，不意味着每次 Clean/Rebuild。纯文档、脚本源文件或外部模型源文件的编辑，本身不要求连接或关闭 UE。

## 编辑器内制作

- MCP 服务和 Vibe3D 会话位于编辑器进程内；仅在编辑器已经运行，或符合上方打开条件后使用。需要实际操作时按需读取当前工具 schema 和目标资料；不要为每个任务追加连接测试、示例建模或全项目扫描。历史连接成功不表示当前在线。
- 规则几何、建筑模块/机械件和模型后处理走 [Vibe3D 分支](../../asset-model-workflow/references/vibe3d-workflow.md)。蓝图、UI、动画、玩法、存档继续使用各自技能与工具集；用户已指定的生成器和已认可母版继续沿用。
- 已加载的资产通过当前编辑器修改、导入并保存；未加载且适合后台处理的资产使用后台接口。不要另起 commandlet 或第二个编辑器覆盖相同包；确有离线工具需求时使用不冲突的输出路径，真实冲突仅向当前用户说明。
- **资产写边界（2026-09-25 实测）**：运行中的编辑器持有 .uasset 文件锁，外部 commandlet 删除/覆盖报 Error 32；活编辑器里 `StaticMeshEditorSubsystem.import_lod` 异步生效（恒返回 -1、后续 tick 才落地），失败批次排队的任务还会污染同路径重新导入的包。整包替换安装（删＋全新导入＋LOD 补回）放在**编辑器关闭后的 commandlet 窗口**执行（先经用户同意关闭）；活编辑器桥只做槽绑定、`save_packages` 等短操作。案例见 [采集工具](../../ue5-weapon-workflow/references/harvesting-tools.md)。
- Vibe3D 的临时 handle 要保存为实际资产后才完成交付；重启后按已保存资产重新加载，不复用旧 handle。仅释放本任务的 handle。
- MCP 断开时读取必要的失败信息并重新连接；断连本身不是杀进程或重启的理由。继续不依赖连接的制作，说明尚未完成的接入；不要重复提交结果不明的写入。

## MCP 效率与 token 约定（2026-09-20）

- 同一任务内复用已经读取的工具 schema；只在首次使用、编辑器/插件发生变化或参数不匹配时重新获取对应工具集。工具集未知时才列目录，不在每步操作前重复发现全部工具。不缓存动态资产状态或跨重启复用 handle。
- 参数已知、无需读取中间结果的一组操作使用 `Tools/AssetPipeline/mcp_call_codex.ps1 -BatchFile` 顺序执行。默认复用会话，不为每次调用加 `-NewSession`。批量不是并行，也不是事务。
- 后一步依赖前一步返回的 handle、资产路径或条件判断时，优先使用编辑器内 Python 编排已注册工具；首次使用读取其执行环境及目标工具 schema，在脚本内传递真实返回值。若不适合脚本，则在依赖边界拆成小批次；普通 BatchFile 不支持返回值插值，不猜 handle。
- 优先在工具参数中限定目标资产、字段和日志范围。编排脚本只返回本任务涉及的资产路径、保存结果、必要 handle、警告和错误，不回传全场景或所有对象属性。
- 常规桥接调用使用 `-OutputFile <本任务唯一新路径> -MaxOutputChars 3000`；完整的显示文本写入文件，每个结果块最多向对话输出 3000 字符，截断时注明路径。按需读取文件中所需部分，不把整份结果重新塞入上下文。3000 是字符预算，不是 token 统计；大批次应按语义分组，避免累积大量输出。
- 原始 JSON 使用 `-Json -OutputFile <新路径>`，不与限长组合。未指定限长时保留原有完整输出兼容性。OutputFile 不覆盖已有文件；普通模式保存去除协议外壳后的完整文本，原始响应只有 Json 模式保留。
- 批量收到 HTTP 错误、JSON-RPC error 或 MCP result.isError 时停止后续步骤。工具在自定义正文里报告的业务失败，仍需调用方按该工具契约处理；桥不会推断所有工具的成功语义。已完成步骤不回滚，修正后从明确的失败边界继续，不重跑整个写入批次。
- 会话丢失的 HTTP 404 最多强制重新握手并重试一次；其他错误不自动重放写入。断连或结果不明时先保留完成状态，不能以重启或重复提交代替处理。
- 不追加连接探针、全量日志、轮询、PIE 或截图来证明流程优化。交付只说明修改、保存/构建范围及未测试状态；不得把输出字符下降换算成已实测 token 节省率。

示例（在工程根目录执行，batch.json 为本任务按已知 schema 制作的调用数组）：

```powershell
$resultPath = Join-Path $env:TEMP ('ue-mcp-' + [guid]::NewGuid().ToString('N') + '.txt')
& .\Tools\AssetPipeline\mcp_call_codex.ps1 -BatchFile .\batch.json -OutputFile $resultPath -MaxOutputChars 3000
```

## Live Coding 与生效范围

- 仅在编辑器已经运行且需要应用已有函数的小范围改动时考虑 Live Coding；编辑器未运行时直接后台构建，不为热编译启动它。不要把普通外部 UBT 构建、旧 Hot Reload 和 Live Coding 混为同一条路径，也不为绕过占用默认更改模块后缀。
- UE 的 Object Reinstancing 支持部分反射和结构变化，不能把“修改 .h / 新增 UFUNCTION”一律写成引擎强制关闭。涉及已有对象、保存资产和缓存引用时按上表选择；保留 FPSGAME 带资产 USTRUCT 和新类落盘的项目限制。
- .cpp 构造函数默认值不会自动更新已有实例。需要交付新实例时按任务选择后台重建/保存，或在已经运行的编辑器中重建；不得仅为观察默认值变化自动重开项目。蓝图/关卡中已有的属性覆盖值也不能假定会被重启清除。
- Live Coding 可能生成补丁文件，但补丁成功不等于基础 Editor DLL 已更新，也不自动代表下一次启动或打包已包含修改。后续常规构建完成前如实说明当前生效范围；新类型成为保存资产的依赖前先完成常规构建。
- 为完成必要编译读取该次构建输出并处理错误，属于开发工作；不因此追加运行测试。编译成功、资产保存、运行效果分别报告。

## 停止 PIE 与关闭/重启

- 停止 PIE 只是结束游戏运行，编辑器与 MCP 可以继续使用。工具不支持 PIE 中的资产编辑，或当前运行实例妨碍改动时，优先停止相关 PIE，再继续编辑；不自动升级为关闭编辑器。
- Live Coding 本身支持 PIE，但是否在当前运行中应用仍取决于对象与改动范围。用户未要求测试时，不主动启动 PIE。
- 必须关闭时，先完成仍需在当前编辑器内完成的制作，说明具体原因，保存本任务需要保留的正常资产；若其他任务占用或未保存内容归属不明，仅向当前用户说明阻塞，不联系其他会话。可以安全退出后完成后台构建/更新，默认保持关闭；只有用户要求或仍有只能在编辑器内完成的必要操作时才重新打开。
- 符合打开条件且归属清楚的必要重启按授权执行，不逐次增加确认。共享会话或未保存内容的处置不明时，仅向当前用户说明实际冲突；不要因“可能有人使用”放弃必要 MCP 工作。不得通过强制终止用户或其他任务的编辑器来绕过占用。
- 若加载失败使关卡缺类或对象残缺，不保存残缺包覆盖磁盘资产；先区分需要保留的改动与加载失败状态，再安排退出和常规构建。正常退出时处理具体保存提示，不把强杀作为恢复步骤。

## 并行与交付

- 多会话可以共同使用 MCP，但共享资产、关卡、主线程和编译窗口。调用按序执行；同一目标写入、编译和 PIE 操作协调排队，不覆盖其他会话改动。详见 [MCP 多会话规则](mcp-multi-session.md)。
- 沿用用户 2026-09-12 规则：默认不主动检查、测试、回归、截图、验收渲染或启动游戏。资料读取、制作、导出、导入、必要构建与接入照常完成；用户明确要求的测试/预览只在指定范围执行。
- 交付说明实际完成的文件/资产、构建方式，以及是否还需常规构建或重启；未测试就注明由用户测试。流程更新本身不触发编辑器操作、资产替换或测试。

## 自建 PowerShell 工具脚本的两个硬要求（2026-09-21）

给本工作流写 `.ps1` 辅助脚本（如 `Tools/Building/run-checkpoint-b.ps1`）时：

1. **文件必须带 UTF-8 BOM**。Windows PowerShell 5.1 对**无 BOM** 的 `.ps1` 按系统 ANSI 代码页
   （本机 936）解码，中文注释/输出会变成乱码，语法直接报错
   （`Unexpected token`、`The string is missing the terminator`），表现为"脚本根本跑不起来"。
   要注意**编辑工具常常会剥掉 BOM**：每次改完都要复核并在需要时补回
   （`[System.IO.File]::WriteAllText($p,$text,(New-Object System.Text.UTF8Encoding($true)))`）。
   改完用 `[System.Management.Automation.Language.Parser]::ParseFile(...)` 做一次语法解析自检，
   比直接运行更快定位这类问题。
2. **转交给外部 EXE 的路径一律给绝对路径**。子进程的工作目录不继承你的预期，
   `& exe 'FPSGAME.uproject'` 这类相对路径会让引擎找不到工程并静默退出（详见
   [无头 commandlet 的静默失败](../../ue5-debug-validation/references/live-coding-vs-full-build.md)）。
   工程文件用 `Join-Path $project 'FPSGAME.uproject'`，脚本自身用 `$PSScriptRoot` 拼。

- **不要用 `git checkout -- <文件>` 去"恢复"自己写坏的文件**。本机实测教训（2026-09-22）：把
  `UI/ColdSteelAmmoPresentation.cpp` 覆写过头后从 HEAD 恢复，结果 HEAD 里那一行 `return Brush.Get();`
  根本编不过（`MakeShared` 返回 `TSharedRef`，其 `Get()` 返回引用），而工作区里别人早已改成
  `&Brush.Get()` 且**尚未提交**——恢复动作等于回退了别人的修复。本仓库并行修改多、未提交工作是常态，
  **工作区才是真值，HEAD 不保证可编译**。要回退自己误写的文件时：先另存一份当前工作区内容，
  再按编译错误反推最小修改，最后用编译核对（本模块 rsp + `cl.exe`）确认结果与之前一致。
- **不要凭命令行猜测某个 `UnrealEditor-Cmd.exe` 是自己的残留进程**。本机实测教训：把并行会话
  正在跑的 `-run=RuneGoldMaterial` commandlet 误当成自己审计脚本的残留并结束了它。
  动手前先读完整命令行（`Get-CimInstance Win32_Process -Filter "ProcessId=<pid>"` 取 `CommandLine`）；
  分不清归属就不要动 —— 同上文，不得通过强制终止其他任务的进程来绕过占用。

## 后台构建的重试判据与产物核对（2026-09-26 实测）

并行会话开着编辑器是常态，构建失败最常见的两个原因都不是代码问题。把"等得起、判得准"写进重试驱动脚本：

- **判"能不能链"要看 DLL，不要看进程名**。`LNK1104: 无法打开 …\UnrealEditor-FPSGAME.dll` 说明有
  `UnrealEditor`／`UnrealEditor-Cmd`／游戏进程占着输出二进制。只检查 `UnrealEditor` 的 GUI 进程会漏掉
  commandlet（本机踩过：等待条件看着"没人占用"，构建照样 LNK1104）。可靠判据是**试着以独占方式打开**
  目标 DLL：`[IO.File]::Open($dll,'Open','ReadWrite','None')` 抛异常＝还被占用。重试循环里同时检查
  别的构建（`cl.exe`／`link.exe`／`dotnet.exe` 的命令行是否含本工程）与 `Saved/BuildEditor/` 最新日志，
  每次等待只打印一行，不抢 `-WaitMutex`（§WORKFLOW 7）。
- **构建成功后再核对产物**：读 `-Log=<path>` 里的 `^Result: Succeeded`，再确认 DLL 的字节数与
  `LastWriteTime` 变了。想在提交前确认"新符号真的进包了"，可对 DLL 做**严格 UTF-16 逐字节扫描**
  找新 CVar／函数名：不要用 `[Text.Encoding]::Unicode.GetString($bytes) -match ...` 之类的近似判断
  （踩过：只比较 3 个字节、跳过 `+2` 的错位实现给出假阳性）。这个检查只能证明**符号在**，
  不能证明行为正确——行为验收仍按用户规则交给用户。
- **加了 `UPROPERTY` 的源文件不要用 `/Zs` 自检当结论**。用旧 rsp 单独 `/Zs` 编译会因 UHT 未重跑而报
  `UCLASS`／`GENERATED_BODY()` "宏未展开／缺少类型说明符"这类假错误，看着像代码写错。真正的判定是让
  UBT 跑一遍（UHT + 编译）；不要在假错误上改代码。
- **PowerShell 里 `$x = <函数>` 会吞掉函数的 `Write-Output`**。本机踩过：把构建函数写成
  `$x = Invoke-Build ...`，函数内的所有进度输出都进了返回值，日志里只剩一行空白。要么用 `Write-Host`，
  要么让函数把结果写文件再读。

## 活编辑器里的资产制作与校验（2026-09-26 实测）

- 需要读写**已加载**资产时走桥：`Tools/AssetPipeline/mcp_call_codex.ps1 -PythonScript <脚本>`（批次互斥，
  输出内联返回，默认 120 秒超时）。只读复核也走桥；不额外起 commandlet／第二个编辑器去覆盖同一包。
- **Geometry Script 的资产制作配方必须按 5.8 实际签名核对**，记忆里的 API 名常常不存在。本机验证可用的组合：
  `GeometryScript_AssetUtils.copy_mesh_from_static_mesh(静态网格, DynamicMesh(), GeometryScriptCopyMeshFromAssetOptions(), GeometryScriptMeshReadLOD(lod_type=SOURCE_MODEL))`
  → `GeometryScript_Materials.get_triangle_material_id` 统计材质分布 → `delete_triangles_by_material_id`
  按材质裁面 → `remap_material_i_ds` 归一槽号 →
  `GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(..., GeometryScriptCreateNewStaticMeshAssetOptions(enable_collision=False))`。
  三角面计数是 `DynamicMesh.get_triangle_count()`（`GeometryScript_MeshQueries` **没有**这个函数）；
  5.8 里 `EditorStaticMeshLibrary` 与 `StaticMeshEditorSubsystem.set_material` 都不可用，赋材质用
  `UStaticMesh.set_material(槽号, 材质)`。
- **材质缺使用标志会静默变默认灰材质**，日志里是 `Default Material will be used in game`。改标志要在
  python 里设完 `save_asset`；无头环境下 `recompile_material` 恒返回 False，不要据此判定失败，
  改成"告警 + 保存"并在日志里留下改前改后的散列。
- 骨骼网格的 **Nanite 组合数据**：python 只能读到 `FNaniteAssemblyData.Parts`（用了哪些网格），
  **读不到 `Nodes`**（摆位/变换空间/骨骼绑定）。`IsValid()` 要求两者都非空，所以"`Parts` 齐全"
  不能证明树冠摆位正常——运行期只能靠引擎侧诊断日志核对。


## 依据

- [Epic：Unreal MCP](https://dev.epicgames.com/documentation/en-us/unreal-engine/unreal-mcp-in-unreal-editor)
- [Epic：Live Coding 与 Object Reinstancing](https://dev.epicgames.com/documentation/en-us/unreal-engine/using-live-coding-to-recompile-unreal-engine-applications-at-runtime)
- [Epic：插件启用与重启](https://dev.epicgames.com/documentation/en-us/unreal-engine/working-with-plugins-in-unreal-engine)
- [Vibe3D：编辑器内建模工具集](https://www.vibeue.com/vibe3d)
- FPSGAME 的历史问题与按需排查：[Live Coding 与常规构建](../../ue5-debug-validation/references/live-coding-vs-full-build.md)。
