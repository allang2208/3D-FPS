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
