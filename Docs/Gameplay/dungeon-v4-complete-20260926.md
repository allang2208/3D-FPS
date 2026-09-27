# 地牢 V4 方案后续实施（清单版本 5）

日期：2026-09-26。承接 `dungeon-topology-v4-implementation-20260926.md`，本批完成此前单列的任务图、房间共享配方和多主门接入。构建与资产保存凭据在文末记录；未执行游戏、PIE、多种子遍历、寻路测试、截图或性能验收。

交付状态：Editor 常规构建成功（150.61 秒），Game 完整构建成功（138.49 秒），最终增量构建成功（23.67 秒）。三个封板网格已保存，十二配置普通房池和配方库已写入地牢生成器的外部 Actor 包。

## 路线与通道

- 先选任务规则、房数和分岔位置，再做几何放置。三种规则为同点三分岔、先左后右、先右后左；错开的分岔之间包含普通遭遇段，沿用两个三门 Junction 配方。
- 三个地下 Boss 入口继续存在；无需清完三路才进入 Boss。最终宝箱仍受原 Boss 战后门控制，回路候选仅连接普通支路房间。
- 任务边明确前段、探索、风险捷径、下行、汇流、Boss 奖励、返回和跨路用途。必需边必须在实际端口图中存在；可选边记录 `optional` 与 `realized`。几何放不下时允许没有额外回路，目标 1–2 条不是保证值。
- 每条普通连接仍为 12 m / 两转弯上限。风险路线偏短直连，探索路线允许更多遮挡转向；连续相同连接会增加代价。
- 全局连接总量同时计入直段、弯头、三个完整楼梯、Boss 接近段及宝箱前室。默认预算为固定 140 m 加每普通房 9 m。另有限制每路 420 m 的房间跨度估计；该值按房壳尺度和作者标定楼梯路线估算，**不是导航网格实测步行长度**。原地下末段 65 m 作者路线约束保留。
- 仍以 12 秒截止保护和有限候选控制搜索。前八次尝试所选错开分岔，之后尝试三分岔规则；实际规则写入清单。失败保留旧场景，不回退同层 Boss，不将不同机器的超时搜索结果宣传为严格同种子复现。

## 房间共享配方

新增 `room_recipe_library` 及 `AuthoredDungeonCatalog` 解析层。通风家族引用两个已有侧门外壳、三个已有设备布置，组成六个兼容配方；复用统一地板与顶板，不复制六套房间网格。五个现有空间家族继续使用，普通池共有十二个配置（其余六个配置加六个通风配方）。

每个通风房有三个真实门位，支持三组双向入口/出口配对。未参与路线的门用同一个新制封板闭合；需要回环或宝箱支线时才开放该门。原双主门房和独立侧门继续兼容。家族候选轮换按门位候选交错，避免门多的家族仅因候选数量增加而抢占搜索。

配方携带 `family_id`、`shell_id`、`interior_recipe_id`、`port_pairs`、`closed_port_parts`、`walk_mask` 与 `encounter_anchors`。外壳与内部组合有明确兼容表；导航/刷怪掩膜用于过滤可用环廊位置，仍由实际碰撞和导航投影决定能否落怪。生成器不会运行时切墙、拉伸普通房或取消碰撞。

封板源文件在 `SourceAssets/DungeonComposition20260926/`，复用现有项目材质。三组网格为 Shell / Tiles / Frames，覆盖门洞且在门框后留搭接。两个三门 Junction 也使用原四门 Junction 加同一封板，不新增完整房间资产。

没有为凑数量追加主题房：本批通过既有通风环廊和多门组合补入多入口战斗体验。A*、全局 WFC、任意节点度数任务图以及双入口地下终点属于提案中的条件扩展，不是本次实施依赖。

## 玩法、存档与缺陷

- 普通房获得 `Approach.n` / `RouteN.n` 逻辑身份；身份从本支路入口沿连接顺序分配，避免长支路从汇流处反向编号。设计推进阶段独立于回路之后的最短邻接距离。
- 较短中路使用风险角色、等级加成与末房精英遭遇；其他支路使用探索角色。导演读取角色，不再把三条固定 Route 名称当作精英规则；旧清单使用动态收集的路线分组兼容。
- 风险房有实际击杀后清房发放额外金币；侧室宝箱继承风险奖励倍率。清房状态、领取标记和奖励在同一份档案事务中提交，无怪成功落地不会凭空生成风险奖励。
- 宝箱奖励整体提交，物品进入背包、弹药进入弹药袋；背包不足的物品成为持久化地面掉落。领取记录按房间逻辑身份、宝箱角色和本地位置区分。保存失败允许重新交互，避免宝箱永久已开却没有奖励。
- 存档增加 `GeneratorVersion` 和实际 `LayoutManifestJson`。清单包含位置、旋转、连接件缩放、真实开门集合、房间配方、逻辑/物理图及最终选择的规则。保留原“进入生成新一局”生命周期；本批没有新增离开后继续同一局的入口。
- 继承首批修复：地下终点错误回退、零成本连接件深度计算、邻接穿越完整通道链、真实 cells 与门洞封锁、玩家进房前刷怪、共享活怪预算，以及四个 Earthwork 材质采样器修复。

核心代码：`AuthoredDungeonMission.inl`、`AuthoredDungeonCatalog.*`、`AuthoredDungeonGenerator.cpp`、`DungeonRunSubsystem.*`、`DungeonSpawnDirector.cpp`、`ColdSteelDungeonLoot.cpp`、`ColdSteelDungeonRewards.cpp`。

## 制作与接入凭据

- 本批制作：`Saved/DungeonV4Complete_20260926/author-seal.log`。
- 封板瓷砖的 1903 个塌缩 UV 三角面已在源文件重建平面 UV，使用 FBX 导入设置重算 Mikk 切线；最终重导保存日志 `asset-tile-uv-final.log` 为 0 错误，已无该网格的 FBX 切线警告。源制作日志为 `author-seal-uv.log`。不使用 commandlet 中不可用的 StaticMeshEditorSubsystem。
- 封板导入回执：`SourceAssets/DungeonComposition20260926/Receipts/import.json`；仅 `meshes_saved` 表示实际保存。
- 地图目录安装回执：`SourceAssets/DungeonComposition20260926/Receipts/install.json`；仅 `map_saved` 表示关卡外部 Actor 包已写盘。
- 本次实际保存包：`/Game/__ExternalActors__/GameMaps/L_Dungeon_Randomized/8/N2/KZ839Z5RGFD4Y0908097LH`。安装 commandlet 日志为 `Saved/DungeonV4Complete_20260926/asset-install.log`。
- 新目录来自地图当前生成器的 JSON 增量扩展；保留安装前 JSON，原生重建目录链末尾应用本批扩展，防止后续旧安装器抹掉配方。
- 本批 Editor / Game 构建日志：`Saved/DungeonV4Complete_20260926/build-editor.log`、`build-game.log`；末次增量 Game 构建为 `build-game-final.log`。

资产保存与构建成功仅代表交付已落盘，不代表布局成功率、视觉、战斗、寻路或性能已经测试。
