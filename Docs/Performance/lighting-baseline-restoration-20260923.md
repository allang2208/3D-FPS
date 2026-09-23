# 恢复关闭光追前的光照基线

用户在确认全面剔除带来的配光返工成本后，明确要求“那你先恢复”。本轮仅回退光照剔除和随后纯光栅配光补偿，不回退模型、实例化、分帧加载、导航、UI 或其他任务的修改。

## 已恢复文本配置

- `Config/DefaultEngine.ini`：恢复 GenerateMeshDistanceFields、RayTracing、RayTracingProxies；GI/ReflectionMethod 恢复为 1。删除本任务新加的禁用门控和平台 RayTracingMode=Disabled，回到先前配置/引擎默认值，不擅自强制原先未启用的功能。
- `Config/DefaultEditor.ini`：恢复资产预览的 Lumen GI/反射和原 MegaLights 属性值。
- `FPSGAME.uproject`：删除本任务新增的四个降噪插件禁用条目，保留 Vibe3D、LiveCodingToolset、Voxel 及其他原有插件状态。
- 四个地牢拍摄制作脚本恢复原有 Lumen 设置；没有执行拍摄。
- `WORKFLOW.md` 更新为恢复原光照的最新用户决定；旧剔除/纯光栅文档标为历史记录。

## 资产恢复范围与进度

恢复清单来自此前实际写入回执，共 **363 个资产文件**：344 个 StaticMesh、16 个灯光/材质资产、3 张地图。使用 `Saved/RayTracingRemoval20260923/Backups/Content/` 中第一次剔除前的备份，不使用后来纯光栅补偿前的中间状态。

准备时这些目标文件的最后写入时间仍属于本任务当时的写入批次。恢复清单保存当前和原始文件散列，离线执行前若目标发生后续修改则停止覆盖，保留现场。

**当前状态：已完成并落盘。** 用户确认保存并关闭 UE 后，离线批次恢复 **363/363 个资产文件**，没有发现准备后的内容冲突；脚本退出码为 0。没有启动新的 UE 进程或 commandlet。

正式昼夜蓝图与 DayNight_Lighting 地图恢复后，太阳、天空、曝光、AO 和场景预设引用随原备份恢复。随后按用户仓库整理要求，七份未使用 RasterProfiles 已移到 `trash/dungeon-performance-rejected-20260923/Content/Lighting/RasterProfiles/`。离线包名称表扫描和已有编辑器资产注册表均未发现外部引用，目标未加载且无待保存修改；逐文件散列见 [归档清单](../AssetArchives/dungeon-performance-20260923.json)。

恢复前现状另存 `Saved/LightingRestore20260923/BeforeRestore/`，不覆盖原始备份。清单为 `restore-manifest.json`；实际资产执行结果为 `asset-restore-receipt.json`。一次性恢复脚本现已归档为 `trash/dungeon-performance-rejected-20260923/Tools/Rendering/restore_lighting_assets_20260923.ps1`；其旧目标散列和工作目录属于历史批次，不应直接重跑。原剔除／补光脚本及两份废案说明同步归档，正式路线以本文和 [优化完成记录](dungeon-performance-completion-20260923.md) 为准。

没有用 Git 整文件重置 Config/DefaultEngine.ini 或 FPSGAME.uproject；同期导航高度、Python 远程接口、插件配置和其他开发改动保留。资产仅按实际写入回执恢复，另外六份只备份但未修改的原始预设没有覆盖。

## 生效方式

硬件光追支持和着色器设置需要下一次正常启动 UE 才采用。资产恢复为原始文件，不需要 C++ 构建。本轮不自动启动编辑器、运行游戏、截图或追加性能/视觉测试；下一次启动可能重新准备着色器和距离场派生数据。
