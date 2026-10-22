# 暴击相关术语：倍率、伤害加成与点数

适用：新增暴击类词条（装备、套装、技能），或编写/修改相关浮窗行名。FPSGAME 里“暴击倍率”“暴击伤害加成”“暴击率”是三个不同口径，混用会被玩家读成完全不同的收益。

来源：2026-10-22 野行套词条口径统一的定案。用户确认后再落地，未做游戏内视觉验收。

## 三个口径

| 术语 | 含义 | 数值形态 | 显示 |
| --- | --- | --- | --- |
| 暴击倍率 | 最终乘数 `1 + 总暴伤` | 无（派生值） | `1.80x` |
| 暴击伤害 / 暴击伤害加成 | 进入 `1 + X` 的**加数** | 比例 `0.25` | `+25%` |
| 暴击率 | 触发概率 | 点值 `10` 或百分比 | `+10%` |

只有整体那一个数是“倍率”，带 `x`；所有加数都叫“暴击伤害”，带 `+%`。

## 代码侧对应

- 倍率：角色面板 `critMultiplier` 行，值 `1+CriticalStrikeEffect().CriticalDamageBonus`，显示 `%.2fx`。
- 暴击伤害：`bonusStats.critDamageBonus`、套装 `SetEffect("critDamage")`，两者相加进 `CriticalDamageBonus`。
- 暴击率：`bonusStats.crit`（点值，10 = 10 点）与 `SetEffect("crit")`（同样返回点值），进 `AdjustCombatStat("crit")`。

`critDamageBonus` 是**加数**不是倍率：写 `0.25` 表示把 1.55x 变成 1.80x，而不是变成 1.55×0.25。

## 统一口径为「暴击伤害 +N%」

2026-10-22 用户确认：目录 `setBonusDesc`、物品浮窗行名、文档三处一律写「暴击伤害 +25%」，不再写「暴击倍率 +0.25」。

理由：

1. `0.25` 描述的是加数，不是结果；
2. 武器浮窗对同类效果（弓 +50%、狙击 +100%）一直写作“暴击伤害加成 +N%”，装备沿用同一词表；
3. “倍率 +0.25”容易被读成“乘 0.25”，语义偏离。

角色面板那一行仍叫“暴击倍率”，因为它显示的是 `1.80x` 这个整体结果——这是正确用法，不要一起改掉。

## 浮窗实现位置

- 属性加成表：`ColdSteelItemTooltipData.cpp` 的 `Names` 映射与 `Percent` 判定，`critDamageBonus` 需同时进这两处，否则要么不显示、要么显示成 `0.25%`。
- 套装加成表：`ColdSteelItemTooltipSummary.cpp` 的 `SetBonusList()`，`{critDamage, 暴击伤害, 25., true}`，数值按百分数写（25 而非 0.25）。
- 这两张表的口径必须与 `SetEffect()` 实际返回值一致：`SetEffect("critDamage")` 返回 `0.25`，表里写 `25`（因为 `bPercent=true` 会加 `%`）。

## 坑

- `crit` 在 `bonusStats` 里是点值，写 `0.10` 会被显示成 `+0%（不足 1 点）`，几乎无收益。要 +10% 就写 `10`。
- `critRes`、`stunResist` 同样是点值；`moveSpeedPercent`、`reloadSpeed`、`bowDrawSpeed`、`castSpeedPercent` 是比例（`0.05` = 5%）。同一张表里两种形态共存，加新键时必须确认它属于哪类。
- 改词条前先搜全项目既有用法，不要只改一处，否则浮窗、套装描述、文档会互相矛盾。
