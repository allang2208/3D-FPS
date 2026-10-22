# 野行套：五件套数值与套装效果（2026-10-22）

用户指定当前装备栏的 **翎羽帽 + 新版野行上衣 + 棕皮裤 + 棕皮靴 + 露指手套** 为一整套。本轮要求：

- 上衣、手套：只保留 **换弹 +10%** 与 **拉弓 +10%**，剔除近战攻速、施法速度等其他效果。
- **帽子仍带自己的暴击**（暴击率 +10%、暴击伤害 +25%），这是单件属性。
- **额外的五件套效果**：暴击率 **+10%**、暴击伤害 **+25%**；与帽子叠加。
- 厚皮革手套留给后续套装，完全不动。

## 一、套装定义

- 套装 ID：`ranger_field`
- 套装描述：**野行套：轻甲五件，集齐五件额外获得防御 +5%、暴击率 +10%、暴击伤害 +25%。**
- 识别沿用现有 `ArmorSet()`（头/上衣/鞋三槽同套），再加手套、裤子同套，即必须 **五件齐全** 才触发套装效果。
- 帽子单戴或只凑三件时，仍只有帽子自身的暴击，没有套装部分。

## 二、逐件数值（实际生效）

| 部位 | 物品 ID | 防御（基础 / 每级强化） | +10 强化后 | 部件效果 |
| --- | --- | --- | --- | --- |
| 头部 | `ue_ranger_feather_hat` | **6 / +0.6** | 12 | `crit +10`（暴击率 +10%）、`critDamageBonus +0.25`（暴击伤害 +25%） |
| 上衣 | `ue_field_sweater` | **8 / +1.2** | 20 | `reloadSpeed +0.10`、`bowDrawSpeed +0.10` |
| 裤子 | `ue_leather_pants` | **20 / +1.6** | 36 | `moveSpeedPercent +0.05`（移动速度 +5%） |
| 鞋靴 | `ue_leather_boots` | **12 / +1.0** | 22 | `moveSpeedPercent +0.05`（移动速度 +5%） |
| 手套 | `ue_field_gloves` | **2 / +0.5** | 7 | `reloadSpeed +0.10`、`bowDrawSpeed +0.10` |

- 五件防御基础合计 **48**；全部 +10 合计 **97**，套装再 +5% → **101**（`floor` 后）。
- 价格合计 **188**，占格不变（2×2、3×3、2×3、2×3、2×2）。
- **覆盖层说明**：`ue_field_gloves` 的 `defense` 与 `bonusStats` 写在 `source-combat-items.json`；本次把 `items.json` 与覆盖层统一成 **2 / +0.5**，避免旧实例快照产生 4 与 2 的歧义。其余四件没有覆盖层，以 `items.json` 为准。

## 三、五件套效果（额外，与单件叠加）

| 效果 | 套装数值 | 实现 |
| --- | --- | --- |
| 防御 | **+5%** | `SetEffect("defense")` → `AdjustCombatStat("def")` 乘算 |
| 暴击率 | **+10%（点值 +10）** | `SetEffect("crit")` → `AdjustCombatStat("crit")` 加算 |
| 暴击伤害 | **+25%** | 新增 `SetEffect("critDamage")` → `CriticalStrikeEffect()` 加算 |

## 四、暴击的叠加结果（五件齐全时）

| 来源 | 暴击率 | 暴击伤害 |
| --- | --- | --- |
| 翎羽帽（单件） | +10% | +25% |
| 野行五件套（套装） | +10% | +25% |
| **合计** | **+20%** | **+50%**（面板倍率 = 1 + 技能暴伤 + 0.50） |

- 另有技能「暴击」按等级提供的暴击率与倍率、装备 `bonusStats.crit`/`critDamageBonus`、幸运与专精等，仍按各自原有规则叠加。

## 五、效果消费端

1. **暴击率（帽子 +10、套装 +10）**
   - 帽子：`bonusStats.crit = 10`，经 `EquipmentBonus("crit")`。
   - 套装：`SetEffect("crit")` 在 `RangerFieldSetComplete()` 为真时返回 10。
   - 两者都汇入 `Derived("crit")` → `AdjustCombatStat("crit")`，再计入近战专精暴击，按目标暴击抵抗结算。

2. **暴击伤害 +25%（帽子 +25%、套装 +25%）**
   - `CriticalStrikeEffect()` 现在把 `EquipmentBonus("critDamageBonus")` 与 `SetEffect("critDamage")` 一起加到技能的 `CriticalDamageBonus` 上。
   - 覆盖近战、枪械、火球/冰锥/闪电/圣光/暴风雪/火焰/雷电与符文球等所有读取该函数的路径。
   - 武器目录顶层 `critDamageBonus` 仍在武器射击分支单独相加，不重复。

3. **换弹 +10% × 2（上衣 + 手套）**：合计 **+20%**，消费端 `ColdSteelWeaponStats::Reload`。

4. **拉弓 +10% × 2（上衣 + 手套）**：合计 **+20%**，消费端 `ColdSteelWeaponStats::BowDrawSpeedBonus`，仅对弓生效。

5. **移动速度 +5% × 2（裤子 + 靴）**：合计 **+10%**，消费端 `CombatMoveMultiplier()`。

6. **已剔除的效果**：上衣的 `meleeAttackSpeed`、`castSpeedPercent`；手套原有的 `meleeAttackSpeed`（覆盖层同步改写）。

## 六、老存档迁移

- `ColdSteelProfileRuntime.cpp` 的 `bSourceCombatStats` 清理列表新增 **`ue_field_gloves`**：加载时删除实例里残留的旧 `bonusStats`（含旧的近战攻速），改按覆盖层读取，避免旧实例挡住新数值。
- **帽子不在清理名单**：它的暴击仍写在 `items.json`，清理会误删。
- 野行上衣同理不清理。
- 本次不修改任何玩家存档文件；迁移发生在加载时。

## 七、与已有套装对比

| 套装 | 五件防御基础 | +10 合计 | 主要收益 |
| --- | --- | --- | --- |
| 蓝法师套（布甲） | 28 | 75 | 施法距离 +50%、魔法攻击 +10% |
| 灰钢锁子甲（重甲） | 98 | 198 | 防御 +15% |
| **野行套（轻甲）** | **48** | **97** | 防御 +5%、暴击率 +10%、暴击伤害 +25%；另换弹/拉弓各 +20%、移速 +10% |

## 八、文件与状态

- 数值发布：`Tools/RangerFieldSet/publish.py`；备份 `SourceAssets/RangerFieldSet20261022/Before/`，回执 `SourceAssets/RangerFieldSet20261022/published.json`。
- C++：
  - `Source/FPSGAME/Combat/ColdSteelFormulaBonuses.cpp`：`RangerFieldSetComplete()`、`SetEffect("crit")`、`SetEffect("critDamage")`、`SetEffect("defense")`。
  - `Source/FPSGAME/UI/ColdSteelStatusModel.h`：`RangerFieldSetComplete()` 声明。
  - `Source/FPSGAME/Skills/ColdSteelSkillModel.cpp`：`CriticalStrikeEffect()` 叠加装备与套装的暴击伤害。
  - `Source/FPSGAME/UI/ColdSteelProfileRuntime.cpp`：手套旧实例 `bonusStats` 清理。
  - `Source/FPSGAME/UI/ColdSteelItemTooltipData.cpp`、`ColdSteelItemTooltipSummary.cpp`：属性表支持 `critDamageBonus`。
  - `Source/FPSGAME/UI/ColdSteelCharacterSheet.cpp`：暴击倍率行说明改为“技能与装备合计”。
- 未改模型、贴图、动画、`modular_outfits.json` 或存档。
- **未做游戏内验证**：套装暴击叠加、暴击伤害、换弹/拉弓、老存档迁移均待实机确认。
