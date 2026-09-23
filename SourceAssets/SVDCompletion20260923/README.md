# SVD 完成版源资产（2026-09-23）

## 2026-09-23 整理后的当前入口

旧换弹导出已由 `SVDThumbUp20260923` 替代；当前模型与材质入口为 `SVDRefinedFinish20260923`。本目录的旧制作记录保留其历史日期与验收边界。已经移走的旧导出、自动备份及恢复快照位于 `trash/svd-superseded-20260923/SourceAssets/` 下的同名目录，原路径、散列及保留替代物见 [归档清单](../../Docs/AssetArchives/svd-superseded-20260923.json)。当前所需 Blend、脚本、参数与原素材仍保留；不要直接重跑旧导入覆盖用户已认可的抓握。新 checkout 的恢复方式见 [SVD 发布说明](../../Docs/Weapons/svd-publication-20260923.md)。

当前运行目录：`/Game/Weapons/SVDDragunov20260922/Complete20260923`。
完整说明见 [开发记录](../../Docs/Weapons/svd-completion-20260923.md)。

- `SVD_Complete_Editable.blend`：本枪刚性件、共享 Manny 手臂和全部动作。
- `Exports/`：骨骼网格 + 12 段 120 Hz 动作 FBX。
- `Audio/`：4 个设计枪声；`audio_provenance.json` 记录来源和散列。
- `author_svd.py` / `authoring.json`：本枪绑定、手部拟合、动作和挂点定义。
- `contact_fit.json`：已固定的左手包握以及右手关键接触记录。`fit_contacts.py` 用于重新拟合时产生该输入，正常重导出不需要先重跑。
- `import_common.py`、`import_mesh.py`、`import_animations_0..3.py`、`import_audio.py`：短批次导入；编辑器内使用现有 `mcp_call_codex.ps1 -PythonScript` 和独立结果文件。
- `render_review.py`：源模型关键帧检查；输出手臂为中性灰，不是 UE 画面。
- `asset_check.json`：本轮 12 动作 / 11 材质 / 4 声音的 UE 读回结果。
- `Before/`：本轮首次修改时的局部备份；不能整目录覆盖恢复，期间存在并行编辑。

## 重新制作

在项目根目录运行：

```powershell
& 'E:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --factory-startup --python SourceAssets/SVDCompletion20260923/author_svd.py
python SourceAssets/SVDCompletion20260923/author_audio.py
```

脚本复用原 SVD 八件源 FBX、AKM native/ReloadPolish 源、M4 共用手臂、A762RightCharge 的接触记录及本目录 contact_fit.json；不需要重新下载第三方模型。

## 最终状态

资产导入和此前指定检查已完成。用户关闭编辑器后，最终后台 Editor 构建返回 Succeeded，包含最后的 M4 配件握姿排除条件；构建产物已落盘。日志：`build_editor_handoff_link_20260923.log`。本次收尾没有打开编辑器、运行游戏或追加测试，完整实机测试由用户进行。


## 后续 UV 修复

用户截图反馈的枪托/瞄准镜错贴已按原包贴图方向修正。当前 blend 与 FBX 包含 UV0 V 轴补偿，源分件脚本也已更新。参见 [修复与 UE 资产渲染记录](UVRepair/README.md)。本修复不改手臂蒙皮与动作。

## 后续战术动作

战术冲刺与枪托快速近战的四段占位动作已重做，完成后台导入保存。当前完整 Blend 和 Exports 包含新版动作；整枪作者入口通过 `tactical_actions.py` 生成它们。仅重做这四段时使用 `TacticalActions/author.py`，避免重新制作其他动作或网格。见 [动作记录](TacticalActions/README.md)。本轮未运行游戏或视觉测试。

## 后续材质

当前完整 Blend 已同步 `SVDSurface20260923` 的枪钢、聚合物和镜筒分区材质。四张 4K BaseColor／ORM 与两个 UE 母材质已保存，七个既有 MI 接入新资源，保留原结构法线、网格与全部动作。若从基础作者入口重新制作完整源，随后运行 [材质制作入口](../SVDSurface20260923/README.md) 恢复这层工作材质；本轮不需要重新导入 FBX。未运行游戏或效果验收。
