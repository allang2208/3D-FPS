# 冶炼点击与存档意图

2026-09-24。点击级操作（开始、加燃料、收取、升级、拆除）在同一次档案 `CommitState` 里写下 `FColdSteelSmeltIntent`，然后 `FlushPersistenceNow()`（内部 `TickPersistence(true)`）。挖掘等连续改动仍走约 2 秒合并的建筑存档，不要为它们每次都刷盘。

`AVoxelBuildWorld::Initialize` 末尾、tick 结算之前调用 `ReconcileIntents`。意图按 `BuildingWorldKey` 过滤。

- 开始：任务已在则丢掉意图；没有任务则退还矿石。
- 燃料：磁盘燃料仍接近扣前值则退还；已经烧掉或达到扣后值则丢掉意图，不再退。
- 收取、拆除：任务或燃料还在磁盘上就清掉，不再发第二次奖励。
- 刷新失败时，开始、加燃料、升级回滚世界并退还意图；收取、拆除留下意图，下次读档再对账。

材料只从背包和主仓库扣。箱子（`Place==4` 且 `Container` 非空）不参与冶炼、强化扣款和 `ConsumeItem`。`CountMaterial` 本来就不计箱子。
