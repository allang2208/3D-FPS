# 书签棋盘格修复（2026-10-16）

截图中的棋盘格是材质编译失败后的默认材质，不是贴图分辨率不足。

`Saved/Logs/FPSGAME.log` 与前次流程检查日志均记录：

```text
M_ManualRibbonInteractive / M_ManualClaspInteractive
Failed to compile Material for platform PCD3D_SM6, Default Material will be used in game.
(Node PreSkinnedPosition) External code identifier 'PreSkinnedPosition'
is not available in the EMaterialShaderFrequency::Pixel shader.
```

书签使用模型局部 X 坐标区分左右，既用于顶点抬升，也用于 BaseColor 的淡出反馈。原先 BaseColor 依赖树直接读取只支持顶点阶段的 `PreSkinnedPosition`，造成两份材质均编译失败。

本次仅在淡出值与 BaseColor 乘法节点之间加入 `VertexInterpolator`：左右判定与淡出值在顶点阶段计算，再把一个标量传给像素阶段。布纹、字样、法线、粗糙度、金属参数、左右独立反馈和顶点抬升保持原设计。

修复通过已有编辑器的共享批次桥执行，未启动或关闭编辑器、未结束当前 PIE。仅保存以下两个源内容包，未保存关卡或其他资产：

- `/Game/Building/PotionWorkbench20261015/ManualV7/Materials/M_ManualRibbonInteractive`
- `/Game/Building/PotionWorkbench20261015/ManualV7/Materials/M_ManualClaspInteractive`

当前引擎的 `MaterialEditingLibrary.recompile_material` 返回编译错误字符串数组，两者均为空，保存成功。旧包备份与落盘回执位于 `SourceAssets/AlchemyManualBookmarkMaterialFix20261016/Before/` 和 `repair-receipt.json`。生成脚本 `AlchemyManualUsability20261016/import_materials.py` 已同步修正，避免重新生成时复发。

前次 69 项流程断言没有覆盖材质编译 Warning；`run_audit.ps1` 现已把手册材质回退列为失败。此次未重新运行整套流程检查，未新增截图或视觉验收。当前私有预览按需捕获，重新打开手册会刷新显示。

当前恢复链、退役文件归档和最终检查状态见 [手册收尾发布](../Publication/AlchemyManual20261016/README.md)。本文所述阶段结果保留为历史记录；本次整理未重新运行测试。
