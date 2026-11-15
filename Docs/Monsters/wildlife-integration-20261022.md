# 野外动物接入（2026-10-22）

把 `PROTOFACTOR ANIMAL VARIETY PACK`（`/Game/AnimalVarietyPack`）里长期未被引用的五套动物接进游戏：动画槽、角色类、数值、行为、生态刷怪与采集掉落。

**本轮完成的是开发接入与必要构建；没有启动 PIE、没有进游戏、没有截图，也没有验收。** 数值与动作观感均由后续实机确认。

---

## 1. 交付入口

| 项 | 路径 |
| --- | --- |
| 数值/行为/刷怪数据 | `Content/ColdSteelData/wildlife.json` |
| 原生角色 | `Source/FPSGAME/Monsters/WildlifeAnimal.h/.cpp` |
| 生态刷怪 | `Source/FPSGAME/Monsters/WildlifeSubsystem.h/.cpp` |
| 动作集与蓝图制作 | `Tools/Wildlife/create_wildlife_assets.py`、`Tools/Wildlife/install_wildlife.ps1` |
| 构建 | `Tools/Wildlife/build_wildlife.ps1` |
| 掉落物品写入 | `Tools/Wildlife/add_loot_items.py` |
| 物种模型命中资产制作 | `Tools/Wildlife/author_hit_physics.py` |
| 资产回执 | `SourceAssets/Wildlife20261022/authoring_manifest.json` |
| F6 生成目录 | 开发面板「怪物生成」下的 `WildlifeDeerDoe / WildlifeDeerStag / WildlifeBoar / WildlifeFox / WildlifeCrow` |
| 打包 Cook | `Config/DefaultGame.ini` 增 `+DirectoriesToAlwaysCook=(Path="/Game/Monsters/Wildlife")` |

每个物种一套资源：

```
/Game/Monsters/Wildlife/<Species>/
    Animations/A_WL_<Species>_<Slot>      源动画副本（关闭 Root Motion、锁首帧、RateScale 1）
    DA_WL_<Species>_AnimationSet          动作映射 + 走/跑标称速度
    BP_WL_<Species>                        父类 AColdSteelAnimal，已填 species_id
```

## 2. 物种与数值

生命填的是**基础值**，运行时统一乘 `MonsterCoreStats::HealthMultiplier()`（当前 2.0，与全部既有怪物同层）。

| ID | 显示名 | 等级 | 基础HP | 实战HP | 物防 | 魔防 | 经验 | 走 / 跑 (cm/s) | 行为 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| `deer_doe` | 母鹿 | 3 | 90 | 180 | 5 | 2 | 70 | 105 / 520 | 胆小，只逃 |
| `deer_stag` | 公鹿 | 6 | 140 | 280 | 9 | 3 | 140 | 110 / 560 | 胆小，被逼住可用角反击 26 |
| `boar` | 野猪 | 7 | 170 | 340 | 15 | 4 | 190 | 100 / 430 | 主动，650 cm 内冲撞 34 |
| `fox` | 狐狸 | 4 | 48 | 96 | 3 | 3 | 80 | 130 / 480 | 胆小，近身可咬 12 |
| `crow` | 乌鸦 | 2 | 20 | 40 | 1 | 1 | 25 | 90 / 200 | 胆小，无攻击。温带丘陵支持群飞和地面起降 |
| `wolf` | 野狼 | 5 | 220（既有） | 440 | 12 | 8 | 180 | 100 / 380 | 掠食者，**直接复用** `AWolfMonster`，本节只负责刷 |

防御、等级、品阶通过 `MonsterCoreStats::Get` 的 `AColdSteelAnimal` 分支读取同一份 JSON，因此武器伤害公式、暴击、经验等级差与金钱掉落都自动沿用既有口径，不另建一套。

**行为参数**：`alertRadius`（抬头警戒）、`fleeRadius`（起跑）、`aggroRadius`（主动仇恨）、`leashRadius`（追击放弃）、`homeRadius`（游荡范围）、`activity`（`always` / `day` / `night`）。

## 3. 动作槽映射

复用四足模板的 21 槽语义（`UQuadrupedAnimationSet` + `UQuadrupedTemplateAnimInstance`），只填源包真实存在的片段；缺槽不伪造。

| 槽 | 母鹿 | 公鹿 | 野猪 | 狐狸 | 乌鸦 |
| --- | --- | --- | --- | --- | --- |
| Idle | IdleBreathe | IdleBreathe | IdleBreathe | IdleBreathe | IdleLookAround |
| IdleAlert | IdleLookAround | IdleLookAround | IdleLookAround | IdleAggressive | IdleStretchWings |
| LookAround | IdleLookAround | IdleLookAround | IdleLookAround | IdleLookAround | IdleLookAround |
| Walk / Run | Walk / Run | Walk / Run | Walk / Run | Walk / Run | Walk / Hop |
| 转向 | WalkTurnL/R、RunTurnL/R | 同 | 同 | 同 | — |
| AttackBite | — | AntlersAttack | ComboAttackForward | Bite | — |
| AttackRunBite / Pounce | — | AntlersComboAttack / — | — / JumpAttack | RunBite / JumpBite | — |
| Hit* | GetHit（三向同源） | GetHit | GetHit | GetHitFront/Left/Right | — |
| Rest / Sleep | GoToRest→IdleRest→RestToGoBackUp / IdleSleep | Rest 族 / Sleep | Rest 族 / — | Resting 族 / Sleeping | IdleScratchWing / — |
| Death | Death | Death | Death | Death | DeathGrounded |

鹿与猪的受击只有一个源片段，三向映射到同一片段；这不是「已编排三向受击」，只是让三个受击槽都能播。

## 4. 行为状态机

`Idle → Alert → Flee / Chase → Attack → Hit → Dying → Corpse`，全部在服务端跑，客户端按复制的 State 重放表现。

- **Idle / Graze**：交替站立与低头，计时 3–9 s 后切游荡或继续吃草。
- **Alert**：玩家进入 `alertRadius` 时播一次 LookAround，再决定逃还是不理。
- **Flee**：背向玩家跑 `fleeRadius×1.8`，跑出 2.2 倍距离或 8 s 后回到新家点。
- **Chase / Attack**（野猪、受击后的公鹿）：追到 `attack.range` 内起手，单一权威时钟驱动源秒数，接触窗内做一次距离+朝向判定。
- 近战受击按来向选现有动作。子弹命中时，命中骨骼沿来弹方向短暂回弹，地面动物可以继续逃跑，乌鸦可以继续飞行。致命命中直接交给死亡流程。
- **Dying → Corpse**：Death 播到 60% 交给既有 `UMonsterCorpseRagdollComponent`（`Canine` 通用路径），乌鸦关布娃娃、改用定格末姿态。

移动方式：**不依赖 NavMesh**。动物用 `AddMovementInput` 直接转向 + 胶囊碰撞滑行，卡住 1.5 s 换目标；因此不需要新增 `SupportedAgents`，也不会因为地图没烘焙导航而刷不出来。代价是没有绕障寻路，只适合野外开阔地形。

## 5. 生态刷怪

`UWildlifeSubsystem`（`UTickableWorldSubsystem`，仅服务端）：

| 参数 | 值 |
| --- | --- |
| 目标种群 | 24（`populationRadius` 90 m 内） |
| 单次生成距离 | 玩家 42–82 m 外，且离任意玩家 > 30 m |
| 生成间隔 | 3 s |
| 全局上限 | 60 |
| 回收距离 | 140 m |
| 昼夜 | 白天权重含乌鸦；夜晚仍刷鹿/野猪/狐/狼 |
| 地形 | 向下 20 m 射线找地，坡度法线 Z ≥ 0.72，出生点胶囊不重叠 |

按 `spawnWeight` 加权抽物种（母鹿 22 / 乌鸦 20 / 狐狸 20 / 野猪 18 / 公鹿 12 / 狼 8），按 `herdMin..herdMax` 成群。狼不重复造类，直接生成既有 `BP_WolfMonster`。

开发面板的 `SpawnHerd` 也可按物种 ID 在玩家附近手动放一群。

### 温带丘陵群组（2026-11-12）

野生动物子系统只在主地图 `/Game/GameMaps/L_TemperateHills_Initial` 创建，地表就绪后才开始自然刷新。蓝图 `SpawnHerd` 和 F6 的六种野生动物沿用同一地图限制。在丘陵用 F6 选同一物种一次生成 3 只，距离设为 15 米，随后靠近可触发整群逃离。其他地图的 F6 只列出可用敌人，僵尸犬等战斗角色按各自蓝图管理。

鹿群沿可走的旱地换草场，野猪群优先在湿润林缘拱食。成员分别占据落脚点，前队会等，离队成员会加速。玩家靠近、任一成员受伤，或有成员听到项目枪械发出的枪声事件，都能惊动整群。乌鸦在白天自然刷新，沿共享弧线错峰起飞，振翅和滑翔交替，按各自的位置降落。飞行中被击落会先下坠。

`Content/ColdSteelData/wildlife.json` 的 `hillsGroups` 配置草场间距、觅食时长、收拢距离、逃离距离，以及乌鸦航程、高度和速度。群组决策在 `HillsWildlifeGroups.cpp`，移动与动画状态在 `WildlifeAnimal.cpp`。

母鹿、公鹿、野猪、狐狸和乌鸦分别使用自己蓝图下的 `PA_WL_*`，野狼沿用 `PA_Wolf_Gameplay`。枪械射线和近战模型扫掠共用随动画移动的骨骼碰撞。五种环境动物通过战斗组件向武器提供生命和死亡状态，命中按既有攻防公式结算。

枪声在开火时从声源传播，普通枪声上限 36 米，消音枪声上限 10 米，完全静音配件沿用原规则。独行狐狸和普通野狼会沿旱地向远离声源的方向选路，后续枪声刷新六秒警戒时间。飞行中的鸦群遇到新威胁可以转向，并从当前高度衔接逃离航线。

## 6. 当前掉落（2026-11-15 源码与配置复核）

死亡时由服务端抽取一次，排入 `WildlifeSubsystem::PendingLoot`，批量保存为地面物品。单机写入该世界的玩家存档；监听服写入按地图和 `WorldId` 隔离的共享地面库存。它不会直接进入击杀者背包。乌鸦落地时结算；仍在空中而到达清理时限时补做掉落。

六种动物的当前 `wildlife.json` 均为 `raw_meat_chunk`，尸体时限均为 5 秒：

| 物种 | 掉落 |
| --- | --- |
| 母鹿 | 生肉块 ×1–2 |
| 公鹿 | 生肉块 ×2–3 |
| 野猪 | 生肉块 ×2–3 |
| 狐狸 | 生肉块 ×1 |
| 乌鸦 | 生肉块 ×1 |
| 狼 | 生肉块 ×1–2；由狼角色死亡流程调用同一地面掉落入口 |

生肉块已引用 `SM_RawVenison` 与 `Icons/raw_venison.png`，腐坏时间为 3 天，描述与篝火系统相接。旧的分物种肉、皮毛、鸦羽、鹿角、獠牙定义仍存在；七类战利品已具备世界模型，但部分图标仍标记 `artPending: inventory icon`，且这些战利品当前没有列入动物掉落表。本次审查保留现有游戏配置，不凭旧文档重置物品经济。

联机权限与状态审查见 `Docs/WorldGeneration/conversation-audit-20261115.md`。地面库存源码路径成立不等于已通过双人拾取、重连和断线事务的端到端验收。

## 7. 实际落盘与读回结果（2026-10-22 20:10）

`Tools/Wildlife/verify_wildlife.ps1` 在新进程里重新加载全部资产，`verify_report.json` 的 `problems` 为空：

| 物种 | 动作槽 | 走 / 跑标称 | 胶囊 r/h | 蓝图 species_id | 关键片段时长 |
| --- | ---: | --- | --- | --- | --- |
| 母鹿 | 15 | 105 / 520 | 38 / 62 | `deer_doe` | Idle 2.00 · Walk 1.00 · Run 0.80 · Death 2.33 |
| 公鹿 | 17 | 110 / 560 | 42 / 68 | `deer_stag` | AttackBite 1.00 · AttackRunBite 2.00 · Death 2.33 |
| 野猪 | 18 | 100 / 430 | 46 / 58 | `boar` | AttackBite 2.67 · AttackPounce 1.17 · Death 2.17 |
| 狐狸 | 20 | 130 / 480 | 28 / 42 | `fox` | AttackBite 0.67 · AttackRunBite 0.53 · Death 2.10 |
| 乌鸦 | 8 | 90 / 200 | 16 / 20 | `crow` | Idle 3.50 · Walk 0.53 · Death 0.80 |

五个 `BP_WL_*` 的父类均为 `AColdSteelAnimal`，`animation_set` 与 `mesh` 均已指向自身资源。构建回执：`build-02-FPSGAMEEditor.log` / `build-02-FPSGAME.log` 双目标 `Result: Succeeded`。

制作过程中遇到并已修正的两处：一是第一次跑脚本时 `set_preview_skeletal_mesh` 产生的预览缓存任务与退出时的压缩任务撞哈希（`AnimSequence.cpp:5266` 断言），移除该调用后正常；二是数据集只在首次创建时写映射，补槽时需要合并写入，现已改为「只补缺失槽、保留已调值」。

## 8. 早期未完成 / 未验证记录（2026-10-22；当前状态以上节和最新审查为准）

1. **接触窗是设计值，不是源帧核对结果。** `wildlife.json` 顶部的 `contactWindowsAuthored: false` 已注明：公鹿 0.55–0.75 s、野猪 0.5–0.7 s、狐狸 0.3–0.45 s 都是按片段长度估的绝对秒数，没有逐帧看源动画。要改直接改 JSON，不用重编。
2. **乌鸦栖息点。** 温带丘陵群飞使用地面落点，树枝定点栖息仍待制作。
3. **掉落没有美术。** 10 件材料只有名字与堆叠规则，图标与模型待制作；也没有对应的篝火配方，暂时只能存着。
4. **动物不是敌人。** 只带 `Wildlife` 标签，不带 `Enemy`，怪物 AI 不会攻击它们，玩家 HUD 也不把它们当敌人；猎人式主动索敌没有做。
5. **没有做生态模拟**（繁殖、迁徙、种群压制）。当前是「按玩家周围补足数量」的刷怪制。
6. **未运行游戏。** 寻路替代方案的实际走位、逃跑路线被地形挡住时的表现、布娃娃与尸体接地、夜间的实际观感，都还没有人看过。
7. 动作只有源片段副本，**没有做体型适配、足底相位标定或转向片段调校**；走/跑标称速度取 JSON 值，不是实测步频。

## 9. 复现与重建

```powershell
# 1) 生成/补齐动画副本、数据集与蓝图（已存在的资源不会覆盖）
powershell -NoProfile -File Tools/Wildlife/install_wildlife.ps1

# 2) 编译 Editor 与 Game
powershell -NoProfile -File Tools/Wildlife/build_wildlife.ps1 -ReceiptName build-01

# 3) 掉落物品（幂等，已存在的 ID 不会重复写入）
python Tools/Wildlife/add_loot_items.py
```

改数值只动 `Content/ColdSteelData/wildlife.json`；新增物种在 JSON 里加一行 + 在 `create_wildlife_assets.py` 的 `SPECIES` 里加一条映射，然后重跑脚本。

## 10. 来源与许可

模型、贴图、动画均来自本机已导入的 `/Game/AnimalVarietyPack`，未重新生成、未上传任何生成服务。该商品页在本机记录中标注「Allows usage with AI: No」，本流程只做本地资源复用；原包与派生的二进制资源按 `Docs/AssetSetup.md` 的再分发边界处理，不因本次源码修改而改变。
