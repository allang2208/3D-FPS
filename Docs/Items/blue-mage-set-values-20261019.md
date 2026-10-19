# 蓝魔法师五件套：防御与效果（2026-10-19）

用户要求：为蓝魔法师套（帽 + 袍 + 裤 + 靴 + 手套）设置合理的防御力强化数值，并按部件设置效果：帽子 +10% 魔法攻击力；长袍 +50% 施法距离、−10% 移动速度；手套 +30% 施法速度、−10% 换弹速度／拉弓速度／近战攻击速度；裤子 −25% 魔法系冷却时间；靴子 −25% 魔法系消耗。穿齐五件再额外 +50% 施法距离、+10% 魔法攻击力。

## 结论

| 部件 | 物品 ID | 防御（items.json） | +10 强化 | 部件效果（source-combat-items） |
| --- | --- | --- | --- | --- |
| 蓝色尖顶法师帽 | `ue_blue_mage_hat` | **4 / 每级 +0.8** | 12 | `magicAttackPercent +0.10` 魔法攻击力 +10% |
| 蓝色法师长袍 | `ue_blue_mage_robe` | **8 / 每级 +1.5** | 23 | `castRangePercent +0.50` 施法距离 +50%；`moveSpeedPercent -0.10` 移动速度 −10% |
| 黑色法师长裤 | `ue_blue_mage_pants` | **6 / 每级 +1.0** | 16 | `magicCooldownPercent -0.25` 魔法冷却 −25% |
| 蓝黑法师长靴 | `ue_blue_mage_boots` | **6 / 每级 +0.8** | 14 | `magicCostPercent -0.25` 魔法消耗 −25% |
| 蓝色法师手套 | `ue_blue_mage_gloves` | **4 / 每级 +0.6** | 10 | `castSpeedPercent +0.30` 施法速度 +30%；`reloadSpeed -0.10` 换弹速度 −10%；`bowDrawSpeed -0.10` 拉弓速度 −10%；`meleeAttackSpeed -0.10` 近战攻击速度 −10% |

- 五件基础防御合计 **28**；全部 +10 后合计 **75**。
- 五件套额外效果：**施法距离 +50%、魔法攻击力 +10%**（与部件效果相加：长袍 +50% + 套装 +50% = 施法距离 ×2.0；帽子 +10% + 套装 +10% = 魔法攻击力 ×1.2）。

## 防御取值依据

- 结算：`UColdSteelEnhancementSystem::Defense` = `floor(base + perEnhance × enhanceLevel)`，护甲强化上限 10；角色防御把所有 `Place==1` 装备的防御相加。
- 减伤：`max(floor(Damage × (1 − Def/(Def+60))), floor(Damage × 0.1))`。
- 对照权威表的胸甲档：法袍 7/+1（+10 为 17）、蚀月 9/+1.5（24）、苍月 12/+2（32）、流云 13/+2.5（38）、神谕 15/+2.6（41）。本套胸甲取 **8/+1.5（+10 为 23）**，落在法袍与蚀月之间，符合“布甲法师套”的定位。
- 五件 +10 合计 75，低于苍月整套（32 + 手套 + 鞋靴等）的重甲线，也明显低于壁垒/镇岳/天罡的胸甲单件；高于当前 ST6 战术套（+10 约 68），但本套占用全部五个防具槽，且用 −10% 移速、−10% 换弹/拉弓/近战攻速换取魔法收益。
- 小数成长沿用 `ue_field_gloves` 的 2/+0.5 写法；`floor` 后个别等级会出现平级，这是现有防御公式的既有表现。旧模板“小件 +1、胸甲 +2”是单件重甲口径；五件套若照搬会到 88，故本套按五件合计压到 75。

## 效果接入（真实消费端）

### 1. 魔法攻击力

- 键：`magicAttackPercent`（帽子 +0.10；五件套再 +0.10）。
- 消费端：`UColdSteelStatusModel::AdjustCombatStat("matk")` 在 `Derived("matk")` 上乘 `1 + EquipmentBonus("magicAttackPercent") + SetEffect("magicAttack")`。
- 结果：角色面板魔法攻击、火球/冰锥/闪电/圣光/暴风雪/火焰/雷电等以 `Derived("matk")` 为输入的技能伤害同步提高。

### 2. 施法距离

- 键：`castRangePercent`（长袍 +0.50；五件套再 +0.50）。
- 消费端：`UColdSteelStatusModel::MagicRangeMultiplier()` = `max(0.1, 1 + EquipmentBonus("castRangePercent") + SetEffect("castRange"))`，各法术在生成施法结构时乘到 `Range`：
  - 火球 `ColdSteelFireballModel.cpp`
  - 冰锥 `ColdSteelIceSpikeModel.cpp`
  - 闪电 `ColdSteelLightningModel.cpp`
  - 圣光 `ColdSteelHolyLightModel.cpp`
  - 冰墙 `ColdSteelIceWallModel.cpp`
  - 暴风雪 `ColdSteelBlizzardModel.cpp`
  - 火焰系 `ColdSteelFireMagicModel.cpp`
  - 雷电系 `ColdSteelElectricMagicModel.cpp`
- 只放大“施法距离”本身，不放大爆炸半径、连锁范围、冰墙段数等范围参数；法杖改造的 `magicRangePercent` 仍在各自分支内先乘，二者为乘法叠加。

### 3. 施法速度

- 键：`castSpeedPercent`（手套 +0.30）。
- 消费端：`UColdSteelStatusModel::ApplySpellbookFocus()` 开头乘 `max(0.1, 1 + EquipmentBonus("castSpeedPercent"))`，随后才处理魔法书专注的 `castSpeedMultiplier`。
- 该接入不依赖法杖或魔法书：只穿手套也会生效；与法杖改造的 `castSpeedPercent` 为乘法叠加。

### 4. 魔法冷却

- 键：`magicCooldownPercent`（裤子 −0.25）。
- 消费端：`UColdSteelStatusModel::SetEffect("cooldown")` 现在把“旧三件套冷却缩减”和装备冷却合并：
  `return 1 - (1 - LegacyReduction) * max(0.1, 1 + EquipmentBonus("magicCooldownPercent"))`
- 现有所有 `(1 - SetEffect("cooldown"))` 公式（火球、冰锥、闪电、圣光、冰墙、暴风雪、火焰、雷电、冰甲、闪电迅捷、法杖读盘）自动获得裤子的 −25%，无需逐技能改公式。
- 符号沿用 `bonusStats` 约定：负值 = 更短冷却；下限仍由各技能 `max(0.2, …)` 保护。

### 5. 魔法消耗

- 键：`magicCostPercent`（靴子 −0.25）。
- 消费端：`SpellManaCostBeforeFocus()` 在既有法杖改造/符文/连锁计算之后乘 `max(0, 1 + EquipmentBonus("magicCostPercent"))`，再进入 `ApplySpellbookFocus` 的魔法书消耗倍率。
- 对火球、冰锥、闪电、圣光、冰墙、暴风雪、火焰、雷电、冰甲、闪电迅捷等所有走该函数的法术生效。

### 6. 五件套判定

- 现有 `ArmorSet()` 只认头盔（1）+ 铠甲（7）+ 鞋靴（13）三件同 `armorSet`，裤子和手套不参与，无法直接表达五件套。
- 本套给五件都写入 `armorSet: "blue_mage"`；新增 `UColdSteelStatusModel::BlueMageSetComplete()`：先要求 `ArmorSet()=="blue_mage"`（覆盖帽/袍/靴），再检查手套（3）和裤子（15）也都是 `blue_mage`。
- `SetEffect("castRange")` / `SetEffect("magicAttack")` 只在 `BlueMageSetComplete()` 为真时返回 +0.50 / +0.10，因此五件套奖励不会在缺件时误触发。
- `ArmorSet()` 改用 `CombatItemFormula::ReadOnly`（有界 128 条缓存），避免每次 `SetEffect` 重复解析 JSON；语义不变。

## 覆盖检查：现有魔法技能与后续新增

现有 13 个魔法技能的 `*Stats()` 入口全部检查过：

| 技能 | 魔攻 `matk` | 施法距离 | 施法速度 | 冷却 | 消耗 |
| --- | --- | --- | --- | --- | --- |
| 火球 `fireball` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 冰锥 `iceSpike` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 闪电 `lightningStrike` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 圣光 `holyLight` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 冰墙 `iceWall` | —（INT/WIS 物理段） | ✅ | ✅ | ✅ | ✅ |
| 暴风雪 `blizzard` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 陨石 `meteor` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 烈焰护甲 `flameArmor` | ✅ | ✅（自身增益，通常无距离） | ✅ | ✅ | ✅ |
| 龙息 `dragonBreath` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 雷暴领域 `stormDomain` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 雷枪 `thunderLance` | ✅ | ✅ | ✅ | ✅ | ✅ |
| 冰甲 `iceArmor` | ✅（护盾） | —（自身增益） | ✅ | ✅ | ✅ |
| 闪电迅捷 `lightningHaste` | —（纯速度增益） | —（自身增益） | ✅ | ✅ | ✅ |

- **冷却 / 消耗 / 施法速度**：13 个技能全部调用 `SetEffect("cooldown")`、`SpellManaCostBeforeFocus()`、`ApplySpellbookFocus()`。这三项是当前最接近“通用”的部分，但仍是每个 `*Stats()` 手动调用，不是引擎强制。
- **施法距离**：11 个有距离的技能全部调用 `MagicRangeMultiplier()`；冰甲、闪电迅捷是自身增益，没有施法距离，不适用。
- **魔攻**：11 个伤害/治疗/护盾技能使用 `Derived("matk")`；冰墙按设计走 INT/WIS 物理段，闪电迅捷是纯速度增益，不适用。若要让冰墙也吃帽子/套装魔攻，需要改它的伤害公式，是平衡决策。
- **施法速度的边界**：`castSpeedPercent` 只作用在 `TryBeginSpellGesture` 的起手/施法手势；雷电系的蓄力窗口由 `LightningHaste::ActionSpeed` 控制，引导/持续/坠落时间也不随施法速度缩短。若要让手套加速蓄力，需要把 `CastSpeed` 另行乘进 `MinCharge/MaxCharge`，这是额外的机制改动。
- 闪电的 `LightningStats(..., false)` 只用于雷电家族内部取子命中，外层 `ElectricMagicStats()` 会再 `ApplySpellbookFocus`；新技能不要用 `false` 绕过。

### 新增技能接入清单

1. 伤害/治疗/护盾若吃魔攻，用 `Derived("matk")`。
2. 有施法距离的，在法杖 `magicRangePercent` 之后加 `C.Range *= float(MagicRangeMultiplier());`，保持乘法顺序。
3. `C.ManaCost = SpellManaCostBeforeFocus(Id, L);`
4. `C.Cooldown *= FMath::Max(.2, (1 - CooldownReduction) * (1 - SetEffect(TEXT("cooldown"))));`，再乘符文/技能自己的冷却系数，保持现有顺序。
5. 最后 `ApplySpellbookFocus(C.CastSpeed, C.ManaCost);`
6. 五件套不用逐技能判断：`SetEffect` / `MagicRangeMultiplier` 内部已处理。

**自动继承范围**：`FireMagic` / `ElectricMagic` 家族新增 ID，只需加入 `FireMagic::IsSkill` / `ElectricMagic::IsSkill` 和对应 `*Definition`，共享的 `FireMagicStats()` / `ElectricMagicStats()` 会自动带上 5 项。只加 `IsSkill` 不加对应 `*Definition` 会回落到陨石/雷枪默认数据，必须同时补 Definition。**独立新模型没有公共基类或自动注入**，必须手动照上面 5 步接；这是当前架构的缺口，不是词条本身的问题。

## 浮窗

- 详细浮窗：`ColdSteelItemTooltipData.cpp` 的 `bonusStats` 键表新增五个键与中文标签：
  - `magicAttackPercent` → 魔法攻击力（越高越好）
  - `castRangePercent` → 施法距离（越高越好）
  - `castSpeedPercent` → 施法速度（越高越好）
  - `magicCooldownPercent` → 魔法冷却（越低越好）
  - `magicCostPercent` → 魔法消耗（越低越好）
- 简略浮窗：`ColdSteelItemTooltipSummary.cpp` 同步五个字段与百分比/越低越好着色。
- 五件都写入 `setBonusDesc`：`五件套：施法距离 +50%，魔法攻击力 +10%`；浮窗在“套装效果”段显示。
- `desc` 仍只写外观，不重复数值。

## 改动文件

- 数据：`Content/ColdSteelData/items.json`（五件 `defense.base/perEnhance`）、`Content/ColdSteelData/source-combat-items.json`（五件 `armorSet`/`setBonusDesc`/`bonusStats`）。
- 代码：
  - `Source/FPSGAME/UI/ColdSteelStatusModel.h`
  - `Source/FPSGAME/Combat/ColdSteelFormulaBonuses.cpp`
  - `Source/FPSGAME/Skills/ColdSteelSpellMana.cpp`
  - `Source/FPSGAME/Skills/ColdSteelFireballModel.cpp`
  - `Source/FPSGAME/Skills/ColdSteelIceSpikeModel.cpp`
  - `Source/FPSGAME/Skills/ColdSteelLightningModel.cpp`
  - `Source/FPSGAME/Skills/ColdSteelHolyLightModel.cpp`
  - `Source/FPSGAME/Skills/ColdSteelIceWallModel.cpp`
  - `Source/FPSGAME/Skills/ColdSteelBlizzardModel.cpp`
  - `Source/FPSGAME/Skills/ColdSteelFireMagicModel.cpp`
  - `Source/FPSGAME/Skills/ColdSteelElectricMagicModel.cpp`
  - `Source/FPSGAME/UI/ColdSteelItemTooltipData.cpp`
  - `Source/FPSGAME/UI/ColdSteelItemTooltipSummary.cpp`

## 状态

- 数据与代码已落盘。
- 编译：本轮改动的 12 个 `.cpp` 的 `.obj` 均在 2026-10-19 21:03–21:04 成功生成（源文件最后修改 20:59–21:01），说明新增声明与调用可通过编译。随后整包 Editor 构建在无关文件 `Source/FPSGAME/Skills/LightningHastePresentation.cpp` 的 `TObjectPtr` 迭代错误处失败，未完成 DLL 链接；该文件不属于本套改动，未修改。**在重新构建成功前，运行时仍加载旧 DLL，本套新效果不会生效。**
- 未启动游戏/PIE、未做截图验收；实机数值与浮窗由用户验收。
- 已知取舍：五件套奖励用独立 `BlueMageSetComplete()` 判定，而不是扩展现有 `ArmorSet()` 的三槽语义，避免影响旧套装；裤子的冷却缩减通过 `SetEffect("cooldown")` 合并，旧套装的冷却公式无需逐个改动。