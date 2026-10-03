# 手部材质调参（仅实例）

2026-09-23。用户规则：**只改手部材质实例参数**，为后续手部/手臂装备外观扩展预留一个可反复微调的入口。

## 关键发现：保存 API 的返回值不可信

本次排查的核心结论，后续任何在本项目里写资产的人都应该知道：

**`unreal.EditorAssetLibrary.save_loaded_asset()` / `save_asset()` / `EditorLoadingAndSavingUtils.save_packages()` 在本项目里一律返回 `False`，但保存实际上是成功的。** 不要用返回值判断保存结果，否则会误判成"保存被占用"并去修一个不存在的问题。

正确判据：**看 `.uasset` 的 LastWriteTime 是否前移**，再用一个新的进程回读参数值确认。

排查过程中曾因此浪费数轮：命令进程与编辑器进程都返回 `False`，但日志里 `LogSavePackage: Moving output files ... MI_Manny_01.uasset` 明确写出了盘，文件时间戳也确实变了。

## 为什么之前一直改不动

编辑器（PID 62248）在本次任务开始时就已经打开并持有资产。此时：

- 命令进程 `UnrealEditor-Cmd -run=pythonscript` 保存失败（编辑器占用）；
- 编辑器内通过 MCP 桥执行也保存失败。

**真实原因是资产被编辑器占用**，不是参数写错、不是缺少事务。用户关闭编辑器后，用命令进程一次即写入成功。

编辑器内执行 Python 的正确入口是 MCP 桥，不是 `-run=pythonscript`：

```powershell
cd D:/FPS3D/FPSGAME
& powershell -NoProfile -File 'Tools/AssetPipeline/mcp_call_codex.ps1' `
    -PythonScript 'SourceAssets/HandMaterialTuning20260923/tune_instances.py'
```

### 参数传递的坑

`-run=pythonscript -script=x.py -- a b` 里的实参**会被丢弃**，脚本实际拿到的 `sys.argv` 只有脚本路径本身（已实测）。编辑器内的远程执行同样只传路径。因此本目录用**同目录下的 `request.json`** 传参，而不是命令行：

```json
{ "mode": "apply", "preset": "detail-up", "label": "detail-up" }
```

## 本次改动（已落盘并回读确认）

只动两个材质实例，**父材质、shader、烘焙贴图全部未改**（父材质时间戳仍为 2026-09-12）。

| 实例 | 宿主 | 参数 | 原值 | 新值 |
| --- | --- | --- | --- | --- |
| `MI_Manny_01` | 上臂（皮肤+布袖） | `SkinDetailStrength` | 0.012 | **0.03** |
| `MI_Manny_01` | 上臂 | `LeatherNormalStrength` | 0.55 | **0.85** |
| `MI_Manny_02` | 前臂+手套 | `SkinDetailStrength` | 0.012 | **0.03** |
| `MI_Manny_02` | 前臂+手套 | `LeatherNormalStrength` | 0.55 | **0.85** |

`SkinTint`、`SleeveTint`、`SkinScatterStrength`、`GloveCuffStart`、`LeatherTileRepeat` 保持已接受基线不变。

含 `SkinTint`/`SleeveTint` 的任何改动会**同时写两个实例**：上臂与前臂是两个独立构建的父材质，各有一份同名参数，只改一个会让肘部接缝颜色分叉。

## 用法

先编辑 `request.json`，再执行上面那条桥命令。

| mode | 作用 |
| --- | --- |
| `inspect` | 只读：回读两个实例的当前值、父材质路径与已被覆盖的参数名，写 `instance_state.json` |
| `apply` | 应用 `preset` 或显式参数，写 `tuning_report_<label>.json` |
| `baseline` | 恢复 2026-09-12 基线（`SkinDetailStrength`/`LeatherNormalStrength` 删除覆盖，散射与开口回基线值） |

预设（`preset` 字段）：

| 名称 | 效果 |
| --- | --- |
| `detail-up` | 细节上调（本次采用）：皮肤 0.03 / 皮革 0.85 |
| `detail-strong` | 更激进：皮肤 0.05 / 皮革 1.05，用于探上限 |
| `detail-down` | 反向：皮肤 0.006 / 皮革 0.35 |
| `skin-only` | 只动皮肤毛孔 0.035 |
| `leather-only` | 只动皮革皮纹 0.95 |

也可用显式键覆盖（`apply` 模式下与 `preset` 并存时显式值优先）：

```json
{ "mode": "apply", "label": "my-try",
  "skindetail": 0.04, "leathernormal": 1.0,
  "skintint": [0.38, 0.25, 0.19], "sleevetint": [0.02, 0.024, 0.027],
  "scatter": 0.18, "tilerepeat": 4.311859 }
```

`GloveCuffStart` **不要单独改**：卷边几何烘焙在 `T_Manny_Cuff3cmField` 与 `T_Manny_Cuff3cmRollNormal` 里，只改这个标量会让开口与卷边错位。要改长度须走重烘焙管线。

## 未做的事与边界

- **未启动 PIE、未截图、未做视觉验收。** 数值改动已落盘并回读确认，观感由用户用 `SourceAssets/HandEquipmentAppearance/run_preview.ps1 -Label <名称>` 判断。
- 皮肤粗糙度（`skin_sleeve.hlsl` 里 `0.39–0.58`）、皮革粗糙度（`0.35–0.9`）、掌面 `0.77`、布袖 `0.79` **是 shader 里的硬编码常量，实例改不了**。要动它们必须改 HLSL 并重建父材质，超出本次"只改实例"的范围。
- 卷边几何（0.65 mm 隆起 @ 距开口 2.2 mm、0.10 mm 浅槽 @ 4.8 mm）烘焙在贴图里，同样超出范围。
- 曾用 `Content/Weapons/M4InfimaV3/MI_HandMatSaveCap.uasset` 做过"编辑器能否写盘"的能力探针，该临时资产已删除。
- `Tools/AssetPipeline/mcp_call_codex.ps1` 的内层发现超时由 `20` 秒改为 `120` 秒（仅放宽节点发现等待，不改变调用语义）。该文件为 UTF-8 **带 BOM**，用会丢 BOM 的编辑器改它会让 `powershell.exe` 5.1 按 ANSI 解析、中文报错并使整脚本解析失败——本次已踩过一次，改它必须保留 BOM。
