# 功能模块归属与统计

统计日期：2026-11-16。文件数和行数仅来自 Source/FPSGAME 的元数据盘点；不代表每个文件已经阅读。八大模块最多再细分两级，职责叶节点见主报告。

| 大模块 | Source/FPSGAME 目录 | 文件数 | 行数 | 超过 800 行 | 工具与数据入口（不计入本表规模） |
| --- | --- | ---: | ---: | ---: | --- |
| 01 玩家与动作 | Characters, Movement | 209 | 31,095 | 4 | Tools/PlayerBody、GarmentWaist、ModularOutfit；player_body.json |
| 02 武器与战斗 | Combat, Weapons, Skills | 913 | 141,200 | 18 | Tools/Weapons、Bow、Skills、Combat、Fluids；武器和技能目录 |
| 03 敌人与 NPC | Monsters, NPC | 463 | 64,127 | 3 | Tools/Monsters、MonsterAI 及具名怪物制作目录 |
| 04 世界与建造 | Building, WorldGeneration, Water, Props, Dungeons | 360 | 60,377 | 9 | Tools/Building、WorldGeneration、Dungeon、Dungeons、Weather；Shaders；根层 FPSUDS*/Weather* |
| 05 物品与生产生存 | Items, Production, Survival | 177 | 20,292 | 1 | Tools/Items、Production、ProductionTools、Forging、Smelting、Consumables；配方和生存配置 |
| 06 界面与任务显示 | UI, Tasks | 434 | 72,335 | 9 | Tools/UI、MapMarkers；UI-WORKFLOW、TASK-WORKFLOW |
| 07 联机与持久化 | Multiplayer, Dungeon | 64 | 11,288 | 2 | Plugins/ColdSteelNet；Tools/Multiplayer；档案配置及兼容结构 |
| 08 平台与开发工具 | Root, Development, Diagnostics, Rendering | 150 | 26,603 | 2 | Source/*.Target.cs、Source/ThirdParty、Tools/Build、AssetPipeline、Publication、Diagnostics 类工具；其余 Tools/SourceAssets 制作源按内容关联前七域 |

Root 表示 FPSGAME 根层，不是新增目录。天气门面、角色门面按统计位置暂归第八模块，职责关联前述模块；未来目录迁移再调整归属。

## 覆盖层次

- 目录与行数：上述全部 22 个子目录和根层，覆盖 2,770 个文件。
- 定向语义审阅：启动/Build.cs；Tasks/TaskTrackingSubsystem；Dungeon 兼容结构；Survival 计时；Combat 费用与控制免疫入口；Skills 奖励和准备；Multiplayer 协议及 WorldSubsystem；ColdSteelNet 插件；相关 UI/Characters 调用点。
- 拆分设计：48 个超过 800 行文件，按文件职责与有限入口制定初步方案，没有逐段完成依赖分析。
- 仅归属、未语义审阅：其余源码、Tools/SourceAssets 长尾、第三方插件、配置全量数据和着色器。
- 排除：Content 二进制、缓存、Saved 制作宿主、历史镜像、trash、引擎安装目录及其他 FPS3D 工程。

## 边界职责

- UI 只发意图和显示快照；任务完成、开门、资源扣除由玩法拥有者处理。
- 战斗共用公式不依赖具体面板，网络结算读取正确玩家的权威数据。
- 制作脚本生成的数据必须能追溯作者入口；不能仅拆生成结果。
- 当前代码存在跨目录引用，逻辑模块图不等于已经隔离的编译依赖；本轮没有改 Build.cs 或创建 UObject 类型。
