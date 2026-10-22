# 装备浮窗的套装进度段（2026-10-22）

缩略浮窗在核心数值下方加一段套装信息：先报件数，再列凑齐后生效的属性。与
[增益/减益分组](equipment-tooltip-tone.md) 同一套配色，不新造主题值。

## 版式

| 元素 | 取值 |
| --- | --- |
| 与上方数值 | 一条 1px 中性暗线（`AddRule(Body,10,8,false,true)`） |
| 套装名 | 14px 加粗 `ItemTooltipGold`，占 62% |
| 件数 `（4/5）` | 14px 等宽数字右对齐占 38% |
| 属性名 | 13px，占 46% |
| 属性数值 | 14px 等宽数字右对齐占 54% |
| 凑齐时 | 名、件数、属性全用 `ItemTooltipGold` |
| 未凑齐 | 件数与属性降为 `ItemTooltipSecondary`，套装名仍金色 |

凑齐与否**只靠颜色**区分，不加图标、背景块或第二套配色。未凑齐也照列属性，让玩家判断差的那件值不值得换。

## 三条必须记住的坑

1. **分组摘要会提前 `return`**。护甲恰好走「增益/减益分组」那一路，`AddSetBlock` 必须放在那条 `return` **之前**，否则套装块在护甲上永远不出现——功能等于全废。这一处一旦写错没有任何编译期提示。
2. **套装行不要登记进 `RowViews`**。`UpdateRows()` 会用 `RowData(View)` 按 `Card`/`Row` 索引回查 `Presentation.Summary`；套装数据不在那张表里，登记进去会越界。套装行内容本身是静态的。
3. **耗时/消耗类属性必须显示负号**。「ADS 瞄准时间 +10%」「奔跑体力消耗 +15%」会被读成更慢更费，语义正好相反。给加成表加一个 `bLowerValue` 标记，这类行输出 `-`，其余输出 `+`。

## 件数不要写死

- **总件数**：遍历目录里声明同一 `armorSet` 的定义数，不在代码里写 5。将来加第六件或新套装不用改 C++。
- **已装备件数**：只数真正穿在护甲五槽（1 头盔 / 3 手套 / 7 铠甲 / 13 鞋靴 / 15 裤子）上的同套部件，背包里的不算。
- 总件数按套装名缓存（进程级 `static TMap`）。目录在运行期只写入一次，缓存安全；但**目录未加载时不要把 0 写进缓存**，否则之后一直报 `0/5`。
- `Total <= 0` 时直接不渲染整段。少数调用点允许传 `nullptr` 模型，那时无目录可数，显示「（0/0）」是假进度。

## 与「详细参数」的重复

主卡里原有的「套装效果」段读的是目录 `setBonusDesc` 原文，和摘要的套装块讲同一件事。**摘要已渲染套装块时，主卡那段要跳过**，否则 F1 详情里同一套效果出现两遍。

注意执行顺序：主卡构建**早于** `CompleteColdSteelTooltipSummary`，此时 `Content.bHasSet` 还没赋值。所以要在主卡阶段就先算一次套装信息写进 `Content`，摘要直接复用——顺带把「数五槽」这件事从两遍减为一遍。

## 数据与联机

- 套装字段 `armorSet` / `setBonusDesc` / 单件 `bonusStats` 写在 `Content/ColdSteelData/source-combat-items.json` 覆盖层；`CombatItemFormula::ReadOnly` 按 Definition 名补进物品，不需要另开文件。
- **覆盖层写了 `bonusStats` 的装备，必须同时登记到 `ColdSteelProfileRuntime.cpp` 的 `bSourceCombatStats` 清单**。该清单负责清掉实例里残留的 `bonusStats`——`Read` 只在实例缺这个字段时才补覆盖层，实例有值就会盖住。漏登记的症状是「全新存档正常，老存档和联机远端玩家不生效」。
- 远端玩家的套装判定走 `CreateShadowModel` 建出的影子档：它复制了 `Definitions`，`ArmorSet()`/`SetEffect()` 读各自模型的 `Equipped()`，不依赖本机单例，所以能正确算出套装。`ReadOnly` 的缓存 key 只用 `Definition + Data`，与模型实例无关，多个档之间不会串。
- 三个消费端（`Reload`、`ADSTimeMultiplier`、`SprintStaminaPerSecond`）都在各自 pawn 的模型上算，套装项与装备项按同一口径相加。

## 检查

- 护甲件悬停时**能看到**套装块（验证第 1 条坑）。
- 未凑齐与凑齐两种状态下颜色不同，件数与属性同时变色。
- 耗时类显示负号，收益类显示正号。
- F1 详情里套装效果只出现一次。
- 无模型调用点（如探险详情）不显示「（0/0）」。
- 老存档 + 联机远端玩家两条路径都要看；只看全新单人存档会漏掉 `bSourceCombatStats` 那类问题。
- 未做 PIE/截图时，交付中写明「视觉未验收」。
