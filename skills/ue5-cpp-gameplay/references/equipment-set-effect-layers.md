# 装备套装效果的三层数据与结算口径

适用：给护甲加套装效果（逐件属性 + 集齐五件触发），或排查“数值写进去了但游戏里不生效”。FPSGAME 的护甲数值分散在三个地方，搞错层次就会出现“目录有值、实机为 0”，或“单件属性被当成套装效果”。

来源：2026-10-22 野行套（`ranger_field`）接入过程中的实测与代码走查。未做游戏内验证的部分在文末单列。

## 三个层次各自拥有什么

| 层 | 位置 | 拥有字段 | 谁读 |
| --- | --- | --- | --- |
| 目录基础值 | `Content/ColdSteelData/items.json` | `defense`（`base` / `perEnhance`）、`bonusStats`、价格、占格、图标 | 老存档迁移、物品浮窗数值区 |
| 覆盖层 | `Content/ColdSteelData/source-combat-items.json` | `armorSet`、`setBonusDesc`，以及某些件的 `defense` / `bonusStats` | `CombatItemFormula::Read()` 运行时合并 |
| 套装结算 | `ColdSteelFormulaBonuses.cpp::SetEffect()` | 硬编码的套装 id → 数值 | `AdjustCombatStat` 等消费者 |

`SetEffect()` 按套装 id 字符串分支（`blue_mage` / `steel_chainmail` / `ranger_field` / `st6_tactical`），**不读配置里的数值**。所以新增套装必须在 C++ 里加分支，光写 JSON 不会有任何效果。

## 覆盖层只补缺失字段，不覆盖

`CombatItemFormula::Read()` 的合并语义是“实例 Data 里没有的字段才从覆盖层补”：

```cpp
for(const auto& Pair:(*Source)->Values)if(!Data->HasField(Pair.Key))Data->SetField(Pair.Key,Pair.Value);
```

因此同一件装备的 `defense` 若同时写在 `items.json` 和覆盖层，**实际生效的是实例快照里的那个**，覆盖层那份被静默丢弃。判定顺序是：实例 Data → 覆盖层补齐 → `items.json` 只在创建实例时进入快照。

要让覆盖层真正权威，必须同时清掉实例里的同名字段（`ColdSteelProfileRuntime.cpp` 的 `bSourceCombatStats` 清理块），否则老存档会一直用旧快照。**两处数值保持一致是最省事的做法**：让 `items.json` 和覆盖层写同一个数，这样无论哪条路径生效结果都一样，不必依赖清理块。

## 套装识别只认三个槽位

`ArmorSet()` 只检查头盔(1)/上衣(7)/鞋(13) 三槽 `armorSet` 一致。五件套需要额外自己判断手套(3)和裤子(15)：

```cpp
if(ArmorSet()!=TEXT("ranger_field"))return false;
for(int32 Slot:{3,15}){const auto* I=Equipped(Slot);if(!I)return false;FString Id;...if(Id!=TEXT("ranger_field"))return false;}
return true;
```

护甲五槽固定是 1/3/7/13/15。`ArmorSet()` 返回非空只代表“三件套”，不能当成“五件齐全”。

## 单件属性 vs 套装效果要分清

同一个数值放哪一层，玩家感知完全不同：

- 放单件 `bonusStats`：戴上这一件就生效，浮窗在“属性加成”段显示。
- 放 `SetEffect()`：必须凑齐才生效，浮窗在“套装效果”段显示。

用户说“帽子提高 10% 暴击率”和“5 件套提高 10% 暴击率”是两件事。前者写 `bonusStats.crit`，后者写 `SetEffect("crit")`；两者可以叠加，帽子自带 + 套装额外是常见形态。

`crit` 在 `bonusStats` 里是**点值**（10 = +10 个百分点），在 `SetEffect("crit")` 里同样是点值（返回 10），进 `AdjustCombatStat("crit")` 后加算。

## 新增比例类套装词条的顺序

`SetEffect()` 的既有分支混用“比例”和“倍率”，新增时按目标语义选：

- 额外伤害比例（进 `CriticalDamageBonus`、`MagicDamageBonus`）：返回 `0.25`、`0.10` 这类小数。
- 乘算倍率（进 `Value*(1+X)`）：返回 `0.05`、`0.15`。
- 点值（暴击率）：返回 `10`。

`defense` 是乘算（`Value*(1+SetEffect("defense"))`），`crit` 是加算，`critDamage` 是进倍率加数。写反了不会报错，只会静默算错。

## 覆盖层与实例迁移的坑

`ColdSteelProfileRuntime.cpp` 的 `bSourceCombatStats` 是一张**显式白名单**：只有在名单里的定义，加载时才会删掉实例残留的 `bonusStats`，改用覆盖层。没进名单的装备，实例里若有旧 `bonusStats`，就会一直盖住覆盖层。

- 手套类（`ue_field_gloves`）的 `+换弹/+拉弓` 写在覆盖层，因此需要进名单，否则老存档拿不到。
- 帽子如把暴击写在 `items.json`，则**不要**进名单，否则清理会把单件暴击删掉。

改这份名单前先确认该装备的数值到底写在哪一层。

## 交付与核对

1. 发布脚本用字段级替换（如 `Tools/BrownLeatherSet/json_entries.py` 的 `replace` / `insert`），保留同文件里其他并行改动与 BOM。
2. `source-combat-items.json` 的 `setBonusDesc` 是玩家可见文案，术语要与浮窗、文档三处统一。
3. 核对实际生效值要**同时**读 `items.json` 和覆盖层，取覆盖层优先；只读一方会得到错误合计。
4. 未测试就写未测试：套装识别、叠加、联机同步都需要实机确认，构建成功不等于生效。
