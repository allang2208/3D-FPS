# 硬壳手套 / ST6 战术上衣 数值与浮窗（2026-10-18）

用户要求：为 `ue_hardknuckle_gloves`（硬壳战术手套）与 `ue_st6_sleeves`（ST6 战术上衣）设置防御数值与效果，浮窗沿用其他装备的写法；同时给出后续装备可复用的取值标准。

> 修正记录（同日）：第一版把 `bonusStats` 写进 items.json，并新造了 `adsTimePercent` 这个名字。实际上——
> 1. 装备的战斗/手感数值既有权威表是 `Content/ColdSteelData/source-combat-items.json`（`ue_field_gloves`: meleeAttackSpeed/reloadSpeed/bowDrawSpeed；`ue_steel_gauntlets`: −10%；各套装的 defense/armorSet 也在这里），运行时由 `CombatItemFormula::Read` 对缺失字段做覆盖，所以 field gloves 的 +10% 换弹今天就是从这张表生效的。
> 2. ADS 瞄准时间（开镜耗时）本来就是武器属性：`FGunsmithStats::ADS`（秒），配件写 `ads_percent`（时间百分比，负值更快）/`ads_seconds`，弓写 `ads_mult`，面板与浮窗直接显示它。
> 本次已把两件装备的 `bonusStats` 移到权威表，并把装备层键名改成与既有语义一一对应的 `adsPercent`（等价于配件 `ads_percent`），不再新造概念。

## 结算机制（先确认，避免写“只显示不生效”的字段）

- 数值分层：**items.json** 管物品身份与 `defense`（与 `ue_field_gloves` 同惯例）；**source-combat-items.json** 管装备 `bonusStats`/`armorSet` 等战斗数值，`CombatItemFormula::Read` 只补齐实例里缺失的顶层字段——所以同名键在两处都有时，实例快照（items.json 创建时写入）优先。
- 装备防御：`UColdSteelEnhancementSystem::Defense` = `floor(base + perEnhance × enhanceLevel)`，强化上限 `ArmorMax=10`。
- 角色防御：`UColdSteelStatusModel::Derived("def")` 把所有 `Place==1` 装备的防御相加（手套、铠甲、鞋靴等都算），再乘武器工艺 `defensePercent`；角色自身还有 `floor(Con×1.5 + Str×0.3)` 的基础防御。
- 伤害减免：`CoreCombatFormula::Defense` = `max(Damage × (1 − Def/(Def+60)), Damage×10%)`。
- `bonusStats` 真实生效键：`str/dex/int/con/wis/luck`、`maxHp/maxMp`、`atk/matk/crit`、`meleeAttackSpeed`、`meleeStaminaCost`、`moveSpeedPercent`、`reloadSpeed`、`bowDrawSpeed`、`adsPercent`、`sprintStaminaCost`；百分比键用小数（`0.05` = 5%）。
- `adsPercent`：装备层对既有 ADS 属性的修正，语义＝配件 `ads_percent`（时间百分比，**负值更快**）。`UColdSteelStatusModel::ADSTimeMultiplier()` 返回 `clamp(1+bonus, 0.5, 1.5)`；枪械在 `FPSGAMECharacterProfile.cpp` 乘进 `ADSInDuration`，弓在 `BowWeaponComponent::RefreshEquipment` 乘进 `AimInSeconds/AimOutSeconds`，武器浮窗的「开镜耗时」同乘该倍率，三处一致。
- `sprintStaminaCost`：`SprintStaminaPerSecond()` 乘 `max(0, 1+bonus)`；角色面板「奔跑 X/秒」与真实消耗同步。
- `defense.damageReduction`、`defense.staminaCost` 只在盾牌与浮窗上出现，普通护甲没有消费端，本次不写。
- `armorSet` 生效需要槽位 1 头盔 + 7 铠甲 + 13 鞋靴三件同 ID（`UColdSteelStatusModel::ArmorSet`），手套不参与；当前没有配套头盔/鞋靴，因此不写不生效的套装。
- 旧存档：`ColdSteelProfileRuntime` 对 `defense`/`bonusStats` 做目录权威同步；本轮另加一次性清理——这两件实例里若残留早期 `bonusStats` 会挡住覆盖层，清掉后按 `source-combat-items` 读取。

## 权威表里的防御曲线（取值依据）

同一张表里的套装胸甲（`*_armor`）：法袍 7/+1、蚀月 9/+1.5、轻甲 10/+2、苍月 12/+2、流云 13/+2.5、神谕法袍 15/+2.6、星穹 17/+3.5、神域／圣辉 20/+4.2、壁垒 34/+3、镇岳 43/+4、天罡 54/+5。手套：皮手套 2/+0.5、黑色皮手套 4/+1、钢护手 20/+0。items.json 侧的旧值（针织 6、炭灰 4、锁子甲 60、钢护手 16）是更早的薄子集。

换算减伤：防御 4≈6.3%、6≈9.1%、8≈11.8%、12≈16.7%、16≈21.1%、18≈23.1%、32≈34.8%、60=50%（再叠加角色基础防御）。

## 本次设定

| 装备 | 防御（items.json） | +10 强化 | 效果（source-combat-items） | 定位 |
| --- | --- | --- | --- | --- |
| 硬壳战术手套 `ue_hardknuckle_gloves` | **8 / 每级 +1** | 18 | `reloadSpeed +0.05` 换弹 +5%；`adsPercent -0.05` 开镜耗时 −5% | 护指 + 快速出枪：介于黑色皮手套 4/+1 与钢护手 20/+0 之间的硬化皮革档 |
| ST6 战术上衣 `ue_st6_sleeves` | **12 / 每级 +2** | 32 | `reloadSpeed +0.05` 换弹 +5%；`sprintStaminaCost -0.1` 奔跑体力 −10% | 战术织物中甲：对齐苍月 12/+2 档，低于流云 13/+2.5 与重甲线 |

理由：

- 硬壳手套走“快速出枪”而不是再复制一份原版厚皮手套的 +10% 攻速；防御放在黑色皮手套与钢护手之间，靠 +1/级强化成长。
- ST6 对齐权威表的苍月轻甲档（12/+2），比素布上衣有意义、又明显低于壁垒 34/+3 起的重甲，且不带移速/攻速惩罚。
- 三条效果都选真实消费键：`reloadSpeed`→枪械换弹倍率；`adsPercent`→既有开镜耗时；`sprintStaminaCost`→奔跑消耗倍率。

## 浮窗呈现

- 简略浮窗：`Metrics` 对所有装备输出「防御力」+ `bonusStats` 字段（最多 4 行）。
  - 硬壳手套：防御力 / 换弹速度 / ADS 瞄准时间
  - ST6：防御力 / 换弹速度 / 奔跑体力消耗
- 详细浮窗：物品信息 → **防御参数**（防御力含强化、防御基础、每级强化防御）→ **属性加成**（换弹 +5%、开镜耗时 −5% / 换弹 +5%、奔跑体力 −10%）；两个新键按“越低越好”着色。
- 武器浮窗（枪械与弓）的「开镜耗时」行已乘装备倍率，与手套显示一致。

## 后续装备数值模板

1. `defense` 写在 items.json（与既有 `ue_*` 装备一致）；`perEnhance` 小件 1、胸甲类 2；强化上限 10。
2. 战斗/手感 `bonusStats` 写在 `source-combat-items.json` 对应 ID 下，键只从上文真实键里选，1–2 条为宜，百分比用小数，负值表示“更快/更省”。
3. 套装：先备齐头盔+铠甲+鞋靴三件同 `armorSet` ID，再到 `SetEffect` 注册该 ID 的效果。
4. 不要用 `defense.damageReduction` / `defense.staminaCost` 表达普通护甲效果；盾牌的这些字段另有消费端。
5. 描述 `desc` 只写外观与用法，不重复数值。

## 状态

- 目录：`items.json` 两件装备的 `defense`；`source-combat-items.json` 两件装备的 `bonusStats`。
- 代码：`UColdSteelStatusModel::ADSTimeMultiplier()`（`ColdSteelStatusModel.h/.cpp`）、枪械 `ADSInDuration`（`FPSGAMECharacterProfile.cpp`）、弓 `AimIn/AimOut`（`BowWeaponComponent.cpp`）、奔跑消耗（`FPSStaminaModel.cpp`）、旧键清理（`ColdSteelProfileRuntime.cpp`）、浮窗键表与武器开镜耗时（`ColdSteelItemTooltipData.cpp`、`ColdSteelItemTooltipSummary.cpp`）。
- 构建：Game `FPSGAME.exe` 11:45:43、Editor `UnrealEditor-FPSGAME.dll` 11:54:22；七个改动对象（ColdSteelStatusModel、FPSGAMECharacterProfile、FPSStaminaModel、BowWeaponComponent、ColdSteelItemTooltipData、ColdSteelItemTooltipSummary、ColdSteelProfileRuntime）obj 时间均晚于源文件。
- 默认未运行游戏/PIE/截图，由用户体验验收。