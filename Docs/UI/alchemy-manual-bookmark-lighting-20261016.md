# 手册书签暗部可读性调整（2026-10-16）

用户反馈书签受阴影遮挡、部分发黑。书签位于较低的封面，现有阅读灯光为斜向主光，凸起纸页会遮挡其直接照明。

本轮仅调整现有两份书签材质：

- 布条保留 Default Lit、原贴图与法线；从最终基础色接出 `BookmarkReadFill=0.42` 的微量自发光补偿，让材料色、字样和布纹在投影内仍有亮度。
- 金属扣使用 `BookmarkReadFill=0.22`；金属度由 0.85 调整为 0.68，粗糙度由 0.35 调整为 0.44，柔化暗反射与亮部反差。
- 补偿取自已经处理左右书签末端淡出的最终基础色，继续随 `BookmarkFadeLeft/Right` 变化。悬停抬升、点击、跳转和阴影层次保留。
- 生成源 `SourceAssets/AlchemyManualUsability20261016/import_materials.py` 同步修改。

执行脚本为 `SourceAssets/AlchemyManualBookmarkLighting20261016/apply_lighting.py`，通过共享 UE 批次互斥修改并保存两个源材质包；旧包与生成脚本保存于同目录 `Before/`。最初等待已有编辑器接入期间，编辑器已退出，故改用 `apply_headless.ps1` 在现有构建结束后运行无界面资产 commandlet。没有启动可见编辑器或游戏，也不修改关卡灯光。

后台应用已完成：两份材质编译返回的错误数组均为空，并已保存；commandlet 退出码为 0。材质回执为 `SourceAssets/AlchemyManualBookmarkLighting20261016/apply-receipt.json`，进程回执为同目录 `Apply-20261016-201213/result.json`。

此次只进行材质修改、编译与保存，没有截图或运行验收；实际阴影与可读性由用户在重新打开手册后确认。

当前恢复链、退役文件归档和最终检查状态见 [手册收尾发布](../Publication/AlchemyManual20261016/README.md)。本文所述阶段结果保留为历史记录；本次整理未重新运行测试。
