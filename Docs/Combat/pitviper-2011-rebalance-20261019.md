# Pit Viper 2011：系数重拟与自带护甲穿透（2026-10-19）

用户要求（2026-10-19）：先调 Pit Viper 2011——自带 25% 护甲穿透；伤害公式做成现在的 2 倍（不许直接乘 2，要改公式里的系数），并把敏捷做成主属性（系数至少为精神的 1.5 倍）；改完检查背包栏浮窗是否显示正确。

## 一、公式逐项重拟（`Content/ColdSteelData/combat-weapon-formulas.json`）

| 项 | 旧值（`PITVIPER2011_COEFF_DESIGN`） | 新值（`PITVIPER2011_DEX_REBALANCE_2X_20261019`） | 倍数 |
| --- | ---: | ---: | ---: |
| `base` | 7 | 14 | ×2 |
| `enhanceFlat`（每级强化） | 0.4 | 0.8 | ×2 |
| 敏捷 `dex` 基础系数 | 0.30 | 0.66 | ×2.20 |
| 敏捷 `dex` 每级系数 | 0.045 | 0.102 | ×2.27 |
| 精神 `wis` 基础系数 | 0.25 | 0.44 | ×1.76 |
| 精神 `wis` 每级系数 | 0.040 | 0.068 | ×1.70 |

设计约束的落法：

- **总倍率恒为 2 倍**：base、每级平增、敏捷+精神系数总和（0.55→1.10）、每级系数总和（0.085→0.17）全部正好翻倍，所以任意 `(dex, wis, L)` 下公式结果都是旧值的 2 倍，不是"某个档位凑巧 2 倍"。
- **敏捷成为主属性**：dex:wis 的基础比从 `1.20 : 1` 提到 `1.50 : 1`，每级比同样 `1.50 : 1`。倍率内部不是各自 ×2，而是把精神让出来的 0.06（每级 0.013）并给敏捷，总额不变——这样"翻倍"和"主属性"两个要求同时严格成立。
- 攻击力上限没动：强化仍上限 +15，面板沿用 `Round(公式) × (1+精通%) + 精通平伤`。

面板结果（公式值 → 含手枪精通的最终面板）：

| 档位 | 旧公式 | 新公式 | 新/旧（公式） | 旧面板 | 新面板 | 新/旧（面板） |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| A 初始 dex=wis=10 / +0 / 精通 0 | 12.5 | 25 | ×2.00 | 13 | 25 | ×1.92 |
| B 中期 dex=wis=30 / +5 / 精通 10 | 38.25 | 76.5 | ×2.00 | 52 | 95 | ×1.83 |
| C 后期 dex=wis=60 / +15 / 精通 30 | 122.5 | 245 | ×2.00 | 190 | 349 | ×1.84 |

面板倍数低于 2 是因为精通平伤（+精通等级）不随公式翻倍，公式本身严格 2 倍。

## 二、自带护甲穿透 25%

- 数据：`Content/ColdSteelData/items.json` 的 `ue_pit_viper2011` 增加 `"innate_armor_penetration": 0.25`；同条目 `stats` 的展示值 22 → 44（旧值按 dex=wis≈27 标定，新公式同基线 43.7 → 44）。
- 结算：`ColdSteelSkillRules::Snapshot` 把自带值加进 `Shot.ArmorPenetration`，与改造 `armorPenetrationPercent`、附魔同键、弹种 `physical_armor_penetration` 同路相加；发弹分支 `clamp(…, 0, 1)`，因此 25% 与 .45/AP 类叠加也不会超过 100%。
- 生效点：`WeaponHit.PhysicalPenetration = Shot.ArmorPenetration` → `CombatFormulaRuntime::MitigateMonster`（`ActiveWeaponHit` 分支）→ `CoreCombatFormula::Defense` 里 `Def = floor(Def × (1 − 穿透))`，下限仍是 10% 伤害。
- 对常见目标的实际收益（防御 75 → 56、84 → 63）：变异体/手脑类约 +6~8% 命中伤害，护士、狼等低防目标几乎不变。

## 三、预期伤害（含暴击期望与穿透）

| 目标（Def/抗暴） | B 档旧 | B 档新 | C 档旧 | C 档新 |
| --- | ---: | ---: | ---: | ---: |
| 护士（0/0） | 63 | 115 | 349 | 642 |
| 狼（12/5） | 50 | 96 | 275 | 528 |
| 胖僵尸（35/20） | 33 | 67 | 172 | 350 |
| 变异体（75/40） | 23 | 49 | 87 | 187 |
| 大手（84/45） | 21 | 46 | 79 | 170 |
| 理论 DPS | 347 | 633 | 1267 | 2327 |
| 持续 DPS（含 1.75s 换弹、15 发） | 203 | 370 | 740 | 1360 |

## 四、浮窗显示

- 详细浮窗（`ColdSteelItemTooltipData.cpp`）新增一行 `护甲穿透 25% 物理防御`，紧跟在 `暴击伤害加成` 之后；攻击力两行（`攻击力计算公式`、`强化后攻击力公式`）由 `AppendColdSteelTooltipAttackFormula` 直接读同一份公式，会显示 `14+0.66×敏捷+0.44×精神` 与 `14+0.8L+(0.66+0.102L)×敏捷+(0.44+0.068L)×精神`。
- 伤害行 `伤害 / 基础物理 / 含弹种调整伤害` 走 `DamageParts`，与实战同一条 `ProcessedDamage` 链，因此与新面板一致（武器浮窗会跳过 items.json 的旧 `物理攻击` 行，不会出现两个数字）。
- 摘要/对比浮窗（`ColdSteelItemTooltipSummary.cpp`）在 `有效射程` 之后新增次要指标 `护甲穿透 25%`，不进核心对比行。
- 公式表 `WeaponFormulas` 在 `UColdSteelEnhancementSystem` 初始化时读盘，改 JSON 后需要重启游戏（或重新初始化子系统）才会刷新，热改文件不会即时生效。

## 五、改动文件

- `Content/ColdSteelData/combat-weapon-formulas.json`（Viper 系数）
- `Content/ColdSteelData/items.json`（`innate_armor_penetration`、展示值）
- `Source/FPSGAME/Skills/ColdSteelSkillRules.cpp`（自带穿透并入 `Shot.ArmorPenetration`）
- `Source/FPSGAME/UI/ColdSteelItemTooltipData.cpp`、`Source/FPSGAME/UI/ColdSteelItemTooltipSummary.cpp`（浮窗两处显示）

## 六、验证范围

本轮只做静态核对与编译；未开编辑器、未进 PIE、未做实际命中验收。浮窗显示按代码路径确认，实际排版与数字需用户进游戏复核。