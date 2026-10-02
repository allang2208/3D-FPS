# 地牢宝箱仓库式取物面板（2026-10-02）

用户指令：随机地牢宝箱开箱不再直接发放奖励、不再播报提示栏；改为弹出与仓库宝箱一样大的面板（同格子数、默认一页），里面刷新本箱战利品，玩家拖动或交互拾取，交互规则与现有仓库完全一致、直接复用。

## 玩家可见行为

- E 开箱：开盖动画照旧播完 → 弹出抽屉左侧的仓库面板，标题「宝箱战利品」，一页 18×12=216 格（与仓库宝箱单页同尺寸），内容为本箱 roll 出的战利品。
- 取物与仓库完全同款：单击查看浮窗、右键取出（默认动作）、Shift+单击拆分、拖拽进背包格、整理按钮（SortWarehouse 作用域=当前会话容器）。离开宝箱 240cm 自动关面板（与仓库 InteractionRadius 同值同规则）。
- 已开启的宝箱保持 E 可交互：准星提示「探险宝箱/最终宝箱 · 打开战利品」，按 E 重开面板（不重 roll）。
- 失败路径：战利品写入失败（存档事务失败）＝未领取，宝箱保持可重试（重开动画后重 roll——roll 流按运行种子可复现，结果一致）。

## 实现合同

- **容器**：`DungeonChest.<领取键>`（领取键=MissionId/Node<N>+`.chest`/`.final_chest`，`DungeonChestClaim.` 标签可覆盖）——与旧领取标记同一推导，存档里以 `FColdSteelItem.Place=4 + Container` 归属，`StoragePages` 首次开箱登记（只增不减）。
- **roll 与发放**：`FColdSteelDungeonLoot::StoreFromChest`（原 GrantFromChest 改造）——节点解析、档位、种子流、合并计数全部不变；末段从 `GrantDungeonReward`（直接进背包+PostNotice）改为 `UColdSteelStatusModel::StoreDungeonChestLoot`（写容器+同事务打领取标记，不播报）。`HasDungeonClaim` 先查后 roll：重复开箱不重 roll（roll 可复现但弹药条目重写会重复入池）。
- **弹药口径**：`dungeon_loot.json` 里 ammo_* 词条按全局拾取口径**直接入弹药池**（`AddAmmoToState`）——弹药物品在本项目只作为地面/宝箱暂存态存在，储物域从无弹药物品；非弹药（金币/药水/强化石/卷轴等）进面板。
- **弹药物品出箱**：宝箱容器里的弹药物品被取出（右键/拖拽进背包）时＝转弹药池并从箱内消失（`ConvertChestAmmoToPool`，挂 `TransferWarehouse` 与 `MoveItem` 两个提交入口，与地面拾取 Pickup 的转换同一口径）；箱内拆分/堆叠照常。
- **面板开启**：`UColdSteelHUDWidget::OpenChestLootStorage(Anchor,Key,Pages=1,Caption)`——复用 `OpenWarehouse` 全套，差异三点：不做新手军械/强化补给发放、不播宝箱开合动画、离开判据走通用锚点 `WarehouseAnchor`（与 WarehouseChest 互斥，TickWarehouse 按 240cm 距离自动关）。
- **重复开箱链路**：`OpenTreasureChest` 对 Opened 箱不再拒绝，直接 `OpenChestLootPanel`（与开箱完成 lambda 共用，键来自 `FColdSteelDungeonLoot::ChestStorageKey`）。

## 坑与边界

- 主仓库与储物箱会话互斥：开战利品面板前 `WarehouseChest.Reset()`；关闭路径两条（手动/超距）都要复位 `WarehouseAnchor`。
- 跨运行残留：上一局没取完的宝箱战利品按容器键持久保留，下一局同键容器叠加显示——宝箱容器是持久私藏格，不是临时的。
- `GrantDungeonReward/AppendDungeonReward` 保留：AppendDungeonReward 仍被 `DungeonRunSubsystem` 通关奖励使用；Grant 当前无其他调用方。

## 主神空间测试宝箱（2026-10-02 追加）

用户指派：主神空间出生点旁放一只地牢宝箱方便实测。实现＝运行时生成（`AFPSGAMEPlayerController::SpawnHubTestChest`，BeginPlay 在 Hub 地图调用），不改 umap：

- 结构与地牢生成器同口径：`ASkeletalMeshActor` + `SK_GamedevTreasureChest`（闭合姿态冻结）+ BlockAll 盒体（尺寸取 treasure_chest_assets.json），标签 `DungeonTreasureChest` + `DungeonChestClaim.HubTest`（稳定领取键）。
- **`DungeonTreasure.HubTest` 标签＝无运行豁免**：`ResolveChestContext` 放行非运行场景（Depth 0 档；种子用领取键散列固定，`StoreDungeonChestLoot` 的 RunId 匹配对测试箱豁免）。正式地牢宝箱不受影响。
- **取空自动重 roll**：测试箱领取标记在案且容器已空时，`ReleaseHubTestClaimIfEmpty` 清除标记，本次开箱重新 roll——可无限反复实测；箱内还有余量则只开面板不重 roll。
- 每局（每次进入 Hub）生成一只，去重靠标签扫描；撤销＝删 `SpawnHubTestChest` 调用点一处。
