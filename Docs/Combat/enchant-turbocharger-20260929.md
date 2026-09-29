# 附魔卷轴「涡轮增压」：机枪持续开火射速爬升（2026-09-29）

用户要求新建一张附魔卷轴：限定轻机枪类武器使用，附魔后**修改武器的攻击方式**——初始射速降低为原来的
三分之一，在一定时间内**线性**达到原射速的 2 倍；参考原项目（E 盘 `game-dev`）能量轻机枪的爬升代码，
做好全套开发（数据、规则、战斗公式、UI 与说明）。

已确认的设计口径（四项均由用户选定）：

| 项目 | 结论 |
| --- | --- |
| 适用范围 | 所有 `weaponType == "machineGun"` 武器（当前为 `ue_pkm_lowpoly`） |
| 爬升时间 | 2.5 秒（对齐原项目 `energy_lmg.rampUpTime = 2500`） |
| 停火复位 | 松扳机／换弹／切枪**立即**回到初始 1/3 射速，无衰减延迟（原项目能量轻机枪口径） |
| 词缀与费用 | 前缀「涡轮增压」·`rare`·400 魔法粉尘 |

## 数值

| 参数键 | 值 | 含义 | 来源 |
| --- | --- | --- | --- |
| `turboRampStartMul` | 3.0 | 起步攻击间隔倍率：间隔 ×3，等于射速 1/3 | 用户指定 |
| `turboRampPeakMul` | 0.5 | 峰值攻击间隔倍率：间隔 ×0.5，等于射速 2 倍 | 用户指定 |
| `turboRampSeconds` | 2.5 | 线性爬升时间（秒） | 原项目能量轻机枪 `rampUpTime: 2500` |

三个键**同属一次附魔**：任一项缺失或非正数，`ColdSteelCombat::TurboRamp` 返回未启用，
射速完全按原值走，避免半套数据把射速改成未定义状态。

目录基线（`gunsmith.json` 的 `fire_interval`，未计配件与强化）：

| 武器 | 目录射速 | 起步（1/3） | 峰值（2 倍） |
| --- | --- | --- | --- |
| `ue_pkm_lowpoly` PKM | 0.092308 s · 650 发/分 | 0.27692 s · 217 发/分 | 0.046154 s · 1300 发/分 |

表中只列当前**已发布**目录里的机枪（HEAD 的 `ue_pkm_lowpoly`）；后续新增的 `machineGun` 武器自动套用同一规则，
数值按各自 `fire_interval` 现算，本表不预先登记未发布条目。

按目录值算，爬升期的实际收益是**积分**而不是起步与峰值的平均：间隔在 2.5 秒内线性缩短，
发数按 `N(t) = (1/I)·ln(3/(3-2.5t/T))` 累积。

| 指标 | PKM | 201 轻机枪 |
| --- | --- | --- |
| 爬升期 2.5 秒实发 | 19.4 发 | 23.9 发 |
| 未附魔同期实发 | 27.1 发 | 33.3 发 |
| 爬升期平均射速 | 466 发/分 | 573 发/分 |
| 峰值稳态 | 1300 发/分 | 1600 发/分 |

连续开火 **3.21 秒**后累计发射量才与未附魔持平——该时刻与具体武器无关（三个倍率对所有机枪相同），
之后按峰值净收益线性增长（+100%）。停火立即回到 1/3，所以"打几发就松手"始终是净亏，
只有持续压制才回本。以上均为目录基线，供平衡判断。

## 运行时语义

```
I_charged = 目录间隔 × 附魔 attackIntervalMul（本卷轴不带该键，恒为 1）
倍率(t)   = 3.0 + (0.5 - 3.0) × clamp(t / 2.5, 0, 1)      // t = 本次持续开火秒数
实际间隔  = I_charged × 倍率(t)
```

- `t` 只在**真正持续开火**时累积：`bFireHeld && 武器就绪 && !IsWeaponBusy() && !冲刺中 && 弹匣有余弹`，
  与 `ServiceHeldFire` 的射击门槛同口径，多一条余弹要求。
- 松扳机、换弹、切枪、弹匣打空、失去附魔任意一项成立，`t` 立即清零，射速当帧回到起步档。
- 到达 2.5 秒后停在峰值，不再继续加速（不叠加、不溢出）。
- 每条射出的子弹用**发射当帧**的倍率结算自己的间隔；命中判定的 `NextAllowedShotTime` 节拍与
  视觉节奏因此始终一致。

实现位置：

| 位置 | 作用 |
| --- | --- |
| `ColdSteelCombat::TurboRamp` / `TurboIntervalMultiplier`（`Weapons/ColdSteelEnchantmentCombat.cpp`） | 纯函数：解析参数、按秒数线性插值倍率 |
| `AFPSGAMECharacter::UpdateTurboRamp` | 每帧在 `ServiceHeldFire` 之前推进／清零持续开火秒数 |
| `AFPSGAMECharacter::EffectiveFireInterval` | 唯一取值口：`FireInterval × 倍率` |
| `FPSGAMECharacter::FireShot` | 节拍推进、PKM 供弹动画速率改用有效间隔 |
| `FPSGAMECharacter::ServiceHeldFire` | 追赶批次后的节拍对齐用有效间隔 |
| `AFPSGAMECharacter::ApplyColdSteelProfile` | 随档案缓存爬升参数；换枪或失去附魔即清零秒数 |

参数在档案发布时解析一次（`ApplyColdSteelProfile`），开火循环只做插值，不在每帧读 JSON，
沿用现有的有限解析缓存与"面板与实战同源"约定。

## 数据与规则

| 文件 | 改动 |
| --- | --- |
| `Content/ColdSteelData/enhancement.json` | 新增第 5 条卷轴 `turbocharger`（前缀、`restriction: "machineGun"`、400 魔法粉尘、三个爬升键） |
| `Content/ColdSteelData/items.json` | 新增 `enchant_scroll_turbocharger`（`rare`、消耗品、`scroll_id: "turbocharger"`、售价 2000、堆叠 99、共用魔法卷轴图标） |
| `Content/ColdSteelData/dungeon_loot.json` | 8 层掉落表新增该卷轴（weight 2，与「骷髅射手」同档） |
| `Content/ColdSteelData/tooltip-reference.json` | 补 `enchant_scroll_turbocharger` 空条目 |
| `ColdSteelEnhancementSystem::CanEnchant` | 新增 `machineGun` 类别键判定：只接受同类武器 |

`restriction` 语义保持原样：`firearm`（枪械通用，如骷髅射手）与 `weapon`（无类别限制，如狼蛛）
仍按旧口径，`machineGun` 是新的类别键，步枪、手枪、弓、法杖一律拒绝。
卷轴占**前缀**位，因此与「骷髅射手」互斥（同位置替换），可与后缀「狼蛛」共存。

## UI 与说明

| 位置 | 改动 |
| --- | --- |
| 物品提示「附魔效果」卡 | 新增「射速倍率 `1/3 → 2 倍`」与「加速时间 `2.5 秒，停火立即复位`」两行 |
| 物品提示「战斗参数」 | 有该附魔时在理论射速之后补「起步射速」「峰值射速」两行（发/分） |
| 附魔台预览摘要 | 选中该卷轴时输出「持续开火 X 秒：射速 A → B 发/分」，数字取当前装备的实际间隔 |
| 卷轴物品说明 | 「可以给轻机枪类武器附魔前缀「涡轮增压」。」 |

面板与实战同源：展示的起步／峰值倍数直接用 `_enchantEffects` 的三个键插值，附魔台的具体发/分
再用 `ColdSteelWeaponStats::Interval` 取当前装备（含配件与强化）的实际间隔，不另立一套公式。

## 与原项目的关系

原项目能量轻机枪（`src/entities/player/update.js` + `base.js`）用
`currentCooldown = round(baseCooldown - (baseCooldown - maxCooldown) * rampProgress)`、
`rampProgress = min(1, fireTime / rampUpTime)`，并且**只在开火时**累加 `fireTime`，停火即 `fireTime = 0`、
`maxCooldown = baseCooldown`。本卷轴沿用同一口径：线性插值、开火才累积、停火立即复位；
时间取 2500 ms 也与原项目一致。

原项目另有 `MIN_GUN_ATTACK_INTERVAL = 40`（`src/config/gun-ammo.js`），那是**静态间隔**的下限，
原项目能量轻机枪的爬升走 `maxCooldown` 单独参数，不经过该函数。新项目 `ColdSteelWeaponStats::Interval`
没有对应下限，因此 201 轻机枪峰值 37.5 ms 会略低于原项目那道静态门槛——这是"精确 2 倍"的必然结果，
未额外加限，如需收紧请指定峰值间隔下限。

原项目的 `_gunRampStates`（带 `decayDelay` / `decayTime` 的缓慢回落变体）是**未启用**的另一套参数，
本次按用户选定取"立即复位"，未引入衰减延迟。

## 未改动边界

- 枪械静态显示口径不变：`ColdSteelWeaponStats::Interval` 仍只乘附魔的 `attackIntervalMul`，
  爬升是**动态**倍率，只在射击节拍上生效，因此角色面板/枪匠总览的「射击间隔」仍是目录值。
- `ApplyShotFeedback` 的视觉回稳时长仍按静态 `FireInterval` 计算（现有上下限 65–120 ms 未动），
  视觉抖动在高射速下自然累积，不做额外补偿。
- 未给其他武器类别开放该卷轴；未改伤害、后坐力、散布、换弹与弹药消耗。
- 未改附魔台的"只列背包卷轴"过滤与转换晶尘等既有缺口。

## 验证

按用户规则**未运行**编辑器、PIE、截图或验收用例；实战读数与手感由用户测试。
**用户已于 2026-09-29 在本机实测通过**（附魔生效、射速爬升符合预期）。
`ColdSteelEnhancementAudit` 只补了一条源码断言（卷轴定义能加载、机枪为真、步枪为假），同样未运行。

编译状态（`FPSGAMEEditor Win64 Development`，日志见 `Saved/BuildEditor/`）：

| 文件 | 结果 |
| --- | --- |
| `ColdSteelEnhancementCombat.cpp` | 通过（`cl` 直调响应文件，退出码 0） |
| `FPSGAMECharacterProfile.cpp` | 通过（同上） |
| `FPSGAMECharacter.cpp` | 通过（UBT 编译动作 [92/196] 无诊断） |
| `ColdSteelEnhancementSystem.cpp` / `ColdSteelEnhancementWidget.cpp` | 通过（动作 [21] / [28]） |
| `ColdSteelItemTooltipData.cpp` / `ColdSteelEnhancementAudit.cpp` | 通过（动作 [52] / [22]） |

**模块已链接**：同一工作区另有一个未纳入 Git 的在建文件 `Source/FPSGAME/UI/ColdSteelExpHUD.cpp`
（他人正在编辑的底部经验条 HUD），首轮构建因它第 25 行 `FProgressBarStyle::BarBackground`（UE 5.8 的该成员是
`BackgroundImage`）报 `Result: Failed (OtherCompilationError)`。该文件不属于本次改动范围，未做修改；
对方于 15:22:47 自行修正后，15:23:33 的编辑器构建 `Result: Succeeded`，产出
`Binaries/Win64/UnrealEditor-FPSGAME.dll`（15:23:39，晚于本次全部源码改动的最新时间 15:17:46）。
随后复跑 `FPSGAMEEditor Win64 Development` 得到 `Target is up to date` / `Result: Succeeded`
（`Saved/BuildEditor/build-20260929-152445.log`），确认本次改动已进入链接产物。

### 实现注意

`FColdSteelTurboRamp` 的前置声明必须写在 `namespace ColdSteelCombat` **之外**：
命名空间内的 `const class UColdSteelEnhancementSystem*` 会新建 `ColdSteelCombat::UColdSteelEnhancementSystem`
并遮蔽全局类，导致既有的 `Snapshot` 一起报"使用了未定义类型"。首轮构建即因此失败，已按上述方式修正。