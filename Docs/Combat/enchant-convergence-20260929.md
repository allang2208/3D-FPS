# 附魔卷轴「汇聚」

2026-09-29 新增第五种附魔口径、第六张卷轴：后缀「汇聚」，只对狙击步枪生效，
把「逐发点杀」改成「一次射击打空弹匣、伤害聚合成一发」。

关联文档：[附魔工作台业务规则](../UI/enhancement-workbench-20260910.md)、
[附魔卷轴外观](../Art/magic-scroll-20260911.md)、[掉落稀有度光效](../Art/loot-rarity-glow-20260911.md)、
[涡轮增压（另一张模式改变卷轴）](enchant-turbocharger-20260929.md)。

## 词缀口径

| 项 | 值 |
| --- | --- |
| 卷轴 id / 物品 id | `convergence` / `enchant_scroll_convergence` |
| 名称 | 汇聚（后缀） |
| 限制 | `restriction: "sniper"`，只对 `weaponTypeTag == "狙击步枪"` 的武器成立 |
| 稀有度 / 费用 | rare / 400 魔法粉尘 |
| 物品售价 / 堆叠 | 2000 金 / 99 |
| 效果键 | `convergenceShot: true`、`convergenceDamageScale: 0.75` |

**类别键为什么读 `weaponTypeTag`**：狙击步枪只有 SVD 一把，它在目录里的 `weaponType` 是 `rifle`
（与 M4A1／AKM／QBZ-191／ASH-12／M16A2／A762 同类），只有 `weaponTypeTag` 区分出「狙击步枪」。
因此 `sniper` 这个键匹配 tag 而不是 type；以后新增狙击步枪只要 tag 仍是「狙击步枪」即自动生效，
换成别的 tag 就要同步这条规则。机枪卷轴的 `machineGun` 键走的仍是 `weaponType`，两者口径不同是数据现状决定的。

**位置互斥**：汇聚占后缀位，与「狼蛛」互斥；与前缀「骷髅射手」可共存（交互见下）。

## 数值

面板口径（不含角色 `atk`、弹药与强化加成，与工具提示同源）：

| 项 | 值 |
| --- | --- |
| 聚合倍率 | 消耗发数 × 75% |
| 余弹 1 发 | 单发的 75%（明确亏损，按字面口径不设门槛） |
| 满匣 10 发（SVD） | 85 × 10 = 850 → **637.5**（提示四舍五入显示 638） |

SVD 基准（`gunsmith.json`：`damage 85`、`mag_size 10`、`fire_interval 0.35`、`empty_reload_time 4.6`）：

| 对照 | 普通射击 | 汇聚 |
| --- | --- | --- |
| 单次结算伤害 | 85 | 637.5（×7.5） |
| 打空一匣总伤害 | 850 | 637.5（−25%） |
| 打空一匣耗时 | 9 个射击间隔 = 3.15 s | 首发即结算 |
| 含空仓换弹的整匣周期 | 3.15 + 4.6 = 7.75 s | 4.6 s |
| 周期内伤害/秒 | 109.7 | 138.6（+26%） |

两个口径要分开看：**同一批子弹**汇聚恒定交出 75%，永远是 −25%；
但**同一段周期**里少打 9 个射击间隔，摊薄换弹后反而快 26%。
一枪打死目标时汇聚明显吃亏，需要连打多匣时汇聚占优 —— 这是这张卷轴的取舍点，未做额外平衡修正。

## 运行时语义

- 开火时消耗弹匣内**当前全部**余弹（`MagazineAmmo` 直接归零），只产生**一次**命中判定：
  一次开火表现、一发弹丸、一条弹道、一次命中反馈。
- 本发伤害 = `DamagePerShot × 消耗发数 × 0.75`，随后走原有管线：射程衰减
  （`WeaponDamageFalloff`）、护甲结算、暴击与要害倍率全部照常。
- **伤害类型不变**：`UColdSteelStatusModel::ApplySkillWeaponHit` 用
  `Shot.DamagePanel.Scaled(Amount / DamagePanel.Total())` 推导各类型伤害，
  类型比例来自面板、总量来自标量；只缩放标量即可保持物理/魔法构成不变。
- 弹匣归零后按既有逻辑进入空仓换弹（SVD 4.6 s），换弹、切枪、施法交互动画不受影响。
- 射击间隔不新增参数：仍用 `FireInterval`（0.35 s）做节拍与实际射速上限，
  峰值射速不再是这张卷轴的关注点。

**护甲为什么不吃亏**：`CoreCombatFormula::Defense` 是按比例减伤
（`floor(Damage × (1 − Def/(Def+60)))`，下限 `floor(Damage × 10%)`），不是每次命中扣固定值，
所以「一发大伤害」与「十发小伤害」的减免比例相同；逐发 `std::floor` 取整反而让聚合弹少丢几次小数
（十发最多丢 10 点，一发最多丢 1 点）。

## 实现落点

| 位置 | 改动 |
| --- | --- |
| `ColdSteelEnhancementCombat.h/.cpp` | `FColdSteelConvergence`、`Convergence()`（读键，缺一项即不成立）、`ConvergenceShotScale()`（`DamageScale × Rounds`，未附魔恒为 1） |
| `ColdSteelEnhancementSystem.cpp` | `CanEnchant` 新增 `sniper` 类别键分支 |
| `FPSGAMECharacterProfile.cpp` | 随档案缓存 `ConvergenceParams`，与涡轮增压参数同一处解析 |
| `FPSGAMECharacter.h` | 新增 `FColdSteelConvergence ConvergenceParams` |
| `FPSGAMECharacter.cpp` | `FireShot`：按余弹扣弹并算出本发倍率；`ShotDamage = DamagePerShot × ConvergenceScale`；弹道发射改用 `ShotDamage` |

`ShotDamage` 同时供命中判定（`ApplyHit`）与弹道弹丸（`FPSBallisticsComponent::Launch`）使用，
两条路径共用同一个缩放值：SVD 的 `bullet_speed 520` 使它走弹道路径，
但同一改动也让 `ProjectileSpeedCM <= 0` 的枪械在命中路径上行为一致。

## 数据与规则改动

- `enhancement.json`：新增 `convergence` 卷轴条目（第 6 张）。
- `items.json`：新增 `enchant_scroll_convergence`（rare、售价 2000、`scroll_id: "convergence"`、图标沿用魔法卷轴）。
- `dungeon_loot.json`：`min_depth: 8` 档新增 `enchant_scroll_convergence`（weight 2，与其它附魔卷轴一致）。
- `tooltip-reference.json`：补 `enchant_scroll_convergence` 空条目。
- 规则层只新增分支，`firearm`／`weapon`／`sword`／`staff` 与既有卷轴判定未改动。

## UI 呈现

| 位置 | 呈现 |
| --- | --- |
| 物品提示 · 附魔效果卡 | 「射击模式：一次射击打空弹匣」「聚合伤害：消耗发数合计的 75%，类型沿用原枪械」 |
| 物品提示 · 战斗参数 | 「满匣聚合伤害：638（10 发合计 850）」「射击模式：一次射击打空弹匣，伤害类型沿用原枪械」 |
| 附魔台预览 | 「打空 10 发弹匣：合计 850 → 聚合 638 伤害」 |

三处都用当前实例的实时数值（含强化、改造、弹药加成），不是写死的 850／638。

**弹道表现**（2026-09-29 追加）：汇聚弹的曳光单独走一套表现——核心加粗 ×2、轨迹与光晕转纯白、
外绕一条自转的螺旋管，随弹光同步转白增亮。几何、CVar 与保持不变的曳光合同见
[汇聚弹曳光：加粗、纯白、螺旋环绕](../Weapons/convergence-tracer-20260929.md)。

## 与其他系统的交互

- **骷髅射手（前缀，穿透 +2）**：可共存。弹道弹丸在 `FPSBallisticsComponent` 内逐目标结算，
  每个被穿透的目标各自承受完整的聚合伤害与射程衰减 —— 三目标时单次开火合计 3 × 637.5。
  属于「穿透照旧、伤害照聚合」的叠加结果，未做额外限制。
- **暴击 / 要害**：保留既有倍率。SVD 的 `critDamageBonus 0.5` 与步枪要害加成作用于聚合后的总量，
  一枪要害收益被同步放大（按用户确认口径，不做屏蔽）。
- **弹药类型加成**：`DamagePerShot` 已含 `AmmoDamageMultiplier`，聚合计算在其之后，口径一致。

## 未改动边界

- `DamagePerShot`、`FireInterval` 等静态面板值仍是**单发**口径：角色面板、枪匠总览、HUD 伤害数字都不变，
  汇聚只改变开火时的扣弹数量与本发伤害，不写回静态字段。
- 不改弹匣容量、换弹时长、后坐力、散布与开火动画；一次开火就是一次表现。
- 未给汇聚加节拍参数、未加最低余弹门槛、未屏蔽暴击（均为用户确认口径）。
- 静态对比表（`ColdSteelItemTooltipSummary`）不体现该效果：它是模式改变而非静态属性增减，
  与涡轮增压的处理一致。

## 验证

按用户规则**未运行**编辑器、PIE、截图或验收用例；实战读数与手感由用户测试。
`ColdSteelEnhancementAudit` 补了一条源码断言（卷轴定义能加载、SVD 为真、突击步枪为假），同样未运行。

编译状态（`FPSGAMEEditor Win64 Development`，日志 `Saved/BuildEditor/build-20260929-193319.log`）：

| 文件 | 结果 |
| --- | --- |
| `ColdSteelEnchantmentCombat.cpp` / `FPSGAMECharacter.cpp` / `FPSGAMECharacterProfile.cpp` / `ColdSteelEnhancementSystem.cpp` | 通过（对象文件均晚于源码） |
| `ColdSteelItemTooltipData.cpp` / `ColdSteelEnhancementWidget.cpp` / `ColdSteelEnhancementAudit.cpp` | 通过（本批次编译动作） |
| 链接 | `Result: Succeeded`，`UnrealEditor-FPSGAME.dll` 19:33:26 |
| 符号核对 | DLL 内含 `ColdSteelCombat::Convergence`、`ConvergenceShotScale` 与 `convergenceShot`／`convergenceDamageScale`／`狙击步枪` 字面量 |

首版曾在改造台产品预览时崩溃（`BuildColdSteelItemTooltip` 第 373 行 `EE` 空指针断言，见上方「实现注意」）。
已修为判空读键，复跑构建 `Result: Succeeded`（`Saved/BuildEditor/build-20260929-200206.log`），
`UnrealEditor-FPSGAME.dll` 20:02:20，对象文件晚于源码。该路径由用户实测暴露，修复后尚未再次实机验证。

四个 JSON 改动后均用解析器复核通过，卷轴 `item` 字段与物品 `scroll_id` 双向一致。

### 实现注意

`UColdSteelEnhancementSystem::Effect()` 对 JSON **布尔**字段返回 1/0（`convergenceShot: true` 因此可用），
但工具提示里的局部 `Number()` 助手只读数字字段，布尔会读成 0。
物品提示读该键必须用 `TryGetBoolField`，与既有 `poisonOnHit` 的读法一致；
附魔台预览走 `Effect()` 可以直接读。

**`EE`（`_enchantEffects`）必须判空后再解引用**。工具提示的 `Number()` 助手自带判空
（`O&&O->TryGetNumberField`），但 `EE->TryGetBoolField(...)` 是直接解引用：
无附魔物品没有 `_enchantEffects`，`EE` 为空，会命中 `TSharedPtr::operator->` 的断言。
首版在战斗参数段漏了这道判空，改造台产品预览（`ColdSteelGunAssemblyWidget::RefreshProductPreview`）
构建无附魔武器提示时崩溃，已修为 `if(EE)EE->TryGetBoolField(...)`。
新增任何读附魔键的代码都要沿用这个判空；同类键在附魔效果卡内已有 `if(EE)` 外层保护。