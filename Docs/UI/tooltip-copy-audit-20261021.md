# 物品浮窗 / 缩略浮窗 / 改造栏说明一致性排查 · 2026-10-21

按用户要求，逐个核查物品浮窗（详细卡）、缩略浮窗（悬停摘要）与改造栏（枪匠／近战／法杖／弓／工具工作台）的说明是否满足既有标准，并修正不合规项。

## 判定依据

| 范围 | 标准文件 |
| --- | --- |
| 浮窗整体结构、字段名、单位、静态行抑制 | `Docs/ItemTooltipStandard20260928.md`、`skills/ue5-ui-umg-slate/references/weapon-tooltip-schema.md` |
| 改造栏能力卡／特效分工、只列直接属性 | `skills/ue5-weapon-workflow/references/attachment-detail-presentation.md` |
| 配件 stats／effects 措辞与可推导数字 | `skills/ue5-weapon-workflow/references/attachment-standard.md` |
| 缩略浮窗增益／减益分组 | `Docs/UI/equipment-tooltip-buff-debuff-summary-20261019.md` + 设计系统 2.23 |
| 消耗品浮窗行序 | `Docs/Items/consumable-tooltip-standard-20261018.md` |
| 武器 `desc` 与 `traits` | `skills/ue5-weapon-workflow/references/weapon-copy-and-traits.md` |
| 装备不显示稀有度 | AGENTS.md「物品稀有度规则」2026-10-09 |

## 一、缩略浮窗（悬停）

### 已修：祭品／材料的摘要只显示一半

`ColdSteelItemTooltipSummary.cpp` 对没有武器评估的物品（祭品、材料）回退到固定白名单
`恢复生命／恢复魔法／物理攻击／魔法攻击…` 取前四行。祭品的增益与代价都存在
`stats` 里且数值自带正负号，这套白名单只认名字不认符号，结果：

- 「铝矿石：移动速度 −1%、物理攻击 +4%」只显示 `物理攻击`，把移动速度整行丢掉；
- 反过来在「草编仓鼠窝」这类只有 ±修正的条目上，会只留半边、或把代价混进增益里。

改为按数值符号分「增益／减益」两块（与 2.23 条分组摘要一致），整行仍用目录原文，
不重算、不截断行数；没有符号数值的条目（地牢钥匙的「用途」等）保持原回退。

**2026-10-22 自查补正**：首版分组把「没有正负号」的行当成中性行直接跳过，但祭品里
这类行正是该物品独有的具名机制——金刚不坏、月影、点石成金、血藤寄生、狼烟结界、
原地复活、击杀回蓝／回血，共 10 件祭品会因此丢掉自己唯一的特效说明。现改为把中性行
排在增益块最前面（仍是原文），模拟核对后 0 行丢失。

### 已修：尼泊尔弯刀浮窗没有任何数值

`ue_kukri` 是 `weapon_melee` 里唯一的单手刀：不在剑类 `IsTwoHandedSword`、不在
`IsTwoHandedBlunt`，也不在 `IsEquippedProductionTool`，于是摘要与主卡全部落到兜底，
浮窗只剩一行「分类」。新增 `ColdSteelInventory::IsOneHandedMelee()`（按类别＋单双手＋
非剑非钝器判定，不写死 ID），补上武器总伤害／攻击间隔／体力消耗／最大攻击距离四项，
以及主卡的战斗参数段。没有实现的暴击、格挡、连段分段一律不造字段。

**2026-10-22 自查补正**：首版「最大攻击距离」取的是 `S.SlashReach`，但
`KukriWeaponComponent.cpp:283` 实际用 `Stats.BaseReach` 做命中范围，`SlashReach` 是
剑类专用的 `ScaledReach(BaseReach)×2`。会把距离报成两倍，等于凭空翻倍。
摘要与主卡两处都已改为 `BaseReach`。（当时 `melee_reach_cm` 为 150，2026-10-22 已上调到 220；
本条按 `BaseReach` 取值的结论不变。）

### 已修：分类与槽位英文键

`Category()` 缺 `ammo`、`currency`，`EquipSlotLabel()` 缺 `helmet`。命中时会把
内部标识原样显示在「分类」行。补齐为 `弹药／货币／头部槽`。

## 二、改造栏

跑 `Tools/Weapons/check_attachment_consistency.py`，基线 39 项问题，逐条处理后余 4 项
（见文末「保留项」）。

| # | 位置 | 问题 | 处理 |
| --- | --- | --- | --- |
| 1 | `ue_lmg201` 原厂弹匣 | description 写「30 发」，与 `base.mag_size=40` 冲突 | 改为不写数字的原厂描述 |
| 2 | `m870_lightweight_trigger_kit` | 「后坐力减少」「枪械稳定性提升」为禁用同义词 | `后坐力降低`／`枪械稳定性提高` |
| 3 | 两把霰弹枪 `shotgun_duckbill` | 「腰射散布」与全目录「腰射随机散布」不一致 | 统一为「腰射随机散布减少25%」 |
| 4 | `saiga12k_bump_stock` | 「射速提升25%」不是规范动词；「腰射随机扩散」用词漂移 | `射击间隔减少20%`／`腰射随机散布减少25%`（数值不变） |
| 5 | `saiga12k_ext12`／`saiga12k_drum20` | 换弹／装填行写了时长百分比，标准要求定性 | 「装填耗时更长」 |
| 6 | `saiga12k_drum20` | 名称「12k 大弹鼓」用内部缩写 | 「大弹鼓」 |
| 7 | `ue_m870`／`ue_saiga12k` | `traits` 完全缺「可改造槽位清单」行 | 按运行时实际槽集补行 |
| 8 | `ue_svch` | 清单漏 `tactical_secondary`，且写「战术挂件（战术挂件二）」 | 重写为 `战术挂件Ⅰ、战术挂件Ⅱ` |
| 9 | 手枪五把 | 清单把 `reargrip` 写成「后握把」，实际 UI 名是「握把防滑纹」 | 按 `CategoryLabel` 规则区分 |
| 10 | 近战 `破锋燕翎`／`腾云游龙` | 特效段保留「第三段伤害 +40%／+30%」派生值 | 删除该行及对应「收尾伤害」段，连段形态变化保留 |
| 11 | 近战 `速握轻柄` | 能力卡列第二段／第三段伤害（派生值） | 删除两条，`stats` 不动 |
| 12 | 近战 `金色符文强化` | description 手写可推导的 0.5 秒时长 | 改为机制描述，不给数字 |

槽位清单行由脚本按 `options ∪ allowed ∪ common_options` 生成，并复刻
`UGunsmithSystem::CategoryLabel` 的两条特例（有 `tactical_secondary` 时 `tactical` 显示
「战术挂件Ⅰ」；`PistolGripSurface::Supports` 为真的手枪 `reargrip` 显示「握把防滑纹」）。

## 三、物品数据

- `ue_hardknuckle_gloves` 类型写「护甲」，同为手套槽的其余五件都是「手套」→ 改「手套」。
- `ue_jeans`／`ue_cargo_pants` 类型写「裤子」，其余裤装都是「裤装」→ 改「裤装」。

## 四、核查通过、未改动的部分

- **消耗品**：16 件全部符合 `consumable-tooltip-standard-20261018` 的简略／详细行序、
  新鲜度、增益持续（`buffs` 均为 600 秒）与「不填 stats」约定。
- **装备缩略摘要**：防御类装备核心行均为修正项，走 2.23 增益／减益分组，行为正确。
- **武器浮窗**：19 把枪械 + 8 把近战 + 弓 + 法杖 + 3 把工具的摘要字段顺序、单位
  （ms／s／m／×／`/100`）与 `ColdSteelWeaponText.h` 常量一致。
- **武器 `desc`**：全部 ≤200 字，无排行词、无跨型号定位；抽查 desc 内数字与 `base` 一致。
- **装备稀有度**：装备类 `rarity`/`grade` 已全部清空，符合 2026-10-09 规则。
- **改造栏 other catalogs**：`bow-gunsmith.json`、`staff-gunsmith.json`、
  `tool-gunsmith.json`、`warhammer-gunsmith.json` 的 `special_effects` 均为独立机制短段，
  没有复述常驻数值，也没有把派生伤害拆成卡。

## 五、保留项（本轮未改，需要用户裁定）

自检脚本剩余 4 项，都是既有设计而非本轮引入（已核对 HEAD 同样报这 4 项）：

1. **`magazine/ext_mag` 跨枪 3 个版本**：长枪 +10 发／`reload_mult` 1.25，手枪
   +3 发／1.1，G18 +16 发／1.1。同一 `(slot,id)` 跨枪数值不同，但这是按各枪弹匣
   实际长度定的，改统一会动平衡。
2. **`reload_device/false` 2 个版本**：DW715 多一条「逐发入膛结算；少量补弹耗时更短」，
   其余三把为空。属左轮专属机制说明。
3. **`reload_device/super90_tube_loader` 2 个版本**：M870 的第三条写「回握护木泵动上膛」，
   SUPER90 写「释放枪机」——两把枪上膛方式本来就不同。
4. **`ue_pit_viper2011` items 物理攻击 44 ≠ `base.damage` 22**：2026-10-19 重拟公式时
   刻意把展示值按 dex=wis≈27 基线标到 44（见 `Docs/Combat/pitviper-2011-rebalance-20261019.md`）；
   枪械浮窗跳过静态「物理攻击」行，不影响显示，但脚本按逐字相等判定。

## 六、改动文件

- `Source/FPSGAME/UI/ColdSteelItemTooltipData.cpp`：分类／槽位映射；单手刀主卡。
- `Source/FPSGAME/UI/ColdSteelItemTooltipSummary.cpp`：祭品／材料摘要符号分组；单手刀摘要。
- `Source/FPSGAME/UI/ColdSteelInventoryTypes.h`：新增 `IsOneHandedMelee()`。
- `Content/ColdSteelData/gunsmith.json`：19 条 effects／description／name 文案，7 把枪的槽位清单。
- `Content/ColdSteelData/melee-gunsmith.json`：3 处派生伤害／手写数字。
- `Content/ColdSteelData/items.json`：3 件装备的类型名。
- `Tools/Weapons/check_attachment_consistency.py`：`MODEL_TOKENS` 补 M870／Saiga 12K 等
  型号名（此前写枪名会被误判成「残留可推导数字」）。

## 七、构建与测试

- Editor 构建 `Result: Succeeded`，366 项动作，295.37 秒，日志
  `Saved/BuildEditor/build-20261021-145804.log`；`ColdSteelItemTooltipData.cpp`[97]、
  `ColdSteelItemTooltipSummary.cpp`[85] 均编入，`UnrealEditor-FPSGAME.dll` 15:02:59 重链。
- 复核构建返回 `Target is up to date`。
- 自检脚本问题数 39 → 4（余项见上）。
- **未启动编辑器、未进 PIE、未截图**；浮窗排版、分组颜色与实际观感由用户验收。
