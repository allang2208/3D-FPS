# 编辑器内脚本的写法与排障纪律（2026-09-23）

> 从 2026-09-22/23 主场景广场接入中总结。这些是**下一次写编辑器内脚本时都要用**的纪律，
> 不是那一次的过程记录；过程记录见 `Docs/Building/main-plaza-20260922.md`。
> 桥本身的参数与限长约定见 [后台开发与编辑器使用条件](editor-open-development.md)。

## 1. 脚本先设护栏，再动任何东西

一次写入型脚本在开头按顺序断言，任一不满足就**抛错退出且不保存**：

1. 编辑器有 world；
2. 没有 PIE（`editor.get_game_world() is not None`）；
3. 当前地图是目标地图——**不是就先查脏包**：
   - 任何地图有未保存改动 → **拒动**（保护并行会话的工作）；
   - 干净 → `level.load_level(目标)`，做完**保存后切回原地图**。
4. 目标锚点存在（PlayerStart 数量、被改的 actor 是否找齐）。

切图这一步照搬 `SourceAssets/SquareAltar20260922/place_hub_altar.py` 的既有做法。
有了它，**运行时编辑器开在哪张地图都无所谓**，调用方不必先手动切图。

实证：本轮护栏两次正确拦下操作——一次是编辑器开在 `L_Dungeon_Randomized` 而目标是主场景，
两次都"什么都没改、什么都没保存"退出。护栏不是形式，是当晚唯一避免误改的东西。

## 2. 先探 API，再写批次；不要按名字猜

**两次失败都源于猜 API 名**，每次都要重跑一整批：

- `EditorStaticMeshLibrary.set_lod_count` 不存在（该库整体已废弃）→
  正确入口是 `StaticMeshEditorSubsystem.set_lods`，参数形态也不同（见
  [场景几何成本与 LOD 收敛](../../ue5-performance-packaging/references/scene-geometry-cost-and-lod.md)）；
- `StaticMesh.get_static_materials` 不存在 → 应用
  `get_editor_property('static_materials')`。

做法：批次开跑前用一条**只读**脚本 `dir(类)` 打一遍目标 API 面，
或 `-DescribeToolset` 读工具 schema。这比"写完再撞 AttributeError"便宜得多。

## 3. 会静默失败的 setter 必须读回

`set_editor_property` 对**不存在的属性名会抛错**，但对**存在却不生效**的情形不会：
本轮 `set_editor_property('forced_lod', 1)` 不报错也不生效，真实属性名是 `forced_lod_model`；
`set_editor_property('visible', False)` 在组件上正常，但同类写法在别处可能被 try/except 吞掉。

纪律：**任何关键写入都要在同一个脚本里读回校验**，并把读回值写进回执 JSON。
校验不通过就报失败，不能把"调用没抛错"当成生效。

## 4. 幂等：给自己产出的 actor 打标签，重建前先删自己的

生成大量 actor 的脚本要：
- 给全部产出打唯一标签（如 `ColdSteel.MainPlaza.Generated`）与分类子标签；
- 每次运行**先删带该标签的 actor 再重建**，于是可安全重跑；
- 别人的东西用**独立标签**（如火把用 `ColdSteel.PavilionTorch`），
  这样"重建广场"不会连火把一起删掉；
- 写回执 JSON 记录数量与逐项事实，并在保存**之前**断言实际数量等于预期数量。

## 5. 桥的等待条件：6776 是按需监听的

远程执行的命令端口（默认 6776）**只在客户端请求时才开监听**，空闲时不通。
写"等端口就绪再跑"的后台作业时，`Test-Port 6776` 会一直为假直到超时。
判断编辑器是否可接入，用 `py -3.11 Tools/AssetPipeline/ue_python_exec.py --list`（成功即退出码 0），
或只看 MCP 的 8000。

## 6. 不要用变量接收桥的输出

在 PowerShell 里写 `$a = & .\Tools\AssetPipeline\mcp_call_codex.ps1 ...` 会把**脚本的全部输出**
吞进 `$a`，对话里只剩下 `System.Object[]`，而真正的报告已经丢失。
需要判成功时用 `$LASTEXITCODE`，输出让它直接进标准输出。

## 7. 长批次用后台作业，别让工具超时杀掉桥

桥持有命名互斥锁；前台调用被超时杀死会留下"上次桥异常退出、UE 状态未知"的局面。
长批次（数百个 actor 的生成/保存）用后台作业提交，再用 `job_output` 收结果。
