# 档案出口与货运专用池修复

2026-10-02 更新：用户要求全部战斗房刷怪后封门，下文关于“普通清路房开放、推进房入口开放”的实现已被 [全战斗房封门规则](dungeon-all-room-gates-20261002.md) 替代；专用货运池和任意一路完成的条件继续保留。

## 用户运行证据

2026-10-01 的 Seed=1018900784，RunId=1018900784-F1FCC459：货运连接房 Node=51 在 14:59:12 UTC 清除并记录闸门放行；地下车站 Node=57 在 15:02:41 清除；档案中心 Node=33 在 15:09:26 清除后，没有对应出口放行记录。

出口代码同时要求本房清除和 `AnyThemedRouteCleared()`。仓库节点 54 只记录了两个 FatZombie 生成，目录编成为 4–6 只；两只已生成胖子的击杀有记录，但该房没有清除记录。上一轮只将带推进闸门的房间改为进房遭遇，遗漏了同样参与整条路线清除判定的普通仓库与过渡房。这些房仍受 1500 cm 玩家距离、视线和普通刷怪名额限制，存在未生成槽位一直等待的问题。

本轮保留“任意一条完整分支清除，再清除档案中心”的 Boss 门条件，不将仅走过房间当作击杀，也不要求三条路线全部清除。

## 实现

- `DungeonRunSubsystem::ParseCatalog` 在已有运行时配置副本上派生主题清路标记；导演仅对 `Route1`/`Route2`/`Route3` 战斗房启用整组进房遭遇。公共入口前段、连接坡道/通道和 Boss 独立系统不改。
- 普通清路房采用开放遭遇，不额外生成格栅；原精英房和 `sealed_encounter` 主题房继续封门；自带推进闸门的货运房、档案中心仍保持入口开放。
- 整组沿用确定性编成、品阶、等级、原落点、导航/碰撞校验、全局存活预算和遭遇容量预留。零怪波次与无候选落点沿用已明确的结束路径；真实失败沿用有界重试，不丢失清除责任。
- 档案已清但路线仍未清时，推进门只记录一次各分支缺少清除的节点与房型，不每次 Tick 刷日志。

## 货运随机池

`DungeonThemedRoutes20261001/Scripts/extend_catalog.py::restrict_freight_to_theme` 负责同源修改：

- 从随机 `room_ids` 移除 `FreightTransfer` 家族，禁用其随机选取；旧模型和作者模块保留，作为专用版制作来源，不删除共用资产。
- `transition_families` 保留 Distribution / Drainage / ShoredBreach / VentilationLoop。
- `FreightTransfer_WarehouseLink` 保留一次固定核心房用途，添加非通用路线选择限制；主题配置阶段依照固定组合启用。固定顺序仍为货运装卸房 → 货运仓库 → 地下车站。
- 必须保持这一步处于目录重建的最终结果中，避免以后重导恢复普通货运房。

正式地图只改生成器目录字段，使用后台 `save_freight_route_only.py`，不重导模型、不执行生成，也不修改已认可房间摆设。保存前在 `Backup/FreightRouteOnly` 保留原地图与目录；保存后同步 ThemedRoutes / SplitLevels / DungeonRoutes 三份生产目录。

## 交付

后台 Editor 构建已成功并链接，日志 `Saved/BuildEditor/dungeon-archive-route-clear-retry-20261001.log`。正式地图已由后台 commandlet 保存，三份生产目录已同步；回执 `SourceAssets/DungeonThemedRoutes20261001/Receipts/freight-route-only-20261001.json` 的阶段为 `map_saved`，本次移除的普通房 ID 为 `FreightTransfer`，过渡池为四类。保存日志 `Saved/Logs/DungeonFreightRouteOnly-20261001.log`，commandlet 返回 0。

未运行新种子、战斗、开门、行走或渲染测试；没有启动可视编辑器。实际效果由用户重新出征体验，旧局的已规划波次不会自动重排。
