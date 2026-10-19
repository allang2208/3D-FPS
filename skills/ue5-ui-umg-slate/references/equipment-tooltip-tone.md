# 装备浮窗的增益/减益分组与细线（2026-10-19）

适用于装备缩略摘要（悬停主卡与固定卡顶部共用）。武器中性核心数值和详细参数不套用本规则。

## 规则

1. **结构**：标题 → 增益块 → 一条 1px 中性细线 → 减益块。没有增益或减益时省略对应块；只有增益时不画无意义的分隔线。
2. **颜色**：增益的分区标题、属性名、数值都用 `ColdSteelUI::ItemTooltipGold`（#756447，对 #EEF0F2 约 5.01:1）；减益三处都用 `ColdSteelUI::ItemTooltipText`（#252A2E，>12:1）。细线用 `ColdSteelUI::ItemTooltipBorder`。不新造颜色，不使用背景色块。
3. **一条线**：两块之间只画一条 1px 中性暗线（`AddRule(..., Dark=true)`），上 8px、下 6px；**不要**在每个标题下再重复画下划线。
4. **判定按语义**：移速、近战攻速、换弹、拉弓、施法速度正值为增益；魔法冷却、魔法消耗、ADS 时间、体力消耗负值为增益。不要用“数值是否大于 0”代替语义判断。
5. **数值**：左属性名、右数值，单行横排；带真实 `+/-` 符号；`crit`/`critRes`/`stunResist` 按百分点，`maxHpPercent`/`meleeDamagePercent`/速度类按小数乘 100。不截断为 4 行。
6. **范围**：仅当摘要的核心行全部是修正项（无中性核心行）时分组；武器仍有伤害/射速等中性核心，继续走原两列网格。分组摘要在详细参数里不再重复列一遍；详细参数与对比仍用 `ItemTooltipPositive/Negative` 绿/红语义。

## 实现锚点

- `Source/FPSGAME/UI/ColdSteelItemTooltipSummary.cpp`：`FMetric::Tone`，`Add(..., Tone)`，固定增益行（防御、装备魔攻）传 `1`，`bonusStats` 按 `Percent/PointPercent/LowerBetter` 计算 Tone；分组只输出 `bSection` + 增益/减益行。
- `Source/FPSGAME/UI/ColdSteelItemTooltipLayout.cpp`：`AddCoreGrid` 的 `bGrouped` 分支；`AddRule` 的 `Dark` 参数；`UpdateRows` 的 `bSummaryTone` 让标签与数值同色。
- `Source/FPSGAME/UI/ColdSteelItemTooltip.h`：`FRowView::bSummaryTone`、`AddRule(..., bool Dark)`。
- 数据字段与中文名：`ColdSteelItemTooltipSummary.cpp` 的 `Fields` 表、`ColdSteelItemTooltipData.cpp` 的 `Names` 表。

## 检查

- 装备五件套的缩略浮窗逐件看：增益在上、减益在下、中间恰好一条暗线，标题下没有第二条线。
- `maxHpPercent` 显示 `+5%` 而不是 `+500%`；`critRes`/`stunResist` 显示 `+25%` 而不是 `+2500%`；换弹/拉弓的负值显示为减益。
- 武器摘要仍为中性两列；详细参数仍为绿/红；两者不因本规则改语义。
- 颜色只用 `ColdSteelUIStyle` 已有 token；不引入新颜色或竖排文字。
- 未做 PIE/截图时，交付中写明“视觉未验收”。
