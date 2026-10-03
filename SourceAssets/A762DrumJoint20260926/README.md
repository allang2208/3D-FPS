# A762 大弹鼓连接段修复 · 2026-09-26

计划、原因与实施记录：[项目记录](../../Docs/Weapons/a762-drum-joint-20260926.md)。

## 制作源

- `prepare_geometry.py`：读取 A762 原厂弹匣及固定弹井，在就位的弹匣坐标中准备轮廓。
- `author_drum.py`：保留旧鼓体 z ≤ 24 mm 的位置、UV 和角点法线，剪掉扭曲上颈，重建连续外壁与有限内腔。
- `SM_A762_drum.blend` / `Exports/SM_A762_drum.fbx`：可编辑源与引擎导出。
- `interface_inputs.json` / `authoring_receipt.json`：制作输入与产物参数，不是运行验收报告。
- `sync_authoring_entry.py`：只同步共用配件包中的 drum 条目、FBX、Blend，备份其原有文件。

Blender 5.1.2 后台依次执行 `prepare_geometry.py`、`author_drum.py`，随后用 Python 执行 `sync_authoring_entry.py`。共用 `Accessories05/author_geometry.py` 的 drum 分支也转到这套制作入口。

## UE 接入

`run_import.ps1 -StageOnly` 只导入独立包 `/Game/Weapons/A762/DrumJoint20260926/SM_A762_drum`。

`run_import.ps1` 在没有本工程 UE 进程占用时，导入并保存正式路径：
`/Game/Weapons/A762/Accessories05/Meshes/SM_A762_drum`。
已有交互编辑器运行时，用工程 `mcp_call_codex.ps1 -PythonScript <install.py>` 在同一编辑器中操作。
脚本保留挂点、材质身份与既有 LOD/Nanite 策略，正式包替换前备份到 `Before/`。

保存结果分别记在 `candidate_receipt.json` 与 `install_receipt.json`。`saved` 只代表该次资产保存返回成功，不能作为运行观感或动画验收。

## 范围与来源

下部模型来自 `A762DrumNeck20260925/SM_A762_drum.blend`，该文件作为只读供体保留；鼓壳原始制作与来源见 `LargeDrumUpgrade20260920/provenance.json`。
井口轮廓、原厂弹匣和新段涂层来自 `A762Meshy20260920/Accessories05`、`Refinement02`。
本轮不新增第三方素材，不改变已有资源的许可或公开分发范围。

没有改 C++、换弹动画、容量、配件数值或存档；没有启动游戏、PIE、自测或验收渲染，由用户自行测试。
