# 灰钢锁子甲五件套：防御与效果（2026-10-19）

用户要求：下一步构建重甲锁子甲五件套，按现用装备基准设计强化后的数值，并列出五件当前属性。

2026-10-19 追加：按用户逐件效果重订——最大生命改为百分比、加入暴击抵抗/眩晕抵抗/近战武器物理攻击，并补施法速度惩罚；防御与强化值不变。

## 五件与结论

| 部件 | 物品 ID | 防御（items.json） | +10 强化 | 部件效果（source-combat-items） |
| --- | --- | --- | --- | --- |
| 灰钢闭面盔 | `ue_steel_armet` | **24 / 每级 +2** | 44 | `maxHpPercent +0.05` 最大生命 +5%；`critRes +10` 暴击抵抗 +10%；`castSpeedPercent -0.05` 施法速度 −5% |
| 灰钢锁子甲 | `ue_chainmail_shirt` | **34 / 每级 +3** | 64 | `maxHpPercent +0.10` 最大生命 +10%；`critRes +15` 暴击抵抗 +15%；`moveSpeedPercent -0.05`；`meleeAttackSpeed -0.05` |
| 灰钢锁子甲裤 | `ue_chainmail_pants` | **20 / 每级 +2** | 40 | `maxHpPercent +0.05` 最大生命 +5%；`stunResist +25` 眩晕抵抗 +25%；`moveSpeedPercent -0.05` |
| 灰钢铠甲靴 | `ue_armored_boots` | **12 / 每级 +2** | 32 | `stunResist +25` 眩晕抵抗 +25%；`moveSpeedPercent -0.05` |
| 钢甲护手 | `ue_steel_gauntlets` | **8 / 每级 +1** | 18 | `meleeDamagePercent +0.05` 近战武器物理攻击 +5%；`reloadSpeed -0.10`；`bowDrawSpeed -0.10`；`castSpeedPercent -0.05` |

- 五件基础防御合计 **98**；全部 +10 后合计 **198**。
- 五件套额外效果：**防御力 +15%**。`Derived("def")` 的 `(角色基础防御 + 装备防御)` 整体乘 1.15；+10 全套时仅装备部分 198 × 1.15 ≈ **227.7**，随后再乘金刚符文/冰甲等既有倍率。
- 五件套同时提供 **最大生命 +20%**（头 5% + 甲 10% + 裤 5%）、**暴击抵抗 +25%**（头 10 + 甲 15）、**眩晕抵抗 +50%**（裤子 25 + 靴子 25）、**近战武器物理攻击 +5%**；代价是移动速度 **−15%**、近战攻击速度 **−5%**、施法速度 **−10%**、换弹速度 **−10%**、拉弓速度 **−10%**。
- 只穿头盔/铠甲/靴子时，`ArmorSet()` 能识别三件同套，但 **+15% 防御不会生效**；必须同时穿裤子和手套。

## 改前现状（用户要求的“现在这五件”）

| 部件 | 目录防御 | 强化 | 现有属性 |
| --- | --- | --- | --- |
| 灰钢闭面盔 | 24 | 无 `perEnhance`，+10 仍 24 | 无额外效果 |
| 灰钢锁子甲 | 60 | 无 `perEnhance`，+10 仍 60 | 移速 −5%；近战攻击速度 −5% |
| 灰钢锁子甲裤 | 40 | 无 `perEnhance`，+10 仍 40 | 移速 −5% |
| 灰钢铠甲靴 | 24 | 无 `perEnhance`，+10 仍 24 | 移速 −5% |
| 钢甲护手 | 16 | 无 `perEnhance`，+10 仍 16 | 换弹 −10%；拉弓 −10% |

- 改前五件基础防御合计 **164**，但强化不成长；这是旧值薄子集，不符合“强化后数值”的要求。
- 旧 `source-combat-items.json` 的钢甲护手还带一条 `defense.base=20 / perEnhance=0` 覆盖；实例已有目录 `defense` 时不生效，本轮一并同步为 **8/+1**，避免两套数值并存。

## 取值依据

- 防御结算：`UColdSteelEnhancementSystem::Defense` = `floor(base + perEnhance × enhanceLevel)`，护甲强化上限 10。
- 对照权威表胸甲档：壁垒 **34/+3**（+10 为 64）、镇岳 43/+4（83）、天罡 54/+5（104）。本套是基础灰钢重甲，胸甲取 **34/+3**，与壁垒同档，低于镇岳/天罡。
- 头盔取 **24/+2**（+10 为 44），对齐壁垒重盔；靴子取 **12/+2**（32），对齐壁垒重靴的轻量化下修；裤子和手套按同一重甲比例补足 **20/+2**、**8/+1**。
- 五件 +10 合计 198，高于蓝魔法师五件套 75 和 ST6 战术套（约 68），低于天罡等顶级重甲整包；符合“占满五个防具槽、用移速/攻速/换弹换防御”的重甲定位。
- 减伤参考：装备防御 198 时约 76.7%；触发五件套 +15% 后约 227.7，约 79.1%；再叠加角色基础防御与符文。仍保留伤害下限 10%。

## 效果接入

- `maxHpPercent`（新装备键）：`ResourceMaximum()` 先算 `100 + 体质×10 + (等级-1)×10`，再乘 `1 + EquipmentBonusFor(State,"maxHpPercent")`；三件 5% + 10% + 5% 按加法合计 **+20%**。平铺 `maxHp` 仍保留在百分比之后相加，兼容既有装备。
- `critRes`（既有角色词条，新增装备接入）：`Derived("critRes")` 返回 `S.CritRes + 装备暴击抵抗`；装备值按加法叠加，角色面板直接显示总值。随机暴击已有 `CoreCombatFormula::CriticalChance(Chance,Resistance)=max(0,Chance-Resistance)`；本轮把玩家目标也纳入 `CombatFormulaRuntime::MonsterCriticalResistance()`，并按目标身份选择本地档案或远端影子档案。需要注意：武器命中的随机暴击在 `UColdSteelStatusModel::ApplySkillWeaponHit()` 里仍以 `UMonsterCombatComponent` 非空为前提，玩家目标该组件为空，所以 PvP 武器随机暴击目前实际不掷；法术路径没有这个门槛。当前怪物攻击也没有暴击判定，因此这条属性在现有 PvE 中主要体现在角色面板，在 PvP 法术/后续接入中才会实际扣减暴击率。
- `stunResist`（新装备键）：`UCombatStatusFormula::AddStun()` 在玩家、服务器权威侧读取 `EquipmentBonus("stunResist")`，按 `0–100%` 概率免控；25% 抵抗面对 100% 必晕攻击时有 75% 概率仍被眩晕。多次获得按加法叠加，例如裤子 25% + 靴子 25% = 50%，面对 100% 必晕攻击时实际眩晕概率为 50%。
- `meleeDamagePercent`（新装备键）：`UColdSteelEnhancementSystem::ProcessedDamage()` 对 `category=="weapon_melee"` 的武器在最终物理伤害上乘 `1 + EquipmentBonus("meleeDamagePercent")`；只作用于近战武器物理伤害，不加枪械/弓/法术。
- `moveSpeedPercent`：`CombatMoveMultiplier()` 乘 `max(0, 1 + EquipmentBonus("moveSpeedPercent"))`；三件各 −5%，合计 −15%。
- `meleeAttackSpeed`：`Derived("aspd")` 乘 `1 + EquipmentBonus("meleeAttackSpeed")`；胸甲 −5%。
- `castSpeedPercent`：`ApplySpellbookFocus()` 乘 `1 + EquipmentBonus("castSpeedPercent")`；头盔和护手各 −5%，合计 −10%。
- `reloadSpeed` / `bowDrawSpeed`：分别接枪械换弹与弓拉弓倍率；护手各 −10%。
- 五件套防御：`UColdSteelStatusModel::SteelChainmailSetComplete()` 先要求 `ArmorSet()=="steel_chainmail"`（头盔 1 + 铠甲 7 + 靴子 13），再检查手套 3、裤子 15 同套；`SetEffect("defense")` 返回 0.15，`AdjustCombatStat("def")` 乘入。

## 数据落点

- `Content/ColdSteelData/items.json`：五件 `defense`。
- `Content/ColdSteelData/source-combat-items.json`：五件 `armorSet: "steel_chainmail"`、`setBonusDesc: "五件套：防御力 +15%"`、部件 `bonusStats`；旧 `items.json` 里的 `bonusStats` 已移除，避免挡住覆盖层。
- `Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp`：五个 ID 加入旧实例 `bonusStats` 清理名单，旧存档读取覆盖层。
- `Source/FPSGAME/UI/ColdSteelStatusModel.cpp`：`ResourceMaximum()` 接入 `maxHpPercent`；`Derived("critRes")` 加入装备抗暴。
- `Source/FPSGAME/UI/ColdSteelEnhancementSystem.cpp`：`ProcessedDamage()` 接入 `meleeDamagePercent`。
- `Source/FPSGAME/Combat/CombatStatusFormula.cpp`：`AddStun()` 接入 `stunResist`；服务器侧通过 `ColdSteelAuthority::ForPawn()` 取目标自己的模型，远端玩家读 `PlayerState` 的 `ShadowModel`。
- `Source/FPSGAME/Combat/CombatFormulaRuntime.cpp`：玩家目标的暴击抵抗走角色 `critRes`；同样通过 `ForPawn()` 区分本地玩家与远端影子档案。
- `Source/FPSGAME/UI/ColdSteelItemTooltipData.cpp` / `ColdSteelItemTooltipSummary.cpp`：新增四个键的中文名、百分比格式与增益/减益符号。
- 浮窗：防御、最大生命%、暴击抵抗、眩晕抵抗、近战物理攻击显示为增益（金）；移速/近战攻速/施法速度/换弹/拉弓显示为减益（黑）。`critRes`/`stunResist` 按百分点显示（+10%/+25%），`maxHpPercent`/`meleeDamagePercent` 按小数换算成 +5%/+10%。增益块与减益块之间现在只有一条 1px 中性暗线，标题颜色区分，不再在标题下重复画线；规则见 [装备浮窗增益/减益规则](../UI/equipment-tooltip-buff-debuff-summary-20261019.md)。五件套说明走现有 `armorSet`/`setBonusDesc` 详细卡展示。

## 联机审计

- **属性读取**：所有效果都走 `EquipmentBonusFor(State,Key)` 对已装备物品 `bonusStats` 求和；`source-combat-items.json` 是唯一数据源。远程玩家在服务器侧用 `PlayerState::ShadowModel`，本地/主机用本地 `UColdSteelStatusModel`，主机不再把自己的装备误用到访客身上。
- **最大生命%**：`ColdSteelPlayerState::ApplyGuestProfile()` 用访客影子档案调用 `ResourceMaximum(Adopted,false)`，`AFPSGAMECharacter::ApplyColdSteelProfile()` 把结果写入 `FPSCombatHealthComponent::MaxHealth`；换装时保留已损失的生命差值。
- **暴击抵抗**：玩家作为目标时，`CombatFormulaRuntime::MonsterCriticalResistance()` 先取目标自己的档案（远端读影子档案），再走 `max(0, 攻击暴击 − 暴击抵抗)`；玩家攻击怪物仍读怪物常量表。
- **眩晕抵抗**：`UCombatStatusFormula::AddStun()` 只在服务器权威侧掷一次 0–100 概率；目标为远端玩家时读其影子装备。客户端可能先看到本地表现，最终以服务器复制状态为准。
- **近战物理攻击%**：服务器近战结算使用角色/影子档案的 `ProcessedDamage()`，访客的攻击吃到的是访客自己的护手，不是主机的。
- **浮窗**：物品数据读取与角色无关，本地悬停使用本地档案；新增四个键在缩略摘要和详细参数都有中文名与百分比格式，联机不会改变显示值。
- **已知边界**：当前怪物攻击没有暴击判定，所以暴击抵抗在现有 PvE 中主要显示为面板值；要让怪物暴击真正吃抗暴，需要另补怪物暴击率/暴伤。PvP 武器随机暴击还被 `ApplySkillWeaponHit()` 的 `UMonsterCombatComponent` 非空门槛挡住（玩家目标没有该组件），本次只修了抗暴的档案选择，没有擅自改这个玩法门槛；法术路径可实际使用抗暴。部分直接写 `PlayerGuardBreakComponent::Apply()` 的强制硬直路径不经过 `AddStun()`，也不吃眩晕抵抗；本套的常规眩晕入口已覆盖。

## 状态

- 数据与代码已落盘。
- 编译：`SourceAssets/BluntMasteryDamage20261019/FPSGAME-build-3.log` 的 `FPSGAME` 构建 **Result: Succeeded**（2026-10-19 23:19，531.94 秒）。本套涉及的 TU 均通过：[38] `ColdSteelCharacterSheet.cpp`、[49] `ColdSteelEnhancementSystem.cpp`、[88] `ColdSteelItemTooltipSummary.cpp`、[90] `ColdSteelItemTooltipData.cpp`、[126] `ColdSteelStatusModel.cpp`、[147] `CombatFormulaRuntime.cpp`、[148] `CombatStatusFormula.cpp`。
- Editor 目标：最近一次 `SourceAssets/SVCHReplacement20261018/QuickMeleeHandR3_20261019/build-editor.log` 中本套 `ColdSteelItemTooltipLayout.cpp` [22]、`CombatFormulaRuntime.cpp` [44]、`CombatStatusFormula.cpp` [46] 通过；其余本套 TU 在上一轮 Editor 构建通过。整次构建 **Result: Failed (OtherCompilationError)**，错误属于工作区其他未完成文件：`ColdSteelProfileTransfer.cpp(81)` 的 `else if` 和 `TransitLoadingSubsystem.cpp(924)` 的 `[[nodiscard]]`，因此 Editor DLL 未链接。未改动这些文件。
- 2026-10-19 追加：灰钢锁子甲裤补 `stunResist +25`，本套眩晕抵抗合计 **+50%**，复用已接入的 `AddStun()` 抗晕逻辑。
- 2026-10-19 联机审计修复：`AddStun()` 与 `MonsterCriticalResistance()` 不再一律读主机本地档案；服务器上远端玩家改读 `PlayerState::ShadowModel`，主机/单机才回退本地模型。`ColdSteelItemTooltipLayout.cpp` 同时改为两块之间一条 1px 中性暗线。
- 本会话未启动编辑器、PIE 或截图；实际强化数值、套装触发、抗暴/抗晕概率与浮窗由用户验收。