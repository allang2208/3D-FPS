# 丘陵城防、建造与修复

本批保存普通石墙和双扇木门、带城垛和步道的高墙、东西石门楼和升降铁闸、门旁固定石阶及玩家建造的折返石阶。村界墙段按编号存伤，玩家放置的构件按实例 GUID 存伤。高墙、铁闸、石阶的建模脚本与破坏表现保存在同一批次。

## 恢复顺序

| 顺序 | 内容 | 恢复方式 |
| --- | --- | --- |
| 1 | 基础村庄、修女建设、工匠工作站、世界流送及旧联机夹具 | 从 [VillageNetwork](../VillageNetwork20261118/README.md)、[村庄生命周期](../HillsVillageLifecycle20261118/README.md)、[丘陵地貌](../HillsScenery20261118/README.md)、[工匠村](../ArtisanVillage20261119/README.md) 和[店员宿主](../ConversationDelivery20261120/README.md)恢复所需前置。 |
| 2 | 城防专属源码、模型制作配方和导入工具 | [专属文件清单](Defense/source-index.json)列出 40 个 C++ 源／头文件、14 个工具、11 个设计或作者文件。按每条 `target` 恢复到项目同名目录。`existing` 中的 9 个工具可直接从所列 Git 路径恢复。 |
| 3 | 输入、HUD、网络扣费、建造和存档 | [共享接入清单](Integration/defense-hosts.json)给出源文件名、完整本机宿主的 LF SHA-256、片段行号和旧发布来源。7 份 `.patch` 提供具体 Git 基线上的功能差异，58 份 `.inc` 保存按函数合并的生产源码片段。旧批次 `Implementation` 下的联测源应先恢复到目标 `Source` 路径。 |
| 4 | 打包、建设树及按键 | 将[城防 Cook 项](Configuration/defense-cook.ini)合入 `Config/DefaultGame.ini` 的 PackagingSettings 段。建设图标的 UFS 项已在基线中。[输入和配置清单](Configuration/defense-input.json)列出原生按键、五个构件 ID、修复距离、费用和建设树键。 |
| 5 | 本机 UE 包、图标和入口地图 | [恢复清单](Defense/local-recovery.json)逐项记录源、旧版、置换备份及散列。恢复二进制制品时从清单所列的本机备份取回对应文件。 |

共享接入的 Git 比对基线为 `e8b7284d9b086f1ba10841cf368d0f4273bd3ad7`。`previously_published` 指向已保存对应代码的宿主或补丁，`spans` 的行号来自采集时的本机宿主。后来改动过的共享文件按函数合并，保留其他调用方。旧 `VillageDefenseGate-methods.cpp.inc` 的 `PostNetInit` 与现行方法相同；门扇碎裂与快速修复采用本批 `VillageDefenseGate.cpp`。

## 玩家操作与联机接入

- 修女建设树中的「修复围墙」开启高墙升级，「村庄修建」解锁 B 键面板的「村庄建筑」。房主可以从 F6 重置村庄升级。
- 地面放置时滚轮每格正反旋转 1°，R 快速旋转 90°，F 切换吸附。指向城防接口时，滚轮选择接法。固定石阶按东西门的村内通路布置，玩家石阶另作入口占位判断。`VoxelBuildNetwork` 和 V15 至 V17 的存档记录衔接地面朝向和对接姿态，建造事务回滚时保留各玩家的撤销历史。
- 在 2.5 米内对准缺口按 E，普通和建造模式共用 `RequestVillageRepair`。服务器复查角色、目标、余额和受损构件，敌方单位距构件表面 15 米内会阻止修复。墙与石阶默认 100 灵魂，木门和铁闸 150 灵魂。修复回执防止旧客机资料退回已经支付的灵魂。
- 缺口使用绿色半透明预览，轮廓和状态栏复用本地焦点，显示生命和生效减益。修复通知上行为金色标题，下行为白色正文，重复提示刷新显示时间。快速修复时木门、铁闸与配重更新至闭合姿态。
- 村庄工作台通过 `IsSceneStation()` 与玩家放置的构件区分。客户端重建预制构件索引、服务器回滚建造快照时保留固定工作台。工作台的交易、木工和炼药会话见对应店铺宿主。

## 本机资产与既有记录

11 月 21 日的抢救回执记有 32 个从最终发布物写回的 UE 包。另有 3 个 `.meshzip` 和 2 个 JSON 已匹配发布散列。八张建设图标分别保留原始字节恢复、从源图导出以及原本正确的记录。入口地图从保留的旧图按配方重建，带回 22 项原有游戏引用和 1 个带标签的导航边界。最终原始入口地图包仍缺，清单同时记录重建地图和原发布的散列。

城垛制作批次在 `F:/FPSGAMEData/ArtProduction/VillageBattlementFit/20261120-231611-039`，铁闸修补在 `F:/FPSGAMEData/ArtProduction/VillageGrilleRepair/Run-20261120-A`。原始网格、PBR、作者中间模型、引擎内容、旧版游戏门声音源及其使用许可仍依赖本机目录或独立备份。墙身和铁闸保有 Meshy 多视图母版。最终门楼回廊和折返石阶使用工程内的几何配方。

11 月 21 日联机汇总 `Saved/VillageNetworkAudit20261118/delivery-20261121/summary.json` 记录真实 UDP 的 21 项用例，`Saved/Review/VillageAudit20261121/project-local/result.json` 记录 216 项本地检查。`Saved/Review/VillageAudit20261121/delivery.json` 另有三名客户端抢修、角色资料接入期间修复、铁闸和木门快速重建的结果。这些均为原有运行记录。本次整理未打开 UE、编译或运行测试。城防图形效果、跨机器公网及公开源码子集尚无本轮实机验收。
