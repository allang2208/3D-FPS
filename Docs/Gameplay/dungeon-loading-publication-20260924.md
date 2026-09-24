# 地牢与进入游戏加载：源码整理

本次从 `D:/FPS3D/FPSGAME` 整理本对话完成的地牢改动：地下 Boss 路线、短连接与形状变体、装配碰撞和分段显现、杂物堆叠、栏杆/拖车/机械门、最终宝箱出口、墙面升级与稀疏水渍，以及快速/完整两档进入方式。

共享的玩家控制器、世界交互、准星提示和手脑怪源码只暂存地牢/加载相关部分；其他并行功能保留在工作区。正式发布内容为源码、作者脚本、配置、文档和技能，不包含整个本机工程的二进制备份。

## 归档

七个已完成用途的一次性停止试玩、关闭编辑器和 Live Coding 辅助脚本，以及一份已被正式路线目录替代的宝箱房目录快照，共八个文件移入 `trash/dungeon-loading-publication-20260924/`。原路径、归档路径、大小、SHA-256、原因与替代入口见 [归档清单](dungeon-loading-archive-20260924.json)，移动后已核对散列。trash 不进入 Git。

宝箱房的 `Config/catalog-candidate.json` 只有生成入口，没有消费入口；正式配置为 `DungeonRoutes20260922/Config/catalog.json`。后续调试快照改写入本机忽略的 `Receipts`，避免旧的完整目录副本被误当作当前配置。

旧材质对照、发布前备份、当前恢复脚本依赖、已采用模板和来源记录继续保留，不能仅按旧日期或名称含 candidate/before 判断为废案。旧模板材质入口仍被现有资产引用，其升级脚本是有效依赖。

## 恢复边界

- 地图、网格、动画、材质与贴图从完整本机 Content 恢复，遵守 [AssetSetup](../AssetSetup.md)。包含 `GameMaps/L_Dungeon_Randomized`、相关 `Dungeons/*` 和 `Monsters/HandBrain`。
- 新主墙依赖 `DungeonWallUpgrade20260924` 的 Poly Haven 扫描、已取得的 Fab 破损混凝土及作者纹理；Fab 原图和派生图不公开分发。原始来源/许可和导入回执保留本机。
- 地牢油桶、蛛网等七件摆设沿用既有来源记录，并补齐 [CC BY 署名声明](../../ThirdPartyNotices/DUNGEON_ART_PASS.md)。本次不分发它们的网格或贴图。
- 稀疏水痕由 `DungeonWallStains20260924/Scripts/author_masks.py` 自制；后台 `install.py` 更新三个既有材质入口。公开脚本，不上传生成 PNG 和 uasset。
- 目录扩展器会读取各阶段的本机导入/保存回执；远端源码不伪造这些成功标记。恢复完整本机依赖，或按作者顺序重新导入后，才重建地图目录。
- 两档加载入口是当前地图上覆盖式主界面，代码不依赖新启动地图；完整档仅准备当前收集到的场景与装备，未来区域及虚拟纹理页面仍遵守引擎流送。

## 技能沉淀与交付状态

新增 `ue5-pcg-building/references/dungeon-surface-authoring.md`、`ue5-performance-packaging/references/entry-resource-preparation.md`，并从 PCG、性能和 UI 技能入口链接。补充三维占位、短接头与地下终点规则；个人技能与工程镜像同步。

此前两档加载和水渍调整的游戏/编辑器目标均完成必要构建，材质已保存。此次整理只做归档、推送前的差异/大小/敏感信息与许可范围检查；没有重新运行游戏、PIE、视觉或性能测试。具体外观仍由用户验收。
