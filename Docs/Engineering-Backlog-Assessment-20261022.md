# 待办与开发事项评估（2026-10-22）

本文是**评估与排序**，不是开发记录。按用户 2026-10-22 要求编写：盘点项目中尚未完成、且体量足以占用大量工作量的开发与修复事项，供后续开工时选取。

**本轮未修改任何源码、配置或资产，未启动 UE，未构建，未运行游戏或测试。** 下文所有"现状"均来自对工作区文件的静态读取，标注了可复查的文件与行号；凡属推算的排期与工作量均已写明是估算。

---

## 0. 评估口径

### 0.1 判断"大工程"的标准

| 维度 | 说明 |
| --- | --- |
| 跨目录 | 需要同时改 `Source/`（多模块）、`Content/ColdSteelData/*.json`，可能还有存档结构 |
| 上下文量 | 需要通读的大文件多（例如 `ColdSteelStatusModel.h` 44 KB、`AuthoredDungeonGenerator.cpp` 2151 行、`FPSGAMECharacter.cpp` 4364 行、冷钢设计系统 84 KB） |
| 后台可完成 | 纯 C++ / JSON / 文档即可落盘，不需要开编辑器、不需要用户现场验收 |
| 未完成度 | 数据、接口、UI、玩法四层里缺的层数 |

### 0.2 工程规模基线（实测）

| 项 | 数值 |
| --- | --- |
| `Source/FPSGAME` C++ 文件 | 2,029 个 |
| `Source/FPSGAME` 代码行 | 301,227 行（18.46 MB） |
| `Docs` Markdown | 2,373 篇（目录合计 360.8 MB） |
| `Content` 资产包 | 48,055 个 `.uasset` |
| `Docs/Backlog.md` 未完成条目 | 97 条（已完成 125 条） |
| 工作区未提交改动 | **2,050 项**（新增 1,233 / 修改 596 / 删除 221） |

模块行数分布（决定读码成本）：

| 模块 | 行数 |
| --- | --- |
| `Weapons/` | 75,648 |
| `UI/` | 57,213 |
| `Monsters/` | 52,432 |
| `Building/` | 20,308 |
| `Skills/` | 19,111 |
| `Dungeons/` | 10,329 |

> **重要前提**：工作区有 2,050 项未提交改动，`git` 已无法整份提交。任何大工程开工前必须先按模块精确暂存，否则新改动会被现有未提交内容淹没，事后无法分离。

---

## 1. 一级：缺口最完整、最值得投入的五项

这五项的共同点是**数据层已有、运行时没接**。这是最划算的一类工程：设计已定稿、数据结构已存在、缺少的是把两端连起来，工作量集中在 C++ 与 UI，不需要重新做美术。

### A1 · 地牢随机事件系统（女神像 / 陷阱 / 遗物 / 恶魔像 / 宝箱房）

**现状证据**

| 层 | 实际状态 |
| --- | --- |
| 数据 | `Content/ColdSteelData/dungeon_event_buffs.json` 已有 **63 条**事件增益，`trigger` 分布为 `fail` 35 条 / `success` 28 条，`battles` 统一 3，效果键为 `atkPercent` / `defPercent` / `matkPercent` / `moveSpeedPercent` |
| 数据一致性 | 63 个 buff ID **全部**能在 `status_effects.json` 的 138 个 `type` 中找到（0 条缺失）——数据层是干净的 |
| 接口 | `UColdSteelStatusModel::ApplyDungeonEventBuff(FName)` 已实现于 `Source/FPSGAME/Combat/ColdSteelFormulaBonuses.cpp:259`，内部带目录静态缓存 |
| 逐场消耗 | `CompleteDungeonFormulaBattle()` 已实现于同文件 `:282` |
| 卡片同步 | `SyncDungeonBattleTiles()` 已实现于同文件 `:289`，会把"N 场"倒计时推到状态卡 |
| **调用方** | **全部为 0。** 全仓库搜索：`ApplyDungeonEventBuff` 只有定义与头文件声明；`CompleteDungeonFormulaBattle` 只有定义与头文件声明（`:282` / `StatusModel.h:97`） |
| 事件房 / 事件卡 / 属性检定 | `EventRoom`、`EventCard`、`AttributeCheck`、`RevealDepth`、`TrapRoom` 在 `Source/` 中**均为 0 命中** |
| 女神像 | 例外：**已经能用**。`DungeonRunSubsystem::InitializeShrine()`（`Dungeons/DungeonShrine.cpp:17`）从 catalog 的 `start_shrine` 读 6 座雕像，按 `ShrineSelection` 独立种子等权选一，`DungeonFacilityFlow20261007/Config/catalog.json` 中 `start_shrine.statues` 确实有 6 条 |

**结论**：数据、公式、卡片显示三样都已就位，缺的是**事件房本身**（房间角色、选择 UI、属性检定公式、成功/失败分支、结果写档）。这是目前投入产出比最高的一项。

**需要做的**

1. `dungeon-events.json` 数据：事件池、权重、选择项、检定属性、基础成功率、成功/失败对应的 buff ID。
2. 属性检定器：设计文档给的规则是基础 20%、夹在 5%–95%、>80% 软上限、<20% 软下限，对接现有六维。
3. 事件房房间角色：`AuthoredDungeonGenerator` 的目录里加事件房类型，纳入布局清单。
4. 事件卡 UI：按冷钢设计系统做屏幕中下方玻璃卡。
5. 接线：事件结算调用 `ApplyDungeonEventBuff`；战斗结束调用 `CompleteDungeonFormulaBattle`（当前两个函数都是孤岛）。
6. 联机：事件结果必须写进存档且读档不回滚。

**参考**：`Docs/Gameplay/gameplay-roadmap-20260918.md` §4.5 已将五个事件（女神像 / 古老陷阱 / 冒险者遗物 / 恶魔像 / 宝箱房）与检定规则定稿。

**风险**：事件结果一旦写档就不能回滚，需要沿用现有 A/B 双槽 + Generation 校验的提交方式。

---

### A2 · 出征闭环：钥匙阶梯 + 祭品 + 进入提交点 + 结算 + 奖励邮箱

**现状证据**

| 层 | 实际状态 |
| --- | --- |
| 钥匙道具 | `items.json` 已有 `anchorTokenA`–`anchorTokenF` **6 把**（第 553 行起） |
| **钥匙代码** | `anchorToken` 在 `Source/` 中 **0 命中** —— 只有道具定义，没有任何档位规则或消耗逻辑 |
| 祭品 | `OfferTribute` 存在于 `Combat/ColdSteelFormulaBonuses.cpp` 与 `UI/ColdSteelStatusModel.h`；`items.json` 有 6 条 `tribute_` 与 73 条 tribute 类物品 |
| 出征面板 | `ColdSteelExpeditionWidget.h:24` 明写 *"Presentation only. The caller owns eligibility, costs and any departure transaction."* |
| 当前实际规则 | `ColdSteelExpeditionController.cpp:52` 写死 `Facility.EntryCost = TEXT("无需祭品")`；`:63` 规则文案写"无需祭品或钥匙" |
| 出发事务 | `ColdSteelExpeditionController.cpp` 的 `OnDepartureRequested` 直接 `OpenLevel`，**没有扣钥匙、没有祭品提交、没有加载失败回滚** |
| 结算器 | `SettleRun` / `RunSettlement` / `ClaimReward` / `RewardGrant` 全仓库 **0 命中** |
| 奖励邮箱 | `Mailbox` / `RewardMail` / `RewardMailbox` 全仓库 **0 命中** |

**结论**：出征现在是一条"免费直达"的通道。钥匙经济、祭品准备、结算、背包满承接四个环节全部缺失。这四项合起来才构成完整闭环，拆开做没有意义。

**需要做的**

1. 六档钥匙表：等级、节点数、战斗占比、奖励系数、推荐等级、解锁链（数值可直接复用旧工程 `dungeon-config.json` 的 `dungeonList`）。
2. 出征提交点：钥匙与祭品必须**在地图加载成功之后**才确认扣除；加载失败回滚。这是旧工程踩过的坑，`Docs/Gameplay/gameplay-roadmap-20260918.md` §4.2 有明确记录。
3. 结算器：正常通关 / 主动撤离 / 阵亡 / 异常返回四种情形分别处理。
4. 奖励邮箱：背包满时承接，走一次事务提交。
5. 出征面板改造：从"展示"变成真正的"行前准备 + 消耗汇总"。

**附带发现（重要）**：`dungeon_loot.json` 现有 34 个掉落 ID，**全部**能在 `items.json` 找到（无悬空 ID），但分类分布是：

| 分类 | 条数 |
| --- | --- |
| enhancement（强化材料） | 18 |
| material | 8 |
| consumable | 7 |
| currency | 1 |
| **武器 / 护甲** | **0** |

也就是说**地牢宝箱当前永远不出装备**。而整个项目的主轴是"装备驱动"，这一格是空的。三层掉落里的"随机层（武器/护甲 + 词缀）"和"目标层（定向产出）"从未建立。

---

### A3 · 地牢掉落三层与词缀池（把"装备驱动"补上）

**现状证据**

| 项 | 实际状态 |
| --- | --- |
| 掉落表 | `dungeon_loot.json` 存在，三档 `min_depth` 0/4/8，`rolls` 2/2/3，`final_multiplier` 3.0 |
| 掉落消费者 | `ColdSteelDungeonLoot`（`UI/ColdSteelDungeonLoot.cpp:48` 读取该表）；宝箱开启按房间深度 roll，结果写进宝箱自己的容器再领取（2026-10-02 起不再直接发放） |
| 装备产出 | **0 条**（见 A2 附带发现） |
| 词缀池 | `Affix` 有 25 处命中，但全部是**附魔系统**的现有实现（`ColdSteelEnhancementSystem::Affix` 读写 `_enchantData`），**没有掉落词缀池**；`AffixPool` 0 命中 |
| 保底机制 | 无 |

**结论**：`dungeon_loot.json` 是一个"只出材料"的掉落表。要让它承载装备驱动，需要扩表结构本身（现在只有 `tiers[].entries[]`，没有分层、没有权重修正、没有保底计数）。

**需要做的**

1. 扩表结构：稳定层 / 随机层 / 目标层三段。
2. 装备条目：接入现有 19 把 `weapon` + 8 把 `weapon_melee` + 31 件 `equipment`，按强化等级（`enhanceLevel`）分档。
3. 词缀池：**只能使用公式层已支持的 key**（这条是硬约束，否则会与 `CoreCombatFormula`、浮窗公式、武器面板三处口径分叉）。
4. 保底：连续 N 次未出目标层时提权，阈值写在数据里不硬编码。

**风险**：这一项会同时影响战斗数值、浮窗显示和经济，是最容易引发回归的一项。建议放在事件系统之后做。

---

### A4 · 野外动物接入 + 森林怪物

**现状证据**

| 项 | 实际状态 |
| --- | --- |
| 资产 | `Content/AnimalVarietyPack` 本地已有 **220 个文件**：146 段动画、18 个骨骼网格、17 个材质 |
| 分物种 | Crow（17 动画 / 3 网格）、DeerStagAndDoe（46 / 6）、Fox（28 / 3）、Pig（26 / 3）、Wolf（29 / 3），各带 Overview 地图与贴图 |
| **引用情况** | `AnimalVarietyPack` 在 `Source/` 与 `Config/` 中 **0 命中** —— 完全未接入 |
| 四足模板 | `UQuadrupedAnimationSet` / `AQuadrupedAnimationTemplate` 已实现，但当前**只服务 `WolfMonster`**（`WolfMonster.cpp:52` 设置 `UQuadrupedTemplateAnimInstance`） |
| 森林怪物 | 无 |
| 工具 | `Tools/QuadrupedTemplates/` 有 `create_wolf_template.py` 与 `read_source_catalog.py` |

**结论**：220 个资产躺在硬盘上完全没被使用。这是"死资产复活"类工程，投入产出比很高，且与 A1/A2/A3 完全不重叠（独立目录，可并行）。

**需要做的**

1. 猎物（鹿 / 猪 / 乌鸦）：逃跑、群居、昼夜作息、击杀掉肉与皮。
2. 掠食者（狐 / 狼）：主动或受威胁后反击。
3. 复用四足模板与共享行为树，不复制 `WolfMonster` 的实现。
4. 掉落接入现有背包与事务存档；尸体可采集。
5. 新增 1–2 种森林怪物，走 `ue3-monster-workflow`。
6. 生态平衡：与 PCG 生态权重、昼夜、天气联动，刷怪有上限与冷却。

**未决问题**：动物要做生态模拟（繁殖 / 迁徙）还是纯刷怪制？这一条会显著改变工作量级。

---

### A5 · 野外随机事件调度器

**现状证据**

| 项 | 实际状态 |
| --- | --- |
| 事件子系统 | `WorldEvent` 全仓库 **0 命中**；`EventSubsystem` 0 命中 |
| 时间轴 UI | `ColdSteelEventTimeline.cpp` 已完整实现（缩略轨道、展开详情、筛选、未来 5 日窗口） |
| 数据源 | 只有天气。`:88` `TimelineWeatherFilterButton` 是唯一的筛选按钮 |
| 占位行 | `:94` `TimelineInvasionText=MakeTimelineText(TEXT("暂无入侵情报"),...)` 仍是写死的占位文案 |
| 调度器 | 无 |

**结论**：展示面完全建好了，只差数据源。这一项与 A1 结构相似（UI 先行、后端缺失），但依赖底座更大。

**需要做的**

1. `UWorldEventSubsystem`：时钟 Tick → 事件池 → 实例 ID → 状态机。
2. 实例稳定 ID：`EventInstanceId = StableHash(WorldId, DaySerial, SlotIndex, EventType, AttemptIndex)`，读档不重抽。
3. 三态：预报 / 进行中 / 已结算；玩家不在场也要推进（超时即结算）。
4. 数据：`event-types.json`、`event-instances.json`、`poi-templates.json`。
5. 时间轴 UI 扩展：数据源从「天气」扩到「天气 + 事件」，启用入侵情报行。
6. 同步更新 `Docs/UI/event-timeline-plan-20260913.md` 里"不添加尚未接入的入侵事件"这条边界。

**前置依赖**：`WorldId / 世界种子进存档`（见 B4）。

---

## 2. 二级：规模中等、但卡住后续所有事

### B1 · Cook 阻塞：矿镐骨架缺失（P0）

**现状证据（本轮实测）**

| 项 | 结果 |
| --- | --- |
| 目标资产 | `Content/Items/ProductionTools/GripMotion20260913/SK_Harvest_Pickaxe_Skeleton.uasset` |
| `Test-Path` | **False**（文件不存在） |
| 引用方 | 6 个包引用它（`SK_Harvest_Pickaxe` 与 5 条 `A_Harvest_Pickaxe_*`） |
| Cook 表现 | 不在编译期报错，在 `AnimSequence.cpp:2172` 断言 `!Hash.IsZero()`，整次 Cook 崩溃，退出码 25 |
| 作者源 | **齐全**：`SourceAssets/ProductionToolGrip20260913/Export/` 下有 `SK_Harvest_Pickaxe.fbx`（2.67 MB）+ 5 条动画 FBX + `Pickaxe_SingleHand_Editable.blend`（140 MB） |
| Cook 目录 | `Config/DefaultGame.ini` 有 `+DirectoriesToAlwaysCook=(Path="/Game/Items/ProductionTools/GripMotion20260913")` |

**结论**：打包必崩，且这是一个已知缺陷的另一半（2026-09-19 只修了斧头）。作者源齐全，属于半小时级修复，但它让所有"打包验收"类工作都无法进行。

**修法**（与斧头同一套）：按动画已引用的路径补出骨架并显式保存，名字一致即可自动恢复绑定；修完在新进程读回骨架非空，再重跑一次 Cook 确认断言消失。**不要用摘 AlwaysCook 的方式绕过。**

参考：`Docs/Backlog.md:448`、`Docs/Performance/pie-vs-packaged-gap-20260923.md` 第 6 节。

---

### B2 · M66「焚骸」战斗深度补齐

**现状证据**

| 项 | 实际状态 |
| --- | --- |
| 攻击枚举 | `EM66AttackKind` 只有 **3 个**值：`Sweep` / `GroundSlam` / `FurnaceBreath`（`M66IncineratorMonster.h:25`） |
| 已实现 | 横扫 V08、砸地 V16（用户确认"合格"）、炉息喷吐 V17（用户确认"成功"） |
| **未实现** | 设计文档要求的**焦渣抛落**与**回灰蓄压**两招 |
| **三阶段推进** | 在 `M66*.cpp` 中搜索 `0.65` / `PhaseThreshold` / `GetHealthPercent` **0 命中**；`Stage` 变量只出现在 `M66RecoveryAuditGameMode.cpp`（审计用），**真实怪物没有阶段系统** |
| 血量 | `MaxHealth=6000.f`（`:131`），受 `MonsterCoreStats::HealthMultiplier()` 修正（`M66IncineratorMonster.cpp:77`） |
| 弱点窗口 | `M66Weakpoint.cpp` 有 `M66Cleft` 骨骼段与 `PrepareCleftWeakpoint`，但"每两次攻击强制开腔 2.5 秒"的节奏**未实现** |

**结论**：M66 目前是"三招循环 + 固定血量"的首领，设计文档里的阶段推进、弱点击破节奏、两招缺失，意味着它的战斗深度只有设计的一半。

**需要做的**

1. 阶段系统：100–65% 裹灰 / 65–30% 裂壳 / <30% 失压，含转阶段抽搐、干膜脱落、减伤从 30% 降到 10%。
2. 焦渣抛落：地面 1.2 秒落点提示、两块焦渣、6 秒热区、同时最多 2 片。
3. 回灰蓄压：2 秒蓄压、可被打断并触发开腔、未打断则接定向喷吐。
4. 开腔节奏：每两次主要攻击或排热器官受损触发 2.5 秒弱窗，窗口内弱点倍率 1.6。

参考：`Docs/Monsters/incinerator-boss-m66-design-20261014.md` §100–127。

**风险**：这是已被用户确认过多轮的首领，改动战斗节奏容易推翻已认可的节奏感。建议做成可回退的 CVar 或数据驱动参数。

---

### B3 · 体素建造：梁单元聚合（性能）

**现状证据**

| 项 | 实际状态 |
| --- | --- |
| 算法 | 已分析、**未实现**（`Docs/Building/voxel-build-workflow.md:63`） |
| 预期收益 | 节点数按段长下降 5–10 倍；按基线线性关系，20,000 格墙约 **96 ms → 10–20 ms** |
| 现状保护 | 已有局部承重求解：一次解算最多 `fps.Building.MaxSolveNodes`（默认 4096）个节点，超出即把邻居标为边界节点 |
| 语义风险 | 合并后直墙/直柱内部接缝不再参与求解，整体变强，"墙从中段剥裂"的现有效果会减弱 |

**结论**：纯性能工程，收益明确，但会改变失效手感。**必须灰度**：先只对"无荷载、无损伤的垂直段"开启，CVar 控制。

**连带项**（同一系统，可一并做）

| 项 | 现状 |
| --- | --- |
| 过载音画反馈 | 未做。过载只有面板预警行与提示栏播报，**无声无抖动**；30 秒渐进损伤期间玩家容易忽略 |
| 残骸回收比例 | 未做。现在**100% 返还**（拆除进背包、残骸转方块、失败放置也返还），无"倒塌损耗" |
| 构件免料 | 未做。罗马柱、矮栏杆等构件放置**不扣料**，只有体素扣料 |
| 建造地图配置化 | 未做。`VoxelBuildComponent.cpp:335` 硬编码 4 张地图：`DayNight_Lighting` / `L_Normandy_FPS_Test` / `L_MilitaryTrench_FPS_Test` / `L_TemperateHills_Initial` |
| 裂纹写实表现 | 未做。方案已给（材质参数化 + 世界投影裂纹图集），需美术出图集 |
| 体素块专用图标 | 未做。现复用 `Icons/wood|stone|marble.png` 材质图 |

---

### B4 · WorldId / 世界种子进存档（多个系统的共同前置）

**现状证据**

| 项 | 实际状态 |
| --- | --- |
| 大世界侧 | `TemperateHillsWorld.h:141` 有 `Seed=122`，`:144` 有 `FGuid WorldId`；`TemperateHillsStreaming.cpp` 与 `Backdrop.cpp` 有使用者 |
| **存档侧** | `FColdSteelProfile`（`UI/ColdSteelInventoryTypes.h:211` 起）**没有** `WorldId` / `WorldSeed` 字段 |
| 掉落 | 按"当前地图名"恢复，没有独立世界 ID |

**结论**：同一宿主地图的不同随机世界会串档，地牢种子无法复现。这是 A5（事件调度）和"每局随机种子开放世界"的共同前置。

参考：`Docs/WorldGeneration/hills-formula-openworld-20261019.md` §4 已量化这个差距。

---

### B5 · 工作台与制作系统：设施已存在，缺的是配方内容

> 这一条与我在初评时的判断相反，特此更正。工作台**已经做好了**。

**现状证据**

| 项 | 实际状态 |
| --- | --- |
| 世界构件 | **已存在**。`DA_VoxelBuildPalette.uasset` 中含 `workbench_table` / `gun_workbench_table` / `potion_workbench` / `woodworking_bench` 四个条目 |
| 交互判定 | `ColdSteelWorldInteraction::IsWorkbench()` 已实现，按 `VoxelWorkbenchId` / `VoxelGunWorkbenchId` / `VoxelIncineratorId` 判定；提示文案分三种 |
| HUD | `ColdSteelHUDWidget::OpenWorkbench(AActor*)` / `CloseWorkbench()` / `IsWorkbenchOpen()` 均已实现，带滑入动画与背包骑乘 |
| 制作系统 | `UColdSteelCraftingSystem` 已实现，读三份表：`crafting-recipes.json` / `ammo-crafting-recipes.json` / `woodworking-recipes.json` |
| 消费方 | `ColdSteelWorkbenchWidget.cpp:178` 遍历 `Crafting->Catalog()`；`ColdSteelGunAmmoCraft.cpp:26` 遍历 `AmmoCatalog()` |
| **普通配方** | `crafting-recipes.json` **只有 2 条**：`craft_axe`、`craft_pickaxe` |
| 弹药配方 | 21 条（正常） |
| 冶炼配方 | 4 条 |

**结论**：制作系统的**管道、面板、世界物件、扣料事务全都通了**，缺的只是"往表里填配方"。这不是大工程，是一天的内容填充。

**顺带发现**：调色板里有 `blast_furnace`、`campfire`、`planting_bed`，但**没有床铺**（`bed` 类条目在 palette 中 0 命中）。Backlog 里"床铺 = 存档点/重生点/时间推进"这件事确实没做。

**种植地**：`VoxelBuildPalette.cpp:4` 起在 `PostLoad` 里注入 `planting_bed` 条目（模型 `SM_PlantingBed_2m_V2`，占位 10×10×2 格），但**没有播种、生长、收获或专用交互面板**。

---

## 3. 三级：内容与美术（耗时，但需要审美判断）

| 项 | 现状 | 说明 |
| --- | --- | --- |
| 储物箱表面材质 P1–P4 | 计划已定，用户 2026-09-24 指示"后续再做" | 母材质 `M_Crate_Master` + 8 个 MIC + 三通道 2K 贴图 + 档位识别参数（T4 鎏金微发光、T5 宝石自发光）。`Backlog.md:441` |
| 裂纹写实图集 | 未做 | 需美术出法线+粗糙度+暗化图集，再做 0/40%/70% 三档原型 |
| 赛博公寓遗留 P0/P1 | 未做 | 阳台唯一通道被幕墙竖框截成两侧各约 49 cm；`LIV_furniture` 柜体卡在卫浴门洞；贴图穿模三选一（UV / 位置 / 材质缺失）。`CyberpunkApartment-POSITION-AND-TODO.md:238` |
| 地牢环境小物 | 部分未做 | 清单 E1–E13（木桶/木箱/骨堆/铁链/蛛网/破布/木架/长凳/梯子/火把托架/贴花）与 D2–D5 仍标"新建未制作" |
| 采掘破碎表现 | 未做 | 挖矿只有粉尘 + 实例移除，没有预破碎或碎块；`BreakChunk` / `OreBreak` / `RockBreak` 在源码中 0 命中 |

---

## 4. 不建议现在动的（已被多轮否定，容易变无底洞）

这几条在 `Backlog.md` 里反复出现，且都有明确的用户否定记录。投入它们需要用户在场逐帧看画面，与"后台烧 token"的目标冲突。

| 项 | 否定记录 |
| --- | --- |
| 守寝者移动 | "V18 仍被用户判定不合格。本轮停止动画迭代" |
| 铲子双手动画 | 手臂扭转未解决，已暂停；右肩摆动 +98°（已认可基线是 +15°），需要重做站姿而不只是调参 |
| 缚群衣物 | "整体衣物仍不合格；V18、V19 均不作为成功模板" |
| 双持手枪第三人称 | 2026-10-20 起已改三版，2026-10-22 截图仍指出双臂交叉；已转向 Epic Paragon Twinblast 真实参考源 |
| 登 山包背带 | "前版用户明确否定"，剩余手臂/衣袖接触项未结 |
| HK416 首枪顿卡 | 用户判定"都不合格，暂停"；预热改动已落盘但未验证 |

**这些不是不能做，而是必须用户在环**。如果硬要在无验收条件下推进，最可能的结果是第二天全部推翻。

---

## 5. 建议的开工顺序

按依赖关系与"后台可完成度"排序：

| 批次 | 内容 | 理由 |
| --- | --- | --- |
| **第 1 批** | B1 矿镐骨架 | 半小时级，解掉打包阻塞，让后续所有 Cook 类工作可用 |
| **第 2 批** | A1 地牢事件系统 | 数据与 API 已就位，纯接线，独立于其它项 |
| **第 3 批** | A2 + A3 出征闭环与掉落三层 | 依赖 A1 的事件结算钩子；同时补上"装备驱动"这个主轴缺口 |
| **第 4 批** | A4 动物接入 | 与前三批完全不重叠，可全程并行 |
| **第 5 批** | B2 / B3 / B4 / B5 | 视前四批余量选取；B4 是 A5 的前置 |

**如果要一夜之间烧掉尽可能多的量**：第 2 批与第 4 批可以同时开两个子代理（分属 `Dungeons/`+`UI/` 与 `Monsters/`+`Content`，无文件重叠），第 1 批作为收尾顺手做掉。第 3 批因为会动战斗数值与物品目录，建议单独一轮，不要与前两批混在同一构建里。

---

## 6. 本轮未做的事

- 未修改任何源码、配置、资产或存档。
- 未启动 UE 编辑器、游戏或 PIE。
- 未执行任何构建、Cook 或打包。
- 未运行任何测试、采样或截图。
- 未提交或推送 Git。

上文所有工作量判断为**基于静态读取的估算**，实际耗时需以开工后的真实进度为准；本节所列边界不能被解释为上述事项已获验证。
