# 枪械伤害公式：链路核对与联机口径修复（2026-10-19）

用户要求（2026-10-19）：核对枪械类武器伤害公式有没有遗漏。逐段核完后确认主链完整，但联机权威复算有两处真遗漏（P1、P2）、两处信任面/口径问题（P3、P4），另有暴击判定口径（P7）需要统一；P5 经用户确认为设计本意，P6 验证为数学等价。本轮把这些一次性处理掉，不改任何数值调节。

## 一、单发伤害的完整链路

```
面板 = 武器公式(combat-weapon-formulas.json · World-122 六维)
      × (1 + 强化等级×0.05) × 工艺品质(0.75–1.25) × (1 + 工艺伤害%)
      × 精通加成(步枪/手枪/霰弹枪/机枪) × (1 + 附魔伤害%)
单发 = 面板 × 弹种伤害倍率 × 汇聚倍率
单颗 = 单发 / 弹丸数 × 距离衰减
暴击 = 单颗 × (1 + 要害% [仅步枪]) × (1 + 暴击加成 + 赌徒层数)
最终 = 命中 × (1 − Def′/(Def′+60))，下限 floor(0.1 × 命中)
       Def′ = Def × (1 − 物理穿透) × 腐蚀；魔法段用魔抗与魔法穿透，物理穿透不作用
```

| 环节 | 位置 | 说明 |
| --- | --- | --- |
| 武器面板 | `UColdSteelEnhancementSystem::ProcessedDamage`（`Source/FPSGAME/UI/ColdSteelEnhancementSystem.cpp:109`） | 公式只做重定标 `×Base/W->Base.Damage`；强化、工艺、附魔、精通都在这里 |
| 弹种倍率 | `AFPSGAMECharacterProfile::DamagePerShot`（`Source/FPSGAME/FPSGAMECharacterProfile.cpp:154`） | 步枪 AP `×1.05`、独头 `×0.75`、箭形 `×0.9`，普通弹 `1.0` |
| 汇聚 | `ColdSteelCombat::ConvergenceShotScale` | 整匣伤害聚合到一发；发数由服务端按弹匣容量上界钳制 |
| 弹丸数 | `UColdSteelAmmoRuntime::AmmoProjectileCount` | 12G 8 颗（独头 1 颗），每颗均分整发伤害 |
| 距离衰减 | `WeaponDamageFalloff::Multiplier`（`Source/FPSGAME/Weapons/WeaponDamageFalloff.h`） | 有效射程内 `1.0` → 2× 射程处线性降到 `0.1` → 之后地板 `0.1` |
| 要害/暴击 | `UColdSteelStatusModel::ApplySkillWeaponHit`（`Source/FPSGAME/Skills/ColdSteelSkillModel.cpp:184`） | 要害必暴；`WeakpointPercent` 只对步枪生效（步枪精通） |
| 防御 | `CoreCombatFormula::Defense`（`Source/FPSGAME/Combat/CoreCombatFormula.h:34`） | 物理/魔法分开，穿透 0–1，10% 伤害地板 |
| 易伤链 | `CombatFormulaRuntime::MitigateMonster`（`Source/FPSGAME/Combat/CombatFormulaRuntime.cpp:45`） | 冻结 ×1.5(物理)、魔法易伤/石化、无人机、来源减伤、金刚、标记、圣佑 |
| 收口 | `ApplyPointDamage` + `LimitedTo(剩余HP)` | 基础/附加两段结算，超杀钳到剩余生命 |

枪械没有任何配件改伤害/穿透/射程的数据（19 把枪的全部 `options[*].stats` 只有后坐、散布、ADS、换弹、弹匣、弹速），所以不存在"配件加成没生效"这一类遗漏。

## 二、本轮修复

| 编号 | 问题 | 修法 |
| --- | --- | --- |
| **P1** | 联机权威复算只给霰弹枪乘了弹种倍率，步枪/手枪分支 `PelletScale=1` → 远端客户端打 AP 弹少 5%，主机/单机正常 | `ComputeServerDamage` 先把 `AmmoDamageMultiplier` 取成公共项，霰弹枪再除弹丸数 |
| **P2** | 穿透/散弹的射速令牌按"整发"计费：非霰弹枪每个接触点都花 1 个令牌，连射时合法穿透会被 `rate` 拒掉 | 令牌改为 `1/(弹丸数×(1+弹种穿透+附魔穿透))`，覆盖全部开火命中（近战/旋风不受影响） |
| **P3** | 汇聚发数只按弹匣容量钳制，服务端不核影子余弹 | 影子档案上传滞后于命中上报，硬钳会误伤连发，故改为**漂移记录**（`MPTEST convergence drift` 警告），结算仍按容量上界 |
| **P4** | 枪型类别位（`bRifle`/`bPistol`）采信客户端 flag，可让手枪申报成步枪 | 服务端按影子里的真实武器用 `ColdSteelSkills::IsRifle/IsPistol` 重算这两位 |
| **P7** | 暴击逐弹丸各掷：8 颗霰弹在 5% 面板概率下"至少一发暴击"约 39%，面板与实际不符 | 开火时预掷一次样本 `Shot.CriticalRoll`，同一发的全部弹丸/穿透目标共用；服务端按上报开火时刻归并（窗口 0.9×射速间隔、上限 0.25 s，绝不跨两发） |

要点：

- P1 的影响面是"远端客户端"，单机与主机本来就是对的；修复后三条路径同口径。
- P2 只在存在穿透（弹种 `target_penetration` 或附魔 `piercingBonus`）或多弹丸时才改变令牌消耗，无穿透时仍是 1。
- P7 不改暴击概率与暴击倍率，只把"一发一次判定"落实；近战/武技的多目标命中仍逐个敌人各掷（保持独立判定）。
- 暴击样本由服务端掷（客户端只报几何与语义），不存在"客户端挑样本必暴"的漏洞。

## 三、确认为设计本意 / 无需改动

- **P5 没有硬射程上限**：衰减在 2× 有效射程后维持 10% 地板，`TraceDistance = max(1000 m, 3×射程)`，服务端的 `MaxRange` 只作抗伪造上限。经用户确认这是设计本意，本轮不改。
- **P6 武器暴击在防御前、法术暴击在防御后**：两者都是乘性、可交换，`floor(A·c·f)` 与 `floor(floor(A·f)·c)` 只在逐段取整上差 ≤1 点。搬动它会牵动削韧与回血口径，故保留现顺序并在代码处注明（`ColdSteelSkillModel.cpp` 暴击行）。
- **要害倍率只给步枪**：手枪/霰弹枪爆头只有暴击加成，`WeakpointPercent` 属于步枪精通，保持现状。
- **霰弹枪削韧边界**：沿用与伤害衰减同源的有效射程（见 [霰弹枪射程内削韧](firearm-toughness-damage-20261019.md)）。

## 四、未改动

- 目录数值、弹药数值、武器公式表、强化/工艺/附魔/精通系数一律不动，本轮只改判定与复算口径。
- 客户端预测路径的伤害公式不变；服务端复算只是补齐 P1 的弹种倍率。

## 五、状态

- 源码已改；构建与部署状态见提交说明。
- **P1–P4 与 P7 的服务端归并落在 `Source/FPSGAME/Multiplayer/ColdSteelPlayerState.{h,cpp}`**，该文件此刻正是另一会话未提交的命中上报重写（工作树 1769 行 vs HEAD 1297 行），无法单独重建发布；这些改动随那份重写一起发布。
- 其余改动（`ColdSteelSkillTypes.h`、`ColdSteelSkillModel.cpp`、`FPSGAMECharacter.{h,cpp}`、`FPSBallisticsComponent.cpp`、`ColdSteelSuper90Authority.cpp`）独立提交。
- 未做运行期验证，按用户规则由用户自行测试。