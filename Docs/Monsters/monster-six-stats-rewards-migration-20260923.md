# 怪物六维属性迁移与等级/奖励挂接（2026-09-23）

源项目：`E:/无尽轮回/长期备份/2026-7-13-1/game-dev`（`data/enemy-config.json`、
`src/config/enemy-base-stats.js`、`src/config/exp-system.js`、
`src/entities/damageable-entity.js`）。目标：`D:/FPS3D/FPSGAME`。只读源项目，未改动。

## 审计结论

| 怪物 | 六维来源 | str/dex/int/con/wis/luck | 等级 | 品阶 | 六维↔表面关联（原版公式复算） |
| --- | --- | --- | --- | --- | --- |
| 手脑 | 原 shounao 逐字 | 50/25/30/40/20/10 | 12 | Lord | Def=⌊1.5×40+.3×50⌋=**75**✓；HP1500、atk50、matk55、mdef65 为原配置直接指定 |
| 毒蛆 | 原 poisonMaggot 逐字 | 7/13/24/22/24/13 | 4 | Elite | Def **35**/Mdef **36**/抗暴 22✓；matk24 直接指定 |
| 胖子 | 原 fatZombie 逐字 | 18/6/3/20/3/5 | 4* | Normal | Def **35**/Mdef **4**/抗暴 20✓ |
| 突变体3 | 原 mutant3 逐字 | 50/30/5/40/10/6 | 9* | Elite | Def **75**/Mdef 13/抗暴 40✓ |
| 巫婆 | 原 witch 逐字 | 20/15/30/33/25/13 | 8* | Lord | Def **55**✓（Mdef55 为原直接覆盖，推导 39）；matk70 直接指定 |
| 野狼 | **UE 新增→反解** | 16/28/3/5/6/8 | 5* | Normal | Def **12**/Mdef **8**/抗暴 **5**/咬伤 **22** 全部由推导复现现行 UPROPERTY✓（参照 blackWolf 量级） |
| 护士 | **UE 新增→反解** | 3/27/3/0/0/3 | 3* | Normal | 平时无要害防具：Def **0**/Mdef **0**/抗暴 **0**✓（0.3×str<1 保持零减伤，与迁移前逐位一致）；接触伤 15=round(.5×3+.5×27) |

\* 星号等级为本次新增（此前仅手脑 12、毒蛆 4 有等级字段）。

**修复的空洞**：狼与护士原先在 `CombatFormulaRuntime::MonsterAttributes` 里落全 0
（狼的减伤全靠 UPROPERTY 特判撑着，护士完全没有身份）；5 只怪没有等级；任何怪没有品阶；
经验是写死常数、与等级无关；击杀不掉金币。

## 迁移实现

- **`Monsters/MonsterCoreStats.h/.cpp`（新）**：七怪六维+等级+品阶注册表（类识别优先，
  旧 `FatZombie/Mutant3/Witch` 标签回退保留，BP 兼容）。原版公式：
  `deriveEnemyCombatLevel`（图鉴战斗等级：六维主体 + HP≤+8、移速≤+4 封顶补充 + rank 加成，
  与配置等级并存的独立指标）、`getExpLevelMultiplier`（压级 diff>5 每级 −15%，
  下限 normal.01/elite.03/lord.05/boss.10；越级 +10%/级封顶 1.5）、
  `rollEnemyGoldReward`（`(L×4+rand[1,10])×0.5` 取整后乘 rank 金币倍率 elite2/lord3）。
- **各怪物类**：新增 `Level`/`Rank` UPROPERTY（默认=上表），实例可调；
  `MonsterAttributes` 改为读注册表——数值与迁移前逐位一致（checker 断言），伤害/抗暴行为零漂移。
- **奖励接入**（两个提交点，火球延迟击杀与普杀同口径）：
  `AwardKill` 经验 = `max(1, floor(ExperienceReward×压级/越级倍率))`×祭品 expPercent；
  金币按原公式掉落为 `gold` 物品（`ColdSteelInventory::Insert` 并入现有堆栈，包满丢弃，
  与地牢结算同语义）。未注册目标（训练假人、InventoryAudit 断言路径）倍率恒 1、金币 0，
  行为不变。
- 金币区间：护士 6~11、胖子 8~13、狼 10~15、毒蛆 16~26、突变体3 36~46、巫婆 48~63、手脑 72~87。

## 边界与未迁移项（如实）

- 原版经验 `base_g` 依赖地牢 grade 预算（pacingRuns 闭环）与有效等级锚点
  （F3/E13/D28…）；UE 地牢尚无 grade 字段 → **有效等级=配置等级**（等价 F 档），
  单怪经验保留 UE 现表面值作为 base（原版 maxHp/atk 同为直接指定口径）。
  整套 pacing 预算迁移建议等地牢有 grade 后再做。
- 地牢金币系数与金币祭品加成键在 UE 无对应 → 按 1 保留在公式形状里。
- 原版 rank `minor`（精英以下小 BOSS，exp×1、图鉴+1）UE 暂无使用者，枚举已留位。

## 全局生命成长层（同日追加，用户拍板全员翻倍）

`MonsterCoreStats::HealthMultiplier()=2.0`：七怪在各自 BeginPlay 初始化点
（护士系共用 `ANurseZombie::BeginPlay`，覆盖护士/胖子/突变体3/巫婆；手脑/毒蛆/狼单点）
把 `MaxHealth×=2` 后再 `Health=MaxHealth`。**生效血量**：护士 240、胖子 1200、狼 440、
突变体3 1500、巫婆 2600、毒蛆 1600、手脑 3000。选择倍率层而非改字面量：BP 实例覆盖值
同样放大、后续调参只动一个函数；狼的归巢回血读 `MaxHealth` 自动跟随；奖励/防具/六维
不受影响（原版 `monsterGrowth` 同一层语义）。`HandBrainAudit` 的 lord_stats 断言改为
`1500×HealthMultiplier()` 与旋钮联动。

## 状态

- 离线核查器 `Tools/Monsters/check_monster_core_stats.py`：**PASS（0 问题）**（上表与金币区间即其输出）。
- 构建：第一次尝试编译了含注册表调用的 `ColdSteelFireballModel.cpp`、`ColdSteelProfileRuntime.cpp`
  两文件通过，但被另一并行会话的未跟踪文件（`ColdSteelSmeltingVisualAudit.cpp:46` 格式串）挡住；
  追加生命层后两轮编辑器占用被守卫拒绝。**2026-09-23 23:10 编辑器关闭后全量构建成功**
  （46 actions，链接通过，43.64s，日志 `Saved/BuildEditor/build-20260923-231013.log`），
  含 `MonsterCoreStats.cpp`、全部怪物 BeginPlay 翻倍点与同期脚架改动。
- 未运行游戏测试（源码编译与运行验收分开）。实测重点：①各怪血条/击杀时间约翻倍
  ②护士/狼减伤仍与从前逐位一致③金币入包、压级经验衰减④狼归巢回血为翻倍后的 MaxHealth。
- 平衡提醒：单只经验值是翻倍前调的，击杀时间翻倍 ⇒ 单位时间经验产出约减半；若要在
  翻倍后维持原有练级速度，可整体上调各怪 `ExperienceReward`（或给护士系/狼单独加量）——
  属数值决策，等你拍板，不擅改。
