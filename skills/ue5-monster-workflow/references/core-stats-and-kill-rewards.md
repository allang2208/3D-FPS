# 怪物六维、等级与击杀奖励（gamedev 迁移口径）

对应实装：`Source/FPSGAME/Monsters/MonsterCoreStats.h/.cpp`；交付与审计记录见宿主
`Docs/Monsters/monster-six-stats-rewards-migration-20260923.md`；离线核查器
`Tools/Monsters/check_monster_core_stats.py`（改注册表/表面值必须保持 PASS）。

## 注册表模式

- `MonsterCoreStats::Get(Actor, FMonsterCoreStats&)`：类链 `Cast` 优先（覆盖继承族：
  胖子/突变体3/巫婆走护士系），纯标签识别只作 fallback；未命中返回 false。
- 伤害管线（`CombatFormulaRuntime::MonsterAttributes`）与奖励管线共用这一张表，不再各自
  反推六维。新怪接入 = 注册表加一行 + 头文件加 `Level`/`Rank` UPROPERTY。
- 直取字面量的怪（护士 def/mdef/critres=0）用反向解出的六维**逐位复现**旧伤害数学，
  迁移不得改变已有战斗数值（用旧链路对拍验证）。

## 公式合同（原版 `deriveEnemyBaseStats`/`deriveEnemyCombatLevel` 移植）

atk=round(.5str+.5dex)、def=floor(1.5con+.3str)、matk=floor(.5int+.5wis)、
mdef=floor(1.2wis+.3int)、crit=floor(2+luck)、critRes=floor(con)、maxHp 基线 100+5con；
maxHp/atk/matk/mdef 允许直接指定覆盖（原版 direct-override 口径）。
战斗等级=1+Σ属性权重(.08/.08/.10/.08/.08/.04)+√(hp/100)×1.5(≤8)+移速项+阶级加成
(normal0/minor1/elite3/lord5/boss7)，与配置等级是**两个独立口径**。
经验：压级 diff>5 每级 −15%（按 rank 有下限 .01/.03/.05/.1），越级 diff<−5 每级 +10% 封顶 1.5，
乘 rank 经验倍率；金币 `floor((L×4+rand[1,10])×0.5)×rankGoldMul`。UE 无地牢 grade 字段 →
有效等级=配置等级，pacing 预算与祭品键未迁移（文档已记边界）。

## 全局生命成长层

- 调全员血量只改 `MonsterCoreStats::HealthMultiplier()`（当前 2.0，2026-09-23 用户拍板翻倍），
  各怪 `BeginPlay` 初始化点 `MaxHealth*=mult; Health=MaxHealth;`。语义=原版 monsterGrowth 层：
  BP 实例覆盖值同样放大、归巢/回血读 MaxHealth 自动跟随、六维与奖励不动。
- **不要在 ctor 字面量上直接翻倍**：会被 BeginPlay 再乘一次，且盖不住 BP 覆盖。
- 击杀时间随 HP 线性放大而单只经验不变 = 单位时间经验产出按倍率缩小；补偿属数值决策，
  留给用户拍板，不擅改 `ExperienceReward`。

## 接入点

`UColdSteelStatusModel::AwardKill` 与火球延迟击杀提交循环（`ColdSteelFireballModel.cpp`
遍历 Kills 处）**必须成对**改，否则宏杀奖励口径漂移；金币入包用 `CreateItem("gold",n)`
合并堆叠，背包满静默失败为既有行为。

## 预览／立绘用的临时生成体：绝不改写 CDO（2026-09-24）

怪物类在构造里设 `AutoPossessAI = PlacedInWorldOrSpawned`（如 `WolfMonster.cpp`），
**直接 `SpawnActor` 会在预览场景里生成 AI 控制器并跑行为树**。UI 立绘、开发面板预览这类纯展示用途
必须关掉自动附身，但关的方式有对错：

- **错**：`Class->GetDefaultObject<ACharacter>()->AutoPossessAI = Disabled;`
  改写的是**共享 CDO**，会污染真正的游戏怪物（所有同类怪都不再附身 AI），且是全局持久副作用。
- **对**：用 `FActorSpawnParameters::Template` 传一个临时模板——
  `Template = NewObject<ACharacter>(GetTransientPackage(), Class, NAME_None, RF_Transient);`
  `Template->AutoPossessAI = Disabled; Template->AIControllerClass = nullptr;`
  生成体复制**模板**属性而非 CDO 属性，只影响这一具预览体。

同理，任何"预览专用"的属性调整都应走模板或生成后改实例，不落到 CDO。

## 图鉴栏的怪物数据来源与接入成本（2026-09-24）

- 图鉴的怪物列表／六维／品阶全部取自 `UDevelopmentSpawnComponent::GetMonsters()` +
  `MonsterCoreStats::Get()`，与开发面板、刷怪**共用同一张登记表**，不另建名单。
- **登记表挂在 `AFPSGAMEPlayerController`**（构造里 `CreateDefaultSubobject`），**不在 Pawn 上**。
  按 Pawn `FindComponentByClass` 取会永远拿到 null，表现为"怪物分区恒为空"——这个症状很容易被
  误判成"怪物没分配品阶"。
- 新增怪物进图鉴 = 在 `DevelopmentSpawnComponent` 构造函数加一行 `Add(Id, Name, ClassPath, Radius)`；
  登记后列表、详情、立绘全自动，无需再改图鉴代码。这是**有意为之**：该表同时是刷怪名单，
  不应自动收录磁盘上任何怪物资产。
- 立绘取怪物类后由 `UColdSteelMonsterPortraits` 运行时渲染，口径见
  [运行时图标准备与定向刷新](../../ue5-ui-umg-slate/references/runtime-icon-pipeline.md)。
