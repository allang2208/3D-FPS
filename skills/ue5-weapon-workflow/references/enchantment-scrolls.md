# 附魔卷轴：数据、限制键与战斗接入

一次附魔卷轴开发 = **四处数据 + 一处限制键 + 一处战斗消费点 + 审计断言**。涡轮增压（前缀、机枪、射速爬升）
与汇聚（后缀、狙击步枪、整匣聚合）是 2026-09-29 的两个完整案例，数值、取舍与验证边界见
[附魔卷轴「涡轮增压」](../../../Docs/Combat/enchant-turbocharger-20260929.md) 与
[附魔卷轴「汇聚」](../../../Docs/Combat/enchant-convergence-20260929.md)；
汇聚的曳光三层表现见 [Gunplay 与 Niagara 验收](gunplay-vfx.md) 的「表现分层」一节。

## 数据落点（四处，缺一不可）

- `Content/ColdSteelData/enhancement.json`：`id` / `item` / `name` / `slot`（`prefix`|`suffix`）/ `restriction` / `dust` / `description` / `effects`。同槽位的词缀互斥（前缀：涡轮增压 vs 骷髅射手；后缀：汇聚 vs 狼蛛）。
- `Content/ColdSteelData/items.json`：卷轴物品本身（`category: consumable`、价格、堆叠 99、图标沿用现有卷轴外观，不必新做美术）。
- `Content/ColdSteelData/dungeon_loot.json`：按深度分档的掉落权重与数量区间。
- `Content/ColdSteelData/tooltip-reference.json`：提示栏占位，漏了就缺项。

## 限制键：先看目录里真正存在的字段

`CanEnchant` 按 `restriction` 分流：`weapon` / `firearm` 是通用口径，类别键要读对字段——
**狙击步枪在目录里只有 `weaponTypeTag`**（SVD 的 `weaponType` 仍是 `rifle`，读 `weaponType` 永远不匹配），
机枪读 `weaponType == "machineGun"`。新类别键要在 `Supports` / `CanEnchant` / `MaxLevel` 三处口径一致，
并在 `ColdSteelEnhancementAudit.cpp` 加"定义能加载 + 类别正例为真 + 同类不同类别为假"的断言。

## effects 的合并与消费

- 数值键在实例上**相加**合并，唯一例外是 `attackIntervalMul`（相乘）；非数值键直接覆盖（见 `ColdSteelEnhancementSystem` 的合流处）。同一键被多个词缀叠加时，语义必须可相加。
- 战斗侧**不要在开火循环里读 JSON**：在 `ApplyColdSteelProfile` 里解析成缓存参数（`ColdSteelCombat::TurboRamp` / `Convergence` → `TurboRampParams` / `ConvergenceParams`），开火时只做插值或系数计算（`EffectiveFireInterval()`、`FireShot()`）。
- 一次附魔的多个键同属一体：缺任意一项就视为未附魔，避免半套数据把行为改成未定义状态。
- 不写 `attackIntervalMul` 就不会污染静态面板：动态射速只在开火路径生效（代价是提示栏的静态"射击间隔"仍是目录值，要在提示里补实战两档读数）。
- **伤害类型沿用原枪械**：只需缩放伤害**标量**，伤害类型组成由 `Shot.DamagePanel` 的比例决定，缩放不改变类型。

## 必踩的坑

- **读附魔字段一律判空**。改造台的产品预览等物品没有 `_enchantEffects`，`EE` 为空；`EE->TryGetBoolField(...)` 直接解引用会崩在 `BuildColdSteelItemTooltip → RefreshProductPreview → NativeOnInitialized`。提示栏里只有被 `if(EE)` 包住的分支可以直接读，其余一律 `if(EE)` 再读。
- 命名空间内的前置声明会**遮蔽真实类型**：`namespace ColdSteelCombat { class UColdSteelEnhancementSystem; }` 会新建 `ColdSteelCombat::UColdSteelEnhancementSystem`；前置声明要写在命名空间外（本项目 `ColdSteelEnchantmentCombat.h` 的做法）。
- 射速爬升的期望值按积分算：`N(t) = (1/I)·ln(3/(3−2.5t/T))`（起 3 倍间隔、终 0.5 倍间隔时），不要拿两端点做平均。
- 提示栏、工作台预览、实战必须读同一份结果（枪匠的统一评估入口 + `WeaponStatEvaluation` 的伤害分解），不要各自换算。

## 交付与验证

- 编译证据：源 → obj → DLL 的时间戳链，加 DLL 内 UTF-16 宽串扫描新增的 CVar 与日志串。
- 表现类改动的"看不见"排查顺序：**先看诊断日志确认链路**（附魔是否生效 → 标记是否传到表现层），再调实时 CVar 定观感；不要凭观感直接改几何。
- 用户未要求时不主动测试、截图或跑 PIE；把"已编译未实测"写进交付说明与案例文档。