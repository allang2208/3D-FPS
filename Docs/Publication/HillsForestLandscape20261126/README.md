# 丘陵林地与村外道路交付

正式图为 `/Game/GameMaps/L_ForestPathVillage`。丘陵主题管理地形、林下植被和湿地；道路主题管理东门林道、采石场进场路和路肩装饰。独立样板保留自己的布光与高度场。后续制作从[地编技能](../../../skills/ue5-landscape-authoring/SKILL.md)和[两主题组合说明](../../WorldGeneration/hills-landscape-themes.md)进入。

## 制作和恢复

- 高程、分层点集和材质按[教程研究及项目制作记录](../../Production/HillsForestPathStudy.md)定位。[制作工具](../../../Tools/WorldGeneration/ForestVillage)包括 R45 路面裁剪与物理尺度配方。[主题描述](Configuration/HillsForestPathThemes)给出资产顺序和正式 PCG 图；密集点集及高度图在本地制作源。[独立样板代码](ReferenceProject)需要配套 UE 资产。
- [专属源码与目标路径](Implementation/files.json)列出应接入正式宿主的位置。公开主线与本机生产宿主的共享接口有版本差异。[共享文件差异索引](Integration/index.json)按制作批次保存修改，每份 JSON 的 `patch` 是统一差异，`before_sha256_lf` 和 `after_sha256_lf` 对应去除 UTF-8 BOM 并统一 LF 后的文本。恢复时选择与宿主相符的起点，核对前置哈希，再应用对应差异，避免重复应用已交付的阶段。
- [正式包清单](Recovery/packages.json)与[本地产生的高度数据索引](Recovery/generated-includes.json)用于核对同版本依赖。[生产宿主文本清单](Recovery/host-text.json)记录本机私有恢复包中各文件的原目标和 SHA-256。已许可的 Fab 扫描、Unreal Sensei 材质、原始录像、玩家档案、UE 包和编辑器模块分别由正式资产库、制作源或版本回执恢复。Git 发布范围为制作配方、源码与证据摘要，未在纯公开克隆编译游戏。

## 联机与性能

最终编辑器模块在本机双进程、60 ms 模拟延迟和 2% 丢包下完成 22 项检查，覆盖实际地面碰撞、采石场、昼夜与雨、远端砍树、重连和再生。丘陵入口目前只支持单人和监听服。三处固定机位的总帧中位数在正式阴影设置下分别为村内 17.62、路堑 18.68、林坡 20.08 ms，取两轮中位数的均值。完整预载需求 5,904 MiB，实测预算 3,894 MiB，加载界面仍持有输入。下一轮优先评估高清资源分区。[实测摘要](Evidence/summary.json) · [详细复核](../../WorldGeneration/forest-village-network-performance.md#forest-delivery-r47)

## 归档

隔离宿主、工具中间产物、一次性检测画面和已退役候选均按原路径记账。项目内文件移到 D 盘工程的 `trash/ForestLandscapeCloseout-20261126`，F 盘文件移到 `FPSGAMEData/trash/ForestLandscapeCloseout-20261126`。回退版本、正式资产、教程源和可复用的生产脚本留在原有功能目录。本机 `F:/FPSGAMEData/ArtProduction/StorageLayout/ForestLandscapeCloseout-20261126` 保存恢复地址、逐文件 SHA-256 和目录联接定义。NAS 快照位于 `Y:/备份/FPS3D/HillsForestPath/ForestLandscapeCloseout-20261126`。[归档统计](cleanup-summary.json)
