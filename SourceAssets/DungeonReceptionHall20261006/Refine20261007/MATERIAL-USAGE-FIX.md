# 用户报告的 12 条材质实例化警告 / 2026-10-07

用户截图的地图检查结果为 0 个错误、12 个警告，均为指定材质缺少 `InstancedStaticMeshes` 使用标记。上一轮大厅修订使用了独立材质版本，但未修复这些旧版共用材质的持久化使用标记。

修复限定在 `fix_shared_material_usage.py` 明列的 12 个材质：车站电脑与印刷材质 7 个，生活区不锈钢与橡胶 2 个，仓储 ToolPaint 1 个，处理容器 Gray 和 Charcoal 2 个。只开启实例化使用标记、编译必要着色器并保存，不改材质图、配色、模型、关卡或玩法。

五处生产配方已补齐对应新建材质的使用标记：

- `SourceAssets/StationWorkshop20261003/Scripts/materials.py`
- `SourceAssets/StationWorkshop20261003/RefineV2/Scripts/materials.py`
- `SourceAssets/DungeonStaffLiving20261002/Scripts/build_wall_inset_materials_v6.py`
- `SourceAssets/WarehouseContainers20261002/Scripts/materials.py`
- `SourceAssets/IncineratorContainers20261003/Scripts/materials.py`

执行沿用 `install_background.ps1 -ScriptName fix_shared_material_usage.py` 的现有桥和批次互斥。恢复副本在 `Snapshots/shared-material-usage/`；实际保存进度在 `Receipts/shared-material-usage.json`，仅 `stage=materials_saved` 表示全部完成。

首次保存被 UE 的运行模式限制拒绝，第一个材质当时仅在内存开启标记。用户关闭 UE 后，已于 2026-10-07 通过后台 PythonScript commandlet 完成全部 12 个材质的编译与保存，退出码为 0；回执已记录 `stage=materials_saved`，每个目标均为 `used_with_instanced_static_meshes=true`、`saved=true`。未启动交互编辑器，未保存地图，无需重导入大厅。后续执行保留修改前的 PIE 状态限制。

未追加地图检查、PIE、截图或运行测试，由用户测试。
