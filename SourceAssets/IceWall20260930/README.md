# 冰墙作者源

当前运行版本为 `FabIceV3`，复用用户已导入的 `/Game/Ice` 第 6 套冰面，使用大块破裂冰体错缝拼接。制作入口、资产路径和本轮落盘边界见 `Docs/Skills/ice-wall-fab-v3-20260930.md`；下文为 BlockV1 历史源，`RealisticV2` 也继续保留。

本次采用 Blender 精确制作拼接接口，并保留四种有缺角、凹凸外表的方块。每个模块基准体为 1 m，UE 导入转换为厘米，运行时按墙厚、段宽和层高缩放。平整接缝／顶面服务于连续拼接、放置和机枪脚架；破面、裂纹和霜面由原创几何及项目已有材质资源提供。

- `IceWallBlocks.blend` 为可编辑作者源，四份 `SM_IceBlock_*.fbx` 为导出。
- `geometry.json` 记录制作脚本导出统计，每个模块 108 三角面。
- `ice_wall_cold_steel.png` 为原创冷钢图标。
- `icewall.mp3` 保留原项目施法音，`icewall.wav` 为 UE 导入源，出处见 `sound-source.json`；不声明音频可公开再分发。
- UE 已保存资产及共享依赖见工程 `Docs/Skills/ice-wall-migration-20260930.md`。

作者脚本为 `Tools/Skills/author_ice_wall_blocks.py`、`prepare_ice_wall_sources.py` 与 `build_ice_wall_assets.py`。本轮完成后台制作和资产保存，未制作验收渲染，观感交由用户在游戏中测试。
