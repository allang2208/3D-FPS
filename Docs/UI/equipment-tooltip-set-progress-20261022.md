# 装备缩略浮窗套装进度与属性 · 2026-10-22

用户要求：在装备缩略浮窗的数值下方加两段——1）套装显示，带已装备／总件数，例如「锁子甲套装（4/5）差一件凑齐触发」；2）再在下面列出凑齐后才生效的属性；按冷钢 UI 规则设计。

## 数据来源

套装不在 `items.json`，而在覆盖层 `Content/ColdSteelData/source-combat-items.json`：

| 套装 id | 显示名 | 件数 | 占槽位 |
| --- | --- | --- | --- |
| `ranger_field` | 野行套装 | 5 | 头盔 1／手套 3／铠甲 7／鞋靴 13／裤子 15 |
| `steel_chainmail` | 锁子甲套装 | 5 | 同上 |
| `blue_mage` | 法师套装 | 5 | 同上 |

读取路径：`CombatItemFormula::ReadOnly(Item)`（`CombatItemFormula.cpp:27-34`）把覆盖层字段并进物品数据，所以浮窗直接读 `armorSet` 即可，不需要另开一次文件。

## 计数口径

- **总件数**：不是写死的 5，而是遍历 `Model->ItemDefinitions()`（全部 241 条定义）统计声明了同一 `armorSet` 的定义数。将来加第六件或加新套装，无需改 C++。
- **已装备件数**：只数真正穿在 1/3/7/13/15 五个护甲槽上的同套部件，背包里的不计入。
- 结果按套装名缓存（`static TMap<FString,int32> TotalCache`）。目录在运行期不变，241 条全表扫描虽只需约 0.02 ms，但浮窗构建点多达十余处，按 [性能开发约束](../../skills/ue5-performance-packaging/references/fpsgame-development.md) 仍走有界缓存；目录未加载时不缓存 0，避免之后一直报「0/5」。

## 数值口径

浮窗列出的属性与 `ColdSteelFormulaBonuses.cpp::SetEffect()` 的实际结算逐项对应，不写引擎不结算的效果：

| 套装 | 浮窗行 | 结算位置 |
| --- | --- | --- |
| 野行 | 防御力 +5% | `SetEffect("defense")` |
| 野行 | 暴击率 +10% | `SetEffect("crit")`（点数） |
| 野行 | 暴击伤害 +25% | `SetEffect("critDamage")`（比例，进 `CriticalDamageBonus`） |
| 锁子甲 | 防御力 +15% | `SetEffect("defense")` |
| 法师 | 施法距离 +50% | `SetEffect("castRange")` |
| 法师 | 魔法攻击力 +10% | `SetEffect("magicAttack")` |

**统一口径为「暴击伤害 +N%」**：`critDamage` 0.25 进入 `CriticalDamageBonus`（额外伤害比例，见 `ColdSteelSkillModel.cpp:49`），武器浮窗同类效果也写作「暴击伤害加成」；只有 `1 + X` 的整体才叫「暴击倍率」。2026-10-22 经用户确认，目录 `setBonusDesc`、浮窗行名与文档三处统一为「暴击伤害 +25%」，不再使用「暴击倍率 +0.25」。

## 视觉（沿用第 2.23 条）

| 元素 | 取值 |
| --- | --- |
| 与上方数值的分隔 | 一条 1px 中性暗线（`ItemTooltipBorder`），上 10px／下 8px |
| 套装名 | 14px 加粗 `ItemTooltipGold`，左侧 62% |
| 件数 `（4/5）` | 14px 等宽数字，右对齐占 38%；**凑齐＝金色，未凑齐＝`ItemTooltipSecondary`** |
| 属性名 | 13px，左侧 46% |
| 属性数值 | 14px 等宽数字，右对齐 54% |
| 属性配色 | 凑齐＝`ItemTooltipGold`；未凑齐＝`ItemTooltipSecondary`（读起来是「还没生效」而非「已经给了」） |

没有引入新配色、没有背景色块、没有图标；凑齐与否只靠件数那一处颜色区分。未凑齐也照列属性，供玩家判断差的那件值不值得换。

## 代码

- `ColdSteelItemTooltipData.h`：新增 `FColdSteelTooltipSetInfo`（`Name`／`Equipped`／`Total`／`bComplete`／`Bonuses`），`FColdSteelTooltipContent` 增加 `Set` 与 `bHasSet`。
- `ColdSteelItemTooltipSummary.cpp`：新增 `SetBonusList()`（套装加成表，口径对齐 `SetEffect`）、`SetDisplayName()`、`BuildSetInfo()`；在 `CompleteColdSteelTooltipSummary()` 里 `Out.bHasSet=BuildSetInfo(...)`，位置在摘要数值之后、装备对比之前。
- `ColdSteelItemTooltipLayout.cpp`：新增 `AddSetBlock()`；在 `AddCoreGrid()` 的非分组路径末尾、以及**分组路径 `return` 之前**调用。
- `ColdSteelItemTooltip.cpp`：`StructureSignature()` 纳入套装名／件数／是否凑齐／属性条数，穿上或脱下套装时浮窗会重建，不会停在旧进度。
- `ColdSteelStatusModel.h`：新增只读 `ItemDefinitions()`（`Definitions` 原本是 private，且 `ItemCatalog()` 是开发面板的归纳视图，不适合统计件数）。
- `ColdSteelItemTooltip.h`：声明 `AddSetBlock(UVerticalBox*)`。

### 两处必须记住的实现约束

1. **分组摘要在 `AddCoreGrid` 里会提前 `return`**。护甲恰好是走分组的那一类（防御力／属性加成全部为修正项），如果把 `AddSetBlock` 只放在函数末尾，套装段在护甲上永远不出现——这是本次自查发现并修掉的缺陷。
2. **套装行不进 `RowViews`**。`UpdateRows()` 会用 `RowData(View)` 按 `Card`／`Row` 索引回查 `Presentation.Summary`，套装数据不在那张表里，登记进去会越界；这些行内容本身是静态的。

## 状态

- 2026-10-22 Editor 构建 `Result: Succeeded`，304 项动作，326 秒，日志 `Saved/BuildEditor/build-20261022-160134.log`；`ColdSteelItemTooltip.cpp`[71]、`ColdSteelItemTooltipSummary.cpp`[75]、`ColdSteelItemTooltipLayout.cpp`[76]、`ColdSteelItemTooltipData.cpp`[86] 均编入，`UnrealEditor-FPSGAME.dll` 16:06:59 重链。
- DLL 内已确认含「锁子甲套装／野行套装／法师套装／防御力／暴击伤害／施法距离」字面量。
- 数值与目录 `setBonusDesc`、`SetEffect()` 三方核对一致。
- **未启动编辑器、未进 PIE、未截图**。实际排版、颜色、凑齐／未凑齐的观感、悬停与详情两种模式下的表现均由用户验收。
