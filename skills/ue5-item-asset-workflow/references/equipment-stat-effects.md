# 装备属性词条、套装与联机取值（2026-10-19）

适用于护甲、手套、鞋靴、裤装等非武器装备的数值设计、接入与排查。武器伤害公式另读 `ue5-weapon-workflow`。

## 1. 数据分层

- 装备定义在 `Content/ColdSteelData/items.json`：`id`、`name`、`category`、`equipSlot`、`defense`（`base` + `perEnhance`）、`armorSet` 等。运行时的 `Definitions` 只认这张表。
- 战斗/手感覆盖在 `Content/ColdSteelData/source-combat-items.json`：`CombatItemFormula::ReadOnly` 按 `weaponId` → `name` → `Item.Definition` 查找，给实例**缺失的顶层字段**补默认值。
- 覆盖表条目只有 key 等于现役定义 id、物品 `name` 或 `weaponId` 时才可达；不匹配的条目是死数据。改表前先用当前 `items.json` 的 id/name 做一次 key 匹配。
- 同一件装备的 `bonusStats` 只放在一个权威层。若已迁到覆盖表，`items.json` 里不要再留同名 `bonusStats`，否则会重复叠加。

## 2. 词条语义

| 键 | 存储 | 显示/消费 | 应用点 |
|---|---|---|---|
| `maxHpPercent` / `maxMpPercent` | 小数，`0.10` = +10% | 百分比 | `ResourceMaximum`：基础值 `× (1 + Σ)`，之后再加平铺 `maxHp`/`maxMp` |
| `critRes` | 百分点整数，`10` = +10% | 直接显示 `10%` | `Derived("critRes")`：角色基础抗暴 + `Round(EquipmentBonus)` |
| `stunResist` | 百分点整数，`25` = 25% | 直接显示 `25%` | 服务器权威 `AddStun` 掷 `0–100`，命中则免控 |
| `meleeDamagePercent` | 小数，`0.05` = +5% | 百分比 | `ProcessedDamage`；仅 `category == "weapon_melee"`，不缩放 Attack 项 |
| `moveSpeedPercent` | 小数 | 百分比 | `CombatMoveMultiplier`，低于 0 为减益 |
| `meleeAttackSpeed` | 小数 | 百分比 | `Derived("aspd")`；正值为更快 |
| `castSpeedPercent` | 小数 | 百分比 | `ApplySpellbookFocus` 等施法速度乘区 |
| `reloadSpeed` / `bowDrawSpeed` | 小数 | 百分比 | 换弹/拉弓耗时乘区；正值为更快 |
| `magicCooldownPercent` / `magicCostPercent` | 小数 | 百分比 | 负值为冷却/消耗降低，属于增益 |
| `adsPercent` | 小数 | 百分比 | 开镜时间乘区；负值为更快 |

- `crit`、`critRes`、`stunResist` 是**百分点**，不要再乘 100；其余百分比键是**小数**，显示时乘 100。
- “速度”类词条（移速、近战攻速、换弹、拉弓、施法）正值为增益；“冷却/消耗/瞄准时间”类词条负值为增益。不要只看数值正负。
- 最大生命用 `maxHpPercent` 而不是平铺 `maxHp`，这样百分比随等级与体质成长；平铺值保留给兼容旧装备。

## 3. 套装

- 部件在 `items.json`/覆盖表都写 `"armorSet": "<set id>"`，并用 `"setBonusDesc"` 描述五件套效果。
- `ArmorSet()` 目前用槽位 `{1 头, 7 铠甲, 13 鞋}` 识别三件同套；**套装加成必须五件齐全**（`ColdSteelStatusModel` 的五件判定还包含手套 3 与裤子 15）。
- 防御强化：`floor(base + perEnhance × enhanceLevel)`，护甲强化上限 10。基础防御和强化值改在 `items.json`；`bonusStats` 改在覆盖表。
- 五件套的防御百分比在 `Derived("def")` 对“角色基础 + 装备防御”整体乘；不要只乘装备部分。

## 4. 联机取值

- 本地玩家/主机：`UColdSteelStatusModel` 直接读当前档案。
- 服务器上的远端玩家：`ColdSteelAuthority::ForPawn(Pawn)` → `PlayerState::ShadowModel`。凡是按**目标**取装备派生属性（暴击抵抗、眩晕抵抗、减伤等），都先走这个入口。
- 只有 `Pawn->IsLocallyControlled()` 时才回退到 GameInstance 的本地模型；不要把“本地档案存在”当作远端玩家也有档案。
- 生命上限走 `ApplyGuestProfile` 的 `ResourceMaximum(Adopted,false)`，再用 `ApplyColdSteelProfile` 灌入服务端 pawn；近战伤害走 `ProcessedDamage(..., ShadowModel)`；移速/攻速/施法速度同样读影子档案。
- `PlayerState::ShadowModel` 是服务端权威副本；客户端表现只做展示，不以客户端档案作为伤害/免控依据。

## 5. 检查清单

1. `items.json` 与覆盖表都能被 JSON 解析；新 key 可达（id/name 匹配）。
2. 同一件装备只有一个 `bonusStats` 来源；五件套的每件都有 `armorSet` 和一致的 `setBonusDesc`。
3. 百分比键按“小数/百分点”分类检查，避免 5% 被写成 500% 或 0.05%。
4. `meleeDamagePercent` 只影响近战武器物理伤害；不要扩到枪械、弓、法术。
5. 联机路径按目标身份取模型；主机本地模型不得用于远端玩家。
6. 相关 C++ 文件编译通过；未跑 PIE 时在交付中明确“未测试”。

## 6. 已知边界（2026-10-19）

- 当前怪物攻击没有暴击判定，`critRes` 在 PvE 中主要是面板值；PvP 武器随机暴击还被 `ApplySkillWeaponHit()` 的 `UMonsterCombatComponent` 非空门槛挡住，法术路径可用抗暴。
- 部分直接写 `UPlayerGuardBreakComponent::Apply()` 的强制硬直不经过 `AddStun()`，不吃 `stunResist`；常规眩晕入口已覆盖。
- 蓝色法师与灰钢锁子甲的 `stunResist` 只按玩家、服务器权威侧掷；不要把该概率套到怪物或客户端表现层。
