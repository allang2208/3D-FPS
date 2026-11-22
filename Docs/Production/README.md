# FPSGAME 制作目录与功能索引

**第一条　先查功能位置，再创建文件或写引用。** 从当前副本的 [FPSGAME.uproject](../../FPSGAME.uproject) 进入，在下方找到所属功能、可编辑原件和正式使用位置；新增功能沿用下表的分类。引用写法统一见[工程存储规则](../../WORKFLOW.md#引用路径)。交付后在同一条记录更新实际用到的源、产物与恢复位置。

## 文件放在哪里

| 文件用途 | 默认位置 |
|---|---|
| 代码、项目配置、开发工具、文档、版本历史 | `D:/FPS3D/FPSGAME/` 下已有的 `Source`、`Config`、`Plugins`、`Shaders`、`Tools`、`Docs`、`.git`。 |
| 模型、材质与贴图、声音、图标等可编辑源 | Blender、Substance 工程、PBR 原图、录音母带、用于重导入的 FBX、来源说明和许可归入所属功能的制作源。统一从工程 `SourceAssets/<功能>/` 或该功能已登记的源根取用；新增大体量原件使用 `F:/FPSGAMEData/ArtProduction/SourceAssets/<类别>/<功能>/`。跨盘时登记工程入口及实际目标。 |
| 正式 UE 包和游戏数据 | 工程 `Content/` 实际位于 `F:/FPSGAMEData/Content/`。导入后的网格、材质、材质实例、纹理、声音和地图归入所属功能已有的 Content 目录，以 UE 包名引用。运行时直接读取的 JSON、PNG 等保留对应子系统的相对路径。 |
| 独立制作宿主、当批版本的输出、发布回执 | `F:/FPSGAMEData/ArtProduction/<功能>/<批次>/`。修改已收录的功能时沿用已有批次结构。 |
| 截图、对比图、审查记录 | `F:/FPSGAMEData/ArtReviews/<功能>/<批次>/`。如果图片是仍在使用的原始贴图或设计输入，则归入制作源。 |
| 可交付的打包版本 | `F:/FPSGAMEData/Builds/<版本>/`。主工程的编译模块由原来的 `Binaries`、`Intermediate` 流程管理。 |
| 可重建的制作中间文件与引擎缓存 | 制作工具的可重建缓存使用 `F:/FPSGAMEData/Caches/Authoring/<功能>/`。UE 派生缓存使用 `F:/FPSGAMEData/Caches/DerivedDataCache/`，其中 Zen 和虚拟纹理块分别使用 `Zen/` 和 `VT/`。引擎构建目录、存档与自动保存仍按各自的用途管理。[工程存储规则](../../WORKFLOW.md#41-存储分配与文件操作边界) |
| 可恢复的版本 | Y 盘 NAS。登记实际备份批次和包内相对路径。E 盘可继续存放引擎、外部工具、独立旧项目和本次保留的原件。 |

功能目录沿用工程已有英文名，例如 `HillsVillageBakery`。同一功能下的新制作批次可用 `YYYYMMDD-HHmmss`，不同工序可以沿用其既有名称。将可以再次编辑的源和已生成的 UE 包分别登记，避免只留下成品找不到配方。需长期维护的文件直接放到上表对应的项目子目录。

## 已登记的功能

| 功能 | 编辑与接入入口 | 正式路径与恢复线索 |
|---|---|---|
| 武器 · 双弓弹道、观峰与光束弓弦 | [双弓参数](../../Content/ColdSteelData/bows.json)、[改造目录](../../Content/ColdSteelData/bow-gunsmith.json)、[变倍镜材质](../../SourceAssets/SharedPhysicalOptics20261030/peakwatch_clear_lens.py) | [双弓与锻钢双手剑发布及恢复](../Publication/BowSwordConversation20261122/README.md)。含箭矢与弦影箭下坠及衰减、观峰固定准星、弦身外观、雪山三段累计及主客机记录。 |
| 武器 · 锻钢双手剑及专属改造 | [部件配置](../../Content/ColdSteelData/forged-steel-greatsword-modules.json)、[改造目录](../../Content/ColdSteelData/melee-gunsmith.json)、[原厂图标、握柄和材质版本](../Publication/BowSwordConversation20261122/appearance-recovery.json) | [双弓与锻钢双手剑发布及恢复](../Publication/BowSwordConversation20261122/README.md)。含镂空、处刑剑身、环链横扫与鱼尾配重。 |
| 武器 · 通用大马士革钢与材质改造 | [斩马刀 V3 原纹场](../../SourceAssets/ZhanmadaoDamascus20261111/ReferenceRefinementV3)、[双手武器钢面配方](../../SourceAssets/SharedTwoHandMaterials20261101/damascus_v3.py)、[符文剑原生材质](../../SourceAssets/SharedTwoHandMaterials20261101/azure_native_finishes.py)、[斩马刀旋风钢面](../../SourceAssets/ZhanmadaoDamascus20261111/temporal_finishes.py)、[正式材质栏](../../Content/ColdSteelData/melee-gunsmith.json) | [正式包、改前备份、材质槽与同机位对照](F:/FPSGAMEData/ArtReviews/SharedTwoHandMaterials/AllFinishes-20261122/summary.json)。 [源码与正式包版本](../Publication/SharedTwoHandMaterials20261122/README.md)、[本批归档清单](F:/FPSGAMEData/trash/SharedTwoHandMaterials-20261122/cleanup-manifest.json)。本批正式包以 11 月 22 日 SHA-256 清单为恢复依据，NAS 版本待登记。 |
| 丘陵村庄 · 城墙、城门与石阶 `HillsVillageDefenses` | [村防专属源码与制作目录](../Publication/HillsVillageRepair20261121/Defense/source-index.json)、[多人修复和建造接入](../Publication/HillsVillageRepair20261121/defense.md)。 | 正式 UE 资产盘为 `F:/FPSGAMEData/Content/`。墙身、门楼、铁闸、石阶、图标和入口地图的原包及恢复路径见[本机资产回执](../Publication/HillsVillageRepair20261121/Defense/local-recovery.json)。 |
| 丘陵村庄 · 铁匠铺、木工坊与草药铺 `HillsVillageShops` | [炉火与铁砧照明](../Publication/HillsVillageRepair20261121/ShopSurfaces/HillsBlacksmith.cpp)、[驱动水晶材质](../../SourceAssets/WoodworkingCrystalBench/Surfaces/author.py)、[药瓶材质](../../Tools/WorldGeneration/VillageHerbalist/vessel_finishes.py)、[炼药台材质槽绑定](../Publication/HillsVillageRepair20261121/ShopSurfaces/herbalist-workbench.patch) | 丘陵村庄修复后的店铺使用 `/Game/Building/WoodworkingCrystalBench/Surfaces/M_WorkshopDriveCrystal` 和 `/Game/Building/PotionWorkbench20261015/V1/HerbalistVessels/`。[水晶制作批次与原包](F:/FPSGAMEData/ArtProduction/WoodworkingCrystalBench/20261121-Facets)、[药瓶发布回执](F:/FPSGAMEData/ArtProduction/VillageHerbalist/VesselFinish20261121/published.json)、[同机位对比与原图归档](F:/FPSGAMEData/trash/HillsVillageShops-20261121/ArtReviews/HillsVillageShops/20261121-Materials)、[村庄修复系统与制作源恢复说明](../Publication/HillsVillageRepair20261121/README.md)。本版已收录于[晚间恢复增量](Y:/FPSGAME_晚间恢复增量_20261121-222741/Metadata/phase1-files.jsonl)。 |
| 丘陵村庄 · 草药铺药瓶 `VillageHerbalist` | [瓶身与药液材质配方](../../Tools/WorldGeneration/VillageHerbalist/vessel_finishes.py)、[炼药台材质槽接入](../Publication/HillsVillageRepair20261121/ShopSurfaces/herbalist-workbench.patch) | `/Game/Building/PotionWorkbench20261015/V1/HerbalistVessels/` 已发布 6 个材质实例及 2 个父材质。[本地发布清单与 SHA-256](F:/FPSGAMEData/ArtProduction/VillageHerbalist/VesselFinish20261121/published.json)。本版已收录于[晚间恢复增量](Y:/FPSGAME_晚间恢复增量_20261121-222741/Metadata/phase1-files.jsonl)。 |
| 丘陵村庄 · 面包房 `HillsVillageBakery` | [制作源](../../SourceAssets/HillsVillageBakery)、[建筑与安装工具](../../Tools/WorldGeneration/VillageBakery) | [部件、关卡、正式包、来源和 NAS 对照](./丘陵村庄面包房-资产与恢复索引-20261121.md)。该页还标出了共用浮雕墙和村庄关卡。 |
| 装备 · 背包适配 `BackpackFit20261024` | [工程逻辑入口](../../SourceAssets/BackpackFit20261024)、[制作工具](../../Tools/BackpackFit)。已生效的物理位置为 [F 盘装备制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/Equipment/BackpackFit20261024)。 | `/Game/Characters/BackpackFit20261024/<版本>/`。迁移前完整快照中的 [背包源文件](Y:/FPSGAME_完整工程_20261121-1412/External/E/CodexAssetCache/FPSGAME/BackpackFit20261024) 保留当时的 E 盘相对路径。 |
| 装备 · 战术弹挂 `TacticalMagazineBelt20261024` | [D 盘制作目录](../../SourceAssets/TacticalMagazineBelt20261024)、[导出工具](../../Tools/TacticalMagazineBelt/prepare_delivery.py)、[图标配置](../../Tools/BeltIcons/policy.json)。D 盘父目录保管可编辑源和导出；其中 `Delivery` 已转到 F 盘；该交付目录及独立图标场景见[弹挂制作源目录](F:/FPSGAMEData/ArtProduction/SourceAssets/Equipment/TacticalMagazineBelt20261024)。 | `/Game/Characters/ModularOutfit20260924/TacticalMagazineBelt20261024/`。迁移前完整快照独立收录了 [Delivery](Y:/FPSGAME_完整工程_20261121-1412/External/E/FPSGAMEAssetCache/TacticalMagazineBelt20261024/Delivery)。该条回执的覆盖范围是这一个子目录。 |
| 丘陵村防 `HighVillageDefense` | [原始模型和制作源](../../SourceAssets/HillsVillageHighWall20261120)、[生成与导入脚本](../../Tools/WorldGeneration/HighVillageDefense)。默认从 [F 盘派生缓存](F:/FPSGAMEData/Caches/Authoring/HighVillageDefense/Reduced) 读取简化模型；今后导入宿主写到 `F:/FPSGAMEData/ArtProduction/HighVillageDefense/`。 | `/Game/WorldGeneration/TemperateHills/HighVillageDefense/`。[本次转存清单](F:/FPSGAMEData/ArtProduction/StorageLayout/20261121-DualDrive/copy-summary.json) 记录已核对的 3 个简化模型，D 盘保有原始模型。 |
| 旧 Godot FPS 制作源 `LegacyGodotFPS` | [工程入口](../../SourceAssets/LegacyGodotFPS)联接至 [F 盘制作源](F:/FPSGAMEData/ArtProduction/SourceAssets/LegacyGodotFPS)。[音频原件](../../SourceAssets/LegacyGodotFPS/_Recovery/audio.json)、[背包图标来源和版本](../../SourceAssets/LegacyGodotFPS/_Recovery/inventory.json)与[弹鼓原场景缺项及现有可编辑稿](../../SourceAssets/LegacyGodotFPS/_Recovery/m4.json)分别登记。 | 脚本使用工程相对入口。三份雨声和八份 AKM 录音已找回。M4 弹鼓的 UE 适配场景及 FBX 在 [M4Drum20260909](../../SourceAssets/M4Drum20260909)，重跑上游构建和检查仍需原 Godot 场景。[收尾备份与目录联接](Y:/FPSGAME_晚间恢复增量_20261121-222741/Metadata/还原说明.txt)。 |
| 旧项目素材复用 `LegacyGameDev` | 历史原件在 E 盘。16 个制作脚本目前从 [F 盘制作输入](F:/FPSGAMEData/ArtProduction/SourceAssets/LegacyGameDev) 读取丘陵沙漠 BGM、中转加载画面、技能和其他所需资料。 | [逐文件来源、SHA-256 和使用它的脚本](F:/FPSGAMEData/ArtProduction/SourceAssets/LegacyGameDev/_Migration/20261121-source-map.json)；正式输出随各功能登记。 |

背包和弹挂的两处制作源联接已切换到 F 盘。弹挂审查入口也已指向 [F 盘审查插件](F:/FPSGAMEData/ArtReviews/TacticalMagazineBelt20261024/Plugin/TacticalBeltReview)，输出按审查批次登记。E 盘保留原件。这两处联接已收录于 [19:40 整理增量](Y:/FPSGAME_DF整理增量_20261121-1940/Metadata/完成报告.json)。[迁移完成记录](F:/FPSGAMEData/ArtProduction/StorageLayout/20261121-DualDrive/complete.json)

## 新功能如何登记

在上表添加一行，或链接到功能已有的文档。简单功能在一行内给出所需位置即可。涉及多部件、多个来源或多次发布时，可沿用面包房样板，在功能页填写下列内容。

| 字段 | 要留下的信息 |
|---|---|
| 功能名、编辑入口 | 稳定功能名，以及开发者下次应打开的工程文件、原始场景或工具。 |
| 制作源与关键依赖 | 可编辑原件、导出物、导入脚本、来源或许可；跨盘记录逻辑入口和实际目录，复用资产记录其所属功能。 |
| 正式输出与使用位置 | 完整 `/Game/...` 包名或源文件路径，以及使用它的地图、配置或代码。 |
| 批次与发布状态 | 对应的输出目录和回执，注明已制作、已落盘或已发布的实际阶段。 |
| 恢复位置 | 已取得的 NAS 快照名、备份内相对路径；需先使用完整备份再覆盖增量时，一并记录两者。还没有对应版本时写“待备份”。 |

## 存储资料

- [11 月 21 日晚间恢复增量](Y:/FPSGAME_晚间恢复增量_20261121-222741)保存了晚间正式资产、制作源、发布回执、[最新恢复总表](Y:/FPSGAME_晚间恢复增量_20261121-222741/RecoveryRecords/11月待重新开发清单.xlsx)及 Fab 草地库原版风参数材质。恢复整套工程时，按[还原说明](Y:/FPSGAME_晚间恢复增量_20261121-222741/Metadata/还原说明.txt)在 19:40 基础上叠加两阶段文件，并接回新的制作源目录联接。
- 两批 Fab 下载的[清理回执](Y:/FPSGAME_D盘Fab清理凭据_20261121-221445/result.json)、[逐文件补回清单](Y:/FPSGAME_D盘Fab清理凭据_20261121-221445/fab/restore-map.jsonl)和[补回工具](Y:/FPSGAME_D盘Fab清理凭据_20261121-221445/fab/Restore-Files.py)收录了 1,312 个重复文件。保留的 1,823 字节 [PN_WindParameters.uasset](Y:/FPSGAME_晚间恢复增量_20261121-222741/External/D/FPS3D/VaultCache/interactb6925a747911V3/data/Content/PN_GrassLibrary/Materials/PN_WindParameters.uasset) 恢复到原 Fab 下载路径。

- D 盘 `SourceAssets` 内的旧制作宿主需要恢复 `Content` 时，使用[旧制作宿主补回说明](Y:/FPSGAME_D盘清理凭据_20261121-215321/host/还原说明.md) 选择宿主名。[D 盘逐包清单](Y:/FPSGAME_D盘清理凭据_20261121-215321/host/restore-map.jsonl)记录战术衬衣、变异怪等 8 个宿主的原路径、正式包和 NAS 版本。

- 旧恢复宿主要重新载入插件或编辑原始模型、贴图时，可按宿主名和类别补回缺失文件。[制作源与插件补回说明](Y:/FPSGAME_F盘清理凭据_20261121-210628/host/还原说明.md)和[逐文件原位置、NAS 位置及 SHA-256](Y:/FPSGAME_F盘清理凭据_20261121-210628/host/restore-map.jsonl)对应 21:06 批次。宿主的 UE 资产包使用下一条中的 19:58 批次。

- [11 月 21 日 F 盘清理及补回说明](F:/FPSGAMEData/ArtProduction/StorageLayout/F-Cleanup-20261121-195846/清理与还原.md)登记了本轮清理的宿主、缓存和备份操作文件。[NAS 清理凭据](Y:/FPSGAME_F盘清理凭据_20261121-195846)保留逐包映射及补回工具。重开旧宿主时先按宿主名补回依赖，继续开发仍从 D 盘正式工程进入。

- [四盘目录盘点](./项目目录索引-20261121.md) 保留历史目录、外部依赖及 11 月备份覆盖表。
- [D/F 迁移回执目录](F:/FPSGAMEData/ArtProduction/StorageLayout/20261121-DualDrive) 记录本次复制和入口切换；历史快照使用当时的联接记录。
- [工程存储规则](../../WORKFLOW.md#41-存储分配与文件操作边界)维护目录和引用写法。[工程智能体入口](../../AGENTS.md)及[工程技能入口](../../skills/ue5-auto-assistant/SKILL.md)将其列为第一条；本机对应技能位于 `%USERPROFILE%/.codex/skills/`。本次首条规则、工程与本机技能及项目索引已归入 [11 月 21 日存储规范与技能增量](Y:/FPSGAME_存储规范与技能增量_20261121-225937/Metadata/完成报告.json)。
