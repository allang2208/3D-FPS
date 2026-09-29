# 地牢刷怪池阶级入池 — 2026-09-28

## 背景：区分做了，池没接

怪物阶级系统（`EMonsterRank`：normal / minor / elite / lord / boss）与战斗/奖励管线
（`MonsterCoreStats`：阶级战斗加成 +0/+1/+3/+5/+7、经验 ×1/×1/×2/×4/×20、金币 ×1/×1/×2/×3/×3）
早已实装；刷怪导演 `DungeonSpawnDirector` 也从首批起就支持池条目携带 `level` / `rank` 覆盖
（`WriteLevelRank`：`level>0` 替换实例等级、条目带 `rank` 即覆盖品阶，深度/精英加成恒叠加）。

但 20260927 版池配置（`SourceAssets/DungeonSpawn20260925/Config/spawn-groups.json`）的 21 个条目
全部只有 `{id, class, weight}`——运行时一律落各类默认值。直接后果：**大手（类默认 Lord/12 级/
经验 2892）以权重 1–2 常驻全部五个家族的普通战斗房**，每只按领主结算（×4 经验 ≈11.6k、
战斗等级 +5、金币 ×3），与"手脑才是 Boss"的定位冲突。本轮把阶级/等级显式写进每条池条目。

## 入池方案（依据《怪物属性总表》+ 各类构造器现值）

| 怪种 | 池 rank | 池 level | 依据 |
| --- | --- | ---: | --- |
| 小手 FleshHandMinion | **minor** | 1 | 80 HP / 物攻 20，全场最低档杂鱼；minor 给 +1 战斗等级、经验仍 ×1 |
| 感染犬 InfectedDog | normal | 7 | 220 HP 快速近战，类默认即目标值 |
| 野狼 Wolf | normal | 5 | 220 HP 咬/扑，类默认 |
| 胖子 FatZombie | normal | 4 | 600 HP 慢速肉盾，类默认 |
| 毒蛆 PoisonMaggot | elite | 4 | 800 HP 远程毒法（类默认 Elite），坦克型精英 |
| 突变体-3 Mutant3 | elite | 9 | 750 HP / 40 近战（类默认 Elite），输出型精英 |
| 大手 FleshHand | **lord**（用户拍板，2026-09-28） | 12 | 与类默认一致：1500 HP 冲撞重锤，房间级领主，×4 经验 / +5 战斗等级 / ×3 金币 |

设计意图：杂鱼=normal、垫底=minor、房内精英=elite、**大手=每房重量级领主 lord**（用户明确大手、
手脑同归 Lord 档）。手脑不入普通池，保持现 Boss 身份；Boss 遭遇用普通 SpawnActorDeferred 生成、
不覆盖属性，手脑全程走类默认 Lord/12，无需改动。封门精英房行为不变——整组强制 Elite 且 +2 级
（`PlanOpening` 的 `bOverrideRank=Plan.bElite||Chosen->bRank` 优先取房级，即精英房内大手也是 Elite）。
显式写 `level` 同时把池与各类默认值解耦：后续改类默认不再静默改变地牢难度。

## 数值影响（相对 20260927 版）

- 大手显式 lord/12 与 09-27 版隐式类默认完全一致（首轮方案曾提议降 Elite，用户否决），结算零变化。
- 其余六种 rank/level 与类默认一致，结算数值零变化（毒蛆/突变体本就 Elite）。
- 小手自 normal→minor：战斗等级 +1，经验/金币乘区不变（20 基础经验照旧）。

## 写入与安装

真源 `Config/spawn-groups.json`（revision `20260928-rank-tiering`，21 条目全部带
`level`+`rank`）→ `Scripts/extend_catalog.py`（整段替换透传新字段，离线候选已核验零偏差）→
headless `Scripts/install.py`（读 `L_Dungeon_Randomized` 生成器实时 `module_catalog_json`、
备份、写回、只存目标 OFPA 包、镜像回 DungeonRoutes 目录）。`install.py` 回执的
`spawn_pool_revision` 改为从配置 `revision` 字段读取，不再硬编码日期串。

## 边界与未做事项

- 只影响地牢导演刷出的实例（`WriteLevelRank` 只改实例 UPROPERTY，绝不动 CDO）；
  村庄/野外自然刷新与 F6 面板生成仍走各类默认。
- 名册未动：仍是 09-27 用户拍板的七种（无 NurseZombie/ZombieDog/手脑/巫婆）。
  **毒液僵尸 SpitterZombie**（09-28 近战版完成：normal/5 级/120 HP/咬 30）尚未入池——
  是否加入、进哪些家族属名册决策，留给用户拍板；加入时只需在配置加条目并重跑安装。
- 未运行 PIE、多种子或战斗测试；阶级与奖励数值以 `MonsterCoreStats` 现行公式为准。
