# 采集工具改造系统：伐木斧与矿镐四栏（2026-09-24）

> 本文是本次接入的制作与检查记录。运行口径以 [采集工具战斗接入](../../skills/ue5-weapon-workflow/references/harvesting-tools.md) 的「改造系统」一节为准；目录数值以 `Content/ColdSteelData/tool-gunsmith.json` 与离线自检报告为准。

用户要求按改造标准工作流为伐木斧、矿镐加入改造系统，开放握把、握柄、改件、主部件四栏，并用改造优化采集（产出、所需命中、距离、体力、挥速）同时保留自卫定位。本次不改动采集奖励表、资源身份、存档位置与 PCG 补生口径。

## 目录与栏目

四栏沿用「栏目 ≠ 网格」：当前全部是**数值改造**，沿用原装外形，没有实体模块；`appearance` 字段如实说明外观归属，实体拆分后按同一改造 ID 接入。

| 栏目 | 键 | 选项（斧／镐共用除主部件） | 主要影响 |
| --- | --- | --- | --- |
| 握把 | `grip` | 缓冲缠把；快手握位；稳固握把 | 体力、命中宽容半径、挥速、自卫伤害 |
| 握柄 | `shaft` | 加长握柄；白蜡轻柄；铁箍硬木柄 | 采集距离、攻击范围、挥速、体力、自卫伤害与削韧 |
| 改件 | `fitting` | 楔紧件；磨石保养件；幸运挂饰 | 所需有效命中、采集产出、额外产出几率、暴击率 |
| 主部件 | `head` | 斧：伐木宽刃头／淬硬斧刃／劈裂斧头<br>镐：采矿尖镐头／破碎镐头／棱齿镐头 | 采集产出、额外产出几率、自卫伤害、削韧、挥速 |

每栏另有 factory（`id=false`，名称取栏目 `default`），由加载器生成，目录不得自带。主部件按工具分流（`weapons` 字段限定），其余三栏两把工具共用同一份定义，加载器复制到各自条目。

采集吞吐上限（斧／镐同一套栏目，倍率相乘）：快手握位 ＋ 白蜡轻柄 ＋ 楔紧件 ＋ 伐木宽刃头／采矿尖镐头 → 命中 2 次、产出 ×1.30、挥速 ×1.232、体力 ×0.924、自卫伤害 ×0.764，单位时间产出约为出厂 **2.4 倍**。把楔紧件换成磨石保养件则产出 ×1.495 但命中回到 3 次，吞吐约 **1.84 倍**；幸运挂饰走额外产出几率 ＋15%（或劈裂斧头／棱齿镐头 ＋20%），产出倍率相应回落。**命中减免只允许改件栏一个来源**，保证砍倒／开采最少仍需 2 次有效命中，采集节奏与镜头反馈不被改造抹平；离线自检把这条锁成断言。

## 数值口径与作用链

唯一评估入口 `Source/FPSGAME/Production/ProductionToolStats.h::ColdSteelTool::Evaluate(Item, Profile, Preview*)` → `FProductionToolStats`。采集链、自卫链、物品浮窗、摘要指标、工作台总览／详情、图鉴都读这一份结果，任何一处不得二次换算。倍率相乘、绝对值相加，工具分支在 `UGunsmithSystem::Calculate` 内累加并夹取。

| 改造项 | 落点 | 边界 |
| --- | --- | --- |
| `harvest_yield_mult` | `StageProductionDrops` 逐条乘在出厂奖励数量上（木材按根散落，石材／矿石仍是单个堆叠拾取物） | 四舍五入，最少 1 |
| `bonus_harvest_chance` | 采尽结算判定一次，成功则整份材料再落一次 | 期望产出 ＝ 产出倍率 ×（1＋几率） |
| `harvest_hits_add` | `ColdSteelTool::HitsNeeded(Factory, Stats)` | 运行时夹在 ≥1；采尽判定按**出厂**次数（`Target.HitsNeeded()`），完成判定用 `After >= Needed`，采尽后进度写 `max(After, 出厂次数)`，`IsProductionDepleted` 与 PCG 补生仍按出厂口径判断 |
| `harvest_reach_mult`／`harvest_radius_add_cm` | 采集射线距离与辅助球半径 | 矿镐出厂半径 0（只认中心射线），所以辅助宽度用**绝对加值**；倍率对 0 是空操作 |
| `attack_speed_mult` | 只压缩真实时钟 `RateScale` | 动画／镜头关键帧是作者秒：采样器收 `AuthoredElapsed = Elapsed × RateScale`，真实阈值除以 `RateScale`；`RateScale=1` 时逐帧等价 |
| `stamina_mult` | 每次挥动的采集体力，采集与自卫共用同一笔 | `ColdSteelMelee::AttackStamina` 对工具改走 `HarvestCost`（此前误用近战 15 点，HUD 可用次数会算错） |
| `damage_mult`／`toughness_damage_mult`／`crit_chance_add` | 自卫命中：`damage_mult` 走 `ProcessedDamage` 的 `MeleeDamageMultiplier` 通道，削韧与暴击随 `FColdSteelSkillShot` 进 `ColdSteelSkills::ApplyHit` | 不给连击、重击、格挡、精通口径；工具保持 `bMelee=true`，**不**加工具版 `hit_reaction_mult`（受击倍率用 `TGuardValue` 设值而非相乘，内层默认 1 会覆盖外层） |

采集进度与身份：`gunsmith_parts` 写在物品 Data，槽位键即栏目键；`NormalizeProductionState` 只刷新定义字段（含 `desc`），不覆盖 `gunsmith_parts`，旧存档无工具改造字段时按 factory 结算，不需要迁移。铁铲没有目录条目（`IsEquippedProductionTool` 只认斧与镐），`Evaluate` 对它返回出厂倍率。

进度口径分两层：「此处资源已经采尽」按**出厂**所需命中判断，完成判定用 `After >= Needed`。存档里的进度是历史累计命中，可能是用出厂工具打出来的；若两处都用改造后的次数，出厂打到 2 次的资源会在换上楔紧件后被判为采尽而不发奖励，或卡在「差一次」的中间态。采尽后写入 `max(After, 出厂次数)`，因此拆掉改造也不会让已采尽的资源复活。

## UI 接入

- 工作台复用近战那套结构：`IsStandaloneWorkbench() = IsMeleeWorkbench() || IsToolWorkbench()` 管结构布局，内容分支按 `IsToolWorkbench()` 分流（副标题、总览标题、占位文案、详情行）。预览用 `tool_mesh` 建独立静态网格组件并沿用既有正交取景；**没有**扩 `ColdSteelMeleePreview::Supports`，避免把工具塞进背包图标渲染链。
- 总览分「采集」「自卫」两段，行名与目录 `effects` 逐字一致；体力只列一行（采集与自卫共用同一笔）。
- 选项卡片图标由 `SMeleePartIcon` 的程序化矢量分支绘制（握把／握柄／改件／主部件，主部件按 Definition 区分斧头与镐头），不新增位图资源。
- 物品浮窗：「近战参数」改为自卫口径并读评估实值，「采集参数」补产出倍率、额外产出几率、宽容半径与**动态**所需命中（原本硬编码「三次」）；`items` 的 `desc` 同步去掉硬编码次数。摘要指标新增采集键，装备对比因此可用。
- 图鉴新增「采集工具数值」段（出厂口径，不读玩家实例改造）；此前工具会落到「未登记进改造目录」分支。
- 背包「改造武器」按钮、J 键、`OpenGunsmith` 都走 `ModifiableWeapon`，工具自动覆盖，没有新增第二条入口。

## 文件与状态

新增：`Content/ColdSteelData/tool-gunsmith.json`、`Source/FPSGAME/Weapons/ToolGunsmith.cpp`、`Source/FPSGAME/Production/ProductionToolStats.{h,cpp}`、`Source/FPSGAME/UI/M4ToolGunsmith.cpp`、`Tools/Production/check_tool_modification_consistency.py`。

改动：`GunsmithSystem.{h,cpp}`、`MeleeGunsmith.cpp`、`ProductionToolComponent.{h,cpp}`、`ProductionToolMotion.cpp`、`ProductionAxeLocomotion.cpp`、`MeleeWeaponStats.cpp`、`ColdSteelProductionTools.cpp`、`ColdSteelProductionDrops.cpp`、`ColdSteelStatusModel.h`、`M4Gunsmith{Widget,Layout,Overview,SelectedDetails,Controller}.cpp`、`M4{Melee,Standalone}Preview.cpp`、`SMeleePartIcon.h`、`ColdSteelItemTooltip{Data,Summary,Formula}.cpp`、`ColdSteelCodexPage.cpp`、`production_tools.json`、技能文档 `harvesting-tools.md` 与 `SKILL.md`。

构建与自检：

- `FPSGAME Win64 Development` 原生构建成功（UBT 625 s，`Result: Succeeded`，日志 `Saved/BuildEditor/build-tool-gunsmith-game.log`）；唯一告警是既有的 `SkeletonStockAudit.cpp` `FImageUtils::CompressImageArray` 弃用提示，与本次无关。
- `FPSGAMEEditor Win64 Development` **未构建**：用户编辑器（PID 111680）正打开本工程，按规则不主动关闭；编辑器目标需在该会话结束后重编。
- `python Tools/Production/check_tool_modification_consistency.py` 退出 0（报告 `Saved/Production/tool-modification-report.txt`）；并用注入错误的临时副本反测，确认未登记键、行名同义词、benefit 方向、description 手写数字、命中下限、加载器键集合漂移六类问题都能被抓到（临时副本已删除）。
- 未启动交互式编辑器、游戏、PIE 或存档读写测试；采集手感、产出落点、自卫伤害与工作台观感按用户规则交由用户测试。

## 后续

1. 实体模块拆分（柄、头、改件）后按同一改造 ID 接入视模与双手间距动作家族，目录 `appearance` 字段随之改写；在此之前不要为数值选项造网格。
2. 若开放铁铲改造，需要先补它的采集口径（一击一层、回填上限）与 `Evaluate` 分支，不能直接套斧／镐倍率。
3. 剑类在图鉴仍落到「未登记进改造目录」分支（`Gunsmith->Weapon()` 只覆盖枪械），属既有缺口，本次未顺带修改以免与并行工作冲突。
