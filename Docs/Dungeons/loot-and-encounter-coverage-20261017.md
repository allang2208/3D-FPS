# 随机地牢收集物与刷怪覆盖核对（2026-10-17）

按用户要求只读排查。直接读取正式随机地牢生成器已保存的 uasset 中 `ModuleCatalogJson`，与当前 `scene_search_loot.json`、`items.json`、实际 C++ 分派交叉核对；未运行游戏、测试地图或修改玩法配置。

## 结论

- 生活区 67 个普通搜索入口全部绑定：宿舍 36、更衣淋浴区 24、休闲厅 7。8 个生活区池首次搜索均固定 1 件，已生成或取空的箱子不补刷。
- 休闲厅厕所隐藏宝箱不是普通搜索柜，已启用并走 `dungeon_loot.json` 的通用宝箱掉落。
- 全目录 281 个唯一绑定身份（包含候选容器和病区床头箱动态族）、39 个搜索池、50 种搜索物品，未发现漏绑、未知池或缺失物品定义。281 不是每局实际容器数量。
- 六大主题区 18 间房与迎宾两厅均有怪物资源准备和实际遭遇分派；终末泵机大厅有合阙刷新和最终宝箱。
- 档案中心、Distribution 过渡房、通风环廊尚无普通搜索容器/收集物投放，也无怪物刷新分派。排水过渡房已有 2 个工具箱身份绑定，但尚无怪物刷新分派。
- 医疗第三间解剖教学剧场的后廊宝箱 `hospital_rear_gallery_treasure` 在正式保存目录中明确 `interaction_enabled=false`，生成时标记为 `DungeonTreasure.PendingLoot`，未进入可搜索宝箱流程。其普通搜索容器不受影响。

## 生活区普通容器

| 容器 | 数量 | 搜索池 |
| --- | ---: | --- |
| 床头柜 | 12 | staff_bedside |
| 书柜 | 6 | staff_documents |
| 书架 | 6 | staff_personal_electronics |
| 宿舍衣柜 | 12 | staff_personal_locker |
| 更衣柜 | 24 | staff_changing_personal |
| 茶水台储物柜 | 5 | staff_pantry |
| 冰箱冷藏室 | 1 | staff_refrigerated |
| 冰箱冷冻室 | 1 | staff_frozen |

内容包括食品、饮水、U盘、档案、硬盘及生活区四件收集物：珍藏香水、便携音乐播放器、袖珍数码相机、商务笔记本电脑。各类柜子的物品集合不同，不是每种柜子都会出全部物品。

## 全模块清单

“绑定数”是唯一配置身份；随机家具变体共享某些身份，每局会选部分候选，病区床头箱为一族多个实例。侧宝箱房由普通房侧接口机会追加，不因布局库主体未列出就当成已退役。

| 模块 | 区域 | 使用范围 | 普通容器绑定 | 怪物分派 | 宝箱 |
| --- | --- | --- | ---: | --- | --- |
| Distribution | 过渡区 | 正式布局库 | 0/0 | 无 | — |
| Drainage | 过渡区 | 正式布局库 | 2/2 | 无 | — |
| ShoredBreach | 焚化区 | 正式布局库 | 9/9 | 已接入 IsIncineration | — |
| Junction | 连接/保留模块 | 当前布局库未使用 | 0/0 | 无 | — |
| RouteEnd | 连接/保留模块 | 当前布局库未使用 | 0/0 | 无 | — |
| Transit | 连接/保留模块 | 正式布局库 | 0/0 | 无 | — |
| Threshold | 连接/保留模块 | 正式布局库 | 0/0 | 无 | — |
| Treasure | 连接/保留模块 | 可选侧室 | 0/0 | 无 | 通用宝箱池 |
| TreasureLink | 连接/保留模块 | 可选侧室 | 0/0 | 无 | — |
| VentilationLoop | 过渡区 | 正式布局库 | 0/0 | 无 | — |
| FreightTransfer | 连接/保留模块 | 当前布局库未使用 | 0/0 | 无 | — |
| RouteElbow | 连接/保留模块 | 正式布局库 | 0/0 | 无 | — |
| BossConfluence | 连接/保留模块 | 正式布局库 | 0/0 | 无 | — |
| BossApproach | 连接/保留模块 | 正式布局库 | 0/0 | 无 | — |
| BossPumpHall | 终点 | 正式布局库 | 0/0 | 已接入 IsFinalBossRoom | 最终奖励池 |
| StairDrop1080 | 连接/保留模块 | 正式布局库 | 0/0 | 无 | — |
| ForkLeft | 连接/保留模块 | 当前布局库未使用 | 0/0 | 无 | — |
| ForkRight | 连接/保留模块 | 当前布局库未使用 | 0/0 | 无 | — |
| AbandonedTransitStation | 货运区 | 正式布局库 | 7/7 | 已接入 IsFreight | 通用宝箱池 |
| AbandonedIsolationWard | 医疗区 | 正式布局库 | 11/11 | 已接入 IsMedical | — |
| AbandonedIncineratorHall | 焚化区 | 正式布局库 | 16/16 | 已接入 IsIncineration | — |
| AbandonedDataArchive | 档案中心 | 正式布局库 | 0/0 | 无 | — |
| AbandonedAnatomyTheatre | 医疗区 | 正式布局库 | 8/8 | 已接入 IsMedical | 待配置/关闭交互 |
| AbandonedFlueGasStation | 焚化区 | 正式布局库 | 15/15 | 已接入 IsIncineration | 通用宝箱池 |
| AbandonedCargoWarehouse | 货运区 | 正式布局库 | 45/45 | 已接入 IsFreight | — |
| FreightTransfer_WarehouseLink | 货运区 | 正式布局库 | 16/16 | 已接入 IsFreight | — |
| RouteRamp540 | 连接/保留模块 | 当前布局库未使用 | 0/0 | 无 | — |
| RouteRamp1080 | 连接/保留模块 | 正式布局库 | 0/0 | 无 | — |
| RouteRamp1620 | 连接/保留模块 | 正式布局库 | 0/0 | 无 | — |
| StaffDormitory | 生活区 | 正式布局库 | 36/36 | 已接入 IsStaffLiving | — |
| StaffChangingShowers | 生活区 | 正式布局库 | 24/24 | 已接入 IsStaffLiving | — |
| StaffRecreation | 生活区 | 正式布局库 | 7/7 | 已接入 IsStaffLiving | 通用宝箱池 |
| EcoNursery | 生态区 | 正式布局库 | 9/9 | 已接入 IsEcology | — |
| EcoHydroponics | 生态区 | 正式布局库 | 9/9 | 已接入 IsEcology | — |
| EcoBiosphere | 生态区 | 正式布局库 | 14/14 | 已接入 IsEcology | 通用宝箱池 |
| SwitchgearGallery | 发电区 | 正式布局库 | 4/4 | 已接入 IsPower | — |
| GeneratorHall | 发电区 | 正式布局库 | 3/3 | 已接入 IsPower | — |
| AccumulatorControl | 发电区 | 正式布局库 | 7/7 | 已接入 IsPower | 通用宝箱池 |
| FacilityReceptionHall | 迎宾区 | 正式布局库 | 15/15 | 已接入 IsHall | — |
| FacilityEntrancePassage | 入口 | 正式布局库 | 0/0 | 无 | — |
| FacilityTransit | 迎宾区 | 正式布局库 | 14/14 | 已接入 IsHall | — |
| MedicalDoctorOffice | 医疗区 | 正式布局库 | 10/10 | 已接入 IsMedical | — |

入口走廊、门槛、连接廊、转角、坡道、下行楼梯与汇流件属于通行/连接模块，不把它们的无刷怪等同于主区域遗漏。未被当前布局采用的旧 Junction/RouteEnd/FreightTransfer/ForkLeft/ForkRight 也不混入当前主要缺口。

## 证据与边界

- 已保存生成器：`Content/__ExternalActors__/GameMaps/L_Dungeon_Randomized/8/N2/KZ839Z5RGFD4Y0908097LH.uasset`。散列：`812a644be76ec12f2a24334d97eb7fcae2da83e215a91b7adb9b9b5e7404c1ae`。
- 保存包内提取的目录：`SourceAssets/DungeonCoverageAudit20261017/saved-catalog.json`；完整逐 ID 结果：同目录 `coverage.json`。
- 制作源目录与正式保存目录并非完全一致，差异涉及部分家具布置、工作台、宝箱属性和布局库；本报告以正式保存目录为准。两者搜索容器身份集合一致，不能用制作源中单独出现的修改代替实际保存。
- 搜索链：`StaffLivingRoomAssembly` / `CargoWarehouseContainers` / `StationWorkshopAssembly` → `runtime_actors` → `WardRoomAssembly::Spawn`；病区床头箱来自 `WardBedScatter`。
- `ColdSteelSceneLoot::BoundPool` 识别完整静态 ID、Run{seed}.Node{node}. 前缀和 Hospital.Bedside 动态族；仅池查找归并，库存与抽取身份仍独立。
- 刷新链：`AuthoredDungeonGenerator` 异步资源准备 → `DungeonRunSubsystem::BindCompletedDungeon` → `FacilityHallEncounter` 各区域 Configure 分支；旧 `DungeonRoomEncounter` 已退役，场景中的 encounter/archive_combat 锚点本身不会刷怪。
- 宝箱链：生成器按 interaction_enabled 写入 DungeonTreasureChest 或 DungeonTreasure.PendingLoot；有效宝箱由 ColdSteelDungeonLoot 读取通用深度档，最终箱使用最高档和 final_multiplier。
- 这是保存数据与源码接入覆盖结果，不替代游戏内搜箱、实际怪物落点和主客机体验。没有执行修复或改变当前编辑器/运行实例。
