# 手持火把 R17 与 11 月恢复

火把的当前实现位于 [WoodenTorchComponent](../../../Source/FPSGAME/Weapons/WoodenTorchComponent.cpp)，出手侧由 [WoodenTorchItem](../../../Source/FPSGAME/Weapons/WoodenTorchItem.h) 决定。双持时 F 使用主手，右键使用副手。手枪配副手火把时，右键瞄准，F 使用副手。工作台用两块木头制作一支。装备状态下，室内或晴天可用 24 分钟，露天下雨 12 分钟、暴风雨 8 分钟。

## 从仓库和恢复包重建

- **资产与原件**　完整本机恢复从 NAS 的 `备份` 目录开始，按 [R1 至 R17 归档清单](restore-chain.json) 的顺序取包，遵循各包回执的前置关系。R11 的源码和 R12 的正式链接分开记录。当前木柄与燃料头使用 R7 的模型，主火焰使用 R10 的材质、体积代理和 Niagara。制作脚本位于 [WoodenTorch20261122](../../../SourceAssets/WoodenTorch20261122)，复用模型的作者与许可见 [Fab 署名](../../../SourceAssets/WoodenTorch20261122/FabHandheldR2/HandheldTorch-NablaDeveloper-CCBY4.txt)。模型、原始纹理、密集手部参数和 UE 二进制从本机或 NAS 取回。
- **共享代码**　[按版本列出的补丁与目标路径](shared-integration.json) 用于合并正式宿主的输入、动作、身体表现、网络结算、燃料、UI 与特效。先处理本次需要的 `MagicCrystalCopy`、`Workstations`、`StaffOffhand`，再按火把版本号升序处理。定向补丁按当时的宿主源码保存。合并前以 `git apply --check` 核对上下文，发现差异时对照目标函数和实例字段合入。已经在仓库源码中直接更新的文件不需要再套这些补丁。双持选择、制作配方与火把物品定义可从仓库根目录直接取用。
- **村庄**　[场景消费者片段](Village)保留炉火、壁炬、烟囱、路灯、门窗和老教堂补光与本批有关的函数或片段。根据文件首行定位到宿主，按函数合入。`FireParticleView`、店员显示、树冠分级及建筑代理使用仓库中的对应源码。酒馆、民居和其他店铺的逐屋参数见[白天室内配置](Village/VillageRooms.json)。城墙裁切的两处迭代器修正另见[独立补丁](Integration/VillageGateCut.patch)。
- **旧资产恢复**　[正式包指纹](asset-fingerprints.json)覆盖魔晶剑身、两种握柄的检视与星髓充能、M24 枪身和枪托、Pit Viper 表面、工作台以及火把。长柄共用配置采用后续 GuardKuboldV24。M24 枪托材质和工作台的 NAS 包分别位于 `FPS3D/M24/ComponentFinish20261121/M24-ComponentFinish-20261123.zip` 和 `FPS3D/Workstations/InteractionRecovery20261121/Workstation-InteractionRecovery-20261123.zip`。

## 检查与归档记录

本机正式编辑器模块已完成 R17 链接。此前的 [18 项隔离服务端检查](authority-cases.json)覆盖双持、手枪换弹、消耗品占用、扣费、命中和重复请求。实机双端、延迟、重连、夜间多人持火把仍待采样。最近一对村口 F6 数据保存在[帧时间摘要](Village/VillageFrameTimes.json)，朝外记录的 GPU 时间线未覆盖采样窗口。

[清理摘要](cleanup-summary.json)列出了可恢复移入 trash 的文件数量与字节数。F 盘制作批次保存逐文件原路径、目标、SHA-256 与保留替代物，NAS 副本位于 `FPS3D/WoodenTorch/ConversationCleanup-20261123/cleanup-manifests.zip`。本次仓库整理未运行编辑器或游戏。
