# 力大无穷：史诗近战与弓类前缀（2026-10-02）

## 数值合同

卷轴 `enchant_scroll_boundless_strength`，附魔 `boundlessStrength`，名称「力大无穷」，前缀，史诗稀有度，限制 `meleeOrBow`。效果为装备力量 +15；近战武器重击蓄力速度 +30%，弓类拉弓速度 +30%。沿用史诗卷轴的售价 4000、魔尘费用 800、统一写实图标、1×2 占格和 99 叠放；深度 8 起的掉落池权重 1，每次 1 张。

速度加成采用加法，时间采用速度的倒数：

`实际蓄力时间 = 重击技能基础蓄力时间 ÷ (1 + 改造蓄力速度增量之和 + 附魔蓄力速度增量)`。

例如改造 +15%、附魔 +30% 合计速度 +45%，2 秒基础蓄力变为 `2 / 1.45 ≈ 1.38 秒`；只有本附魔时为 `2 / 1.30 ≈ 1.54 秒`。技能升级对基础蓄力时间的缩短先应用，再除以合计速度。不能把 +30% 速度写成耗时 ×0.70，也不能将改造与附魔速度相乘。

## 实战与预览同源

- 附魔效果键 `heavyChargeSpeedBonus=0.30`、`bowDrawSpeedBonus=0.30` 和 `str=15`，复用既有前缀替换、后缀保留、库存消耗、命名与附魔存档路径；速度效果按实际武器类型读取。
- `FMeleeModifiers::HeavyChargeSpeedBonus` 是加法增量；近战改造目录字段 `stats.heavy_charge_speed_bonus`，0.15 表示 +15%。目录加载与 `UGunsmithSystem::Calculate` 都按加法汇总，原厂默认 0。
- `ColdSteelMelee::Evaluate` 汇总改造和实际物品的附魔，再产出 `HeavyChargeSpeedBonus` 与 `HeavyChargeSeconds`。武器提示、附魔前后对比、枪匠整体预览和选中配件详情全部读取该结果。
- `BeginHeavyCharge` 在起手时捕获同一份时长。手动松开、快捷栏自动蓄满释放、蓄力进度、提示和既有动作重定时继续使用 `RequiredChargeSeconds`，不分别重算时钟；后续挥砍攻速不被该字段改变。
- 近战限制沿用既有剑、斧、镐分类；蓄力速度作用于支持蓄力重击的动作，不新增斧镐重击动作。

## 弓类扩展与加法叠加

同一卷轴现在可对弓附魔，保留力量 +15。`CanEnchant` 在枪械目录门槛之前处理 `meleeOrBow`，因此既有弓目录可以进入附魔报价、预览、消耗与保存流程。

`实际拉弓时间 = 基础拉弓时间 ÷ (1 + 改造拉弓速度增量之和 + 装备拉弓速度增量 + 当前弓附魔拉弓速度增量)`，再沿用独立的附魔间隔倍率、弓精通冷却折减及既有 0.3 秒下限。+15% 改造与 +30% 附魔合计 +45%；以 1.4 秒基础拉弓为例，只有本附魔为 `1.4 / 1.30 ≈ 1.08 秒`，同时有 +15% 改造时为 `1.4 / 1.45 ≈ 0.97 秒`。

`FBowModifiers::DrawSpeedBonus` 是加法增量。新改造字段 `stats.draw_speed_bonus=0.15` 表示速度 +15%。旧字段 `draw_mult` 表示耗时倍率，每个配件在聚合时换算为 `1 / draw_mult - 1` 的等效速度增量后相加：例如 `draw_mult=0.80` 是耗时 -20%、等效速度 +25%，加上本附魔则总速度 +55%，不能标成 +50%。旧单配件数值不变；多配件组合按新增的加法叠加规则汇总，不再连乘耗时倍率。

`ColdSteelWeaponStats::BowDrawSpeedBonus` 统一合计改造、装备 `bowDrawSpeed` 与当前实例附魔 `bowDrawSpeedBonus`，`Interval` 和 `ColdSteelBow::Evaluate` 共同消费该结果。弓动作起手已有共享间隔读取，因此拉弓进度、动作与声音沿用同一时长；搭箭时间、箭速和持弓时间不因该字段改变。物品附魔卡片按弓类型显示拉弓效果，实战参数、附魔前后比较、改造台整体比较与选中配件详情共同展示总速度及实际时间；附魔比较直接读取 `Evaluate.Draw`，避免将已改造耗时再应用一次改造速度。

## 力量与属性公式

`EquipmentBonusFor` 将装备实例上的 `_enchantEffects` 数值并入装备属性。`str=15` 与装备的原始力量加成共用原有装备范围、感染折减及属性派生链，装备/卸下与同槽前缀替换自动重算；不会写入角色已分配的基础力量。

武器属性公式读取装备力量。加工预览中的物品尚未提交，`AttackFormulaAttribute` 用该候选实例的附魔属性替换档案里同实例的已装备贡献，避免已装备的 +15 再加一次，并使新增或替换前缀的预览反映属性变化。物品附魔卡片、加工摘要和比较表分别列出力量与当前武器的重击蓄力或拉弓速度。

## 交付方式

按用户规则，只做后台开发、必要构建与落盘，不打开 UE 或游戏，不进行自测、lint、静态检查、截图、渲染或验收。无新增表现资产制作需求，卷轴复用既有正式资产；用户自行进行玩法测试。

2026-10-02 近战初版必要构建：`FPSGAME Win64 Development` 返回 `Result: Succeeded`，日志 `Saved/BoundlessStrength/gameBuild.log`，Game 产物已更新。`FPSGAMEEditor` 完成源编译后，链接 `Binaries/Win64/UnrealEditor-FPSGAME.dll` 时被构建期间已打开的 `UnrealEditor.exe` 占用，报 `LNK1104`；日志 `Saved/BoundlessStrength/editorBuild.log`。当时保留运行中的编辑器与所有修改，没有关闭或重启其他进程，Editor DLL 未更新。未进行玩法测试或视觉验收。

2026-10-02 弓类扩展交付：通过作者脚本的 `-OutputSubdirectory BoundlessStrengthBow` 完成后台 `FPSGAME Win64 Development` 与 `FPSGAMEEditor Win64 Development` 两个目标，均返回成功，Game 产物与 Editor DLL 已更新。本次 Editor 构建前 DLL 可写，未再遇到初版的占用阻塞；没有启动、关闭或重启编辑器。构建日志位于 `Saved/BoundlessStrengthBow/gameBuild.log`、`editorBuild.log`，状态记录为 `delivery.json`。仅完成源码、数据、文档落盘和必要构建，未测试、未运行游戏，由用户实测。
