# Buff/Debuff 100% 迁移覆盖矩阵

审计与迁移日期：2026-09-24 ｜ 源：`E:\无尽轮回\长期备份\2026-7-13-1\game-dev`（Phaser/DOM，只读）
目标：`D:\FPS3D\FPSGAME`（UE 5.8.2）左上角状态栏 + 机制层
配套盘点：[target-inventory.md](target-inventory.md)（迁移前 UE 现状）｜ 源侧五卷穷举：source-inventory.md ＋ -1…-4.md（106 静态 ID 全目录/46 机制/约105施加入口/HUD 规格）｜ 前作公式审计：[gamedev-formula-migration-20260914.md](../gamedev-formula-migration-20260914.md)

图标策略（用户指定）：**全部使用 emoji/单字符占位符，零贴图资产**。tile 图标由
`UStatusEffectTile` 的 `UTextBlock`（seguiemj.ttf）渲染，与旧 DOM 栏的 emoji 字形一一对应；
后续换真图标只需替换 `status_effects.json` 的 `icon` 字段并接入贴图通路。

## 0. 架构映射

| 旧（gamedev） | UE 对应 | 说明 |
|---|---|---|
| `StatusBar`（单例 DOM 栏，玩家视角） | `UStatusEffectsComponent`（每实体 Records + 活状态适配器）+ `UStatusEffectsHUD`（只绑玩家 pawn） | HUD 绑定玩家即旧“玩家状态栏”语义；怪物身上的记录等价旧实体 `statusEffects[]`（内部账本，不显示） |
| `game-style.css` `.status-bar` 几何（104,12 / 252×44 / 54×44 格 / 2px 边框） | `StatusEffectsHUD.cpp` 逐像素复刻（已在前审计确认，本次未动） | 字体/色板按冷钢设计系统落地 |
| 实体 `STATUS_CONFIG` + `addStatusEffect/removeStatusEffect`（同型刷新取最大剩余） | `UStatusEffectsComponent::SetTimed/SetTimedDisplay/SetPersistent/SetBattles/Remove`（同型保留更长 End） | 语义一致；`×N`、`Ns`、`N场`、`持续` 文本格式一致 |
| `DamageableEntity.apply*/takeDamage` 机制链 | `UCombatStatusFormula`（目标侧）+ `CombatFormulaRuntime::MitigateMonster`（怪物承伤）+ `UFPSCombatHealthComponent::DamageAfterArmor/OnDamage`（玩家承伤） | 乘区顺序按旧链逐段取整（见 §2） |
| `tribute-effects.js` 聚合器 + `world122-tribute-system.js` | `UColdSteelStatusModel`（`TributeEffect`/`TributeSpecial`/`SyncTributeTiles`） | 献祭 30 分钟倒计时 = 旧 `RemainingSeconds=1800` |

## 1. 状态全量清单（旧 HUD 31 + 实体扩展 7 + 献祭 10）

图例：✅ 机制+显示均已在 UE 落地（本次迁移新增标 🆕）；♻️ 迁移前已有；⚠️ 机制端口就绪但旧生产者在 UE 无宿主（待玩法接入，代码路径完整）。

| # | type（=旧 key） | 图标(占位) | 旧机制 | UE 落地 | 状态 |
|---|---|---|---|---|---|
| 1 | stun 💫 | 💫 | 不能移动/攻击/技能/物品；同型刷新取最大 | `AddStun`：移速 0＋四类怪物 `InterruptAttack`＋玩家破防输入锁＋卡片；`StartDodge` 闸门 | ♻️+🆕 |
| 2 | poison ☠️ | ☠️ | 1 dmg/s/层，5s 消退 1 层 | `UMaggotPoisonComponent`（活状态适配器）＋🆕 statusImmune 拒绝上毒 | ♻️ |
| 3 | minePoison ☣ | ☣ | 毒区内每秒 maxHp×0.5% 魔伤；离区残留 3s；免疫=僵尸系/statusImmune | 🆕 `AddMinePoison(refresh,linger)`：Tick 每秒 `floor(maxHp*0.005)` → `UStatusMagicDamage`（走魔防链）＋卡片；毒区生成宿主未迁移 ⚠️ | 🆕⚠️ |
| 4 | slow 🐌 | 🐌 | -50% 移速 | 🆕 `AddSlow(Seconds,Percent)` → `MovementMultiplier` | 🆕 |
| 5 | waxSealSlow 🕯️ | 🕯️ | -20%（封顶90%）只刷新不叠层 | 🆕 `AddWaxSeal` | 🆕 |
| 6 | buff ✨ / shield 🛡️ | — | 通用占位（旧由具体技能写名） | 既有 Records（audit 夹具沿用） | ♻️ |
| 7 | bleed 🩸 | 🩸 | HP×1%/s×层（每秒），10s 消退 1 层，上限10 | `AddBleeding` 已有🆕补卡片与逐层消退刷新 | ♻️+🆕 |
| 8 | corrosion 🧪 | 🧪 | 每层物防 -5%，5s 消退 1 层，穿透后乘算 | `AddCorrosion`＋`CorrosionMultiplier` 双链消费已有；🆕 补玩家侧卡片同步（旧仅玩家有卡） | ♻️+🆕 |
| 9 | magicVulnerability 🔮 | 🔮 | 每层受魔伤 +5%，5s 消退 1 层 | `AddMagicVulnerability`＋消费已有（旧内部状态、无玩家卡，保持一致：机制记录无卡片） | ♻️ |
| 10 | droneVulnerability 🛸 | 🛸 | 按来源记账取最强快照；受所有伤害+X%、暴击率+Y%（仅友方来源）；击杀释放 | 🆕 `AddDroneMark/RemoveDroneMark`＋`MitigateMonster`承伤/魔爆率消费＋卡片（stacks=1、剩余取各来源最大）；无人机玩法宿主未迁移 ⚠️ | 🆕⚠️ |
| 11 | marbleHeal 🗿 | 🗿 | 击杀后 1s 内回复 maxHp×(killHpHealPercent-1) | 🆕 `AwardKill`→1 秒滴灌＋`marbleHeal` 卡片 | 🆕 |
| 12 | goddessBless ✨ / demonPrayer 🔥 + **63 地牢事件 buff**（1D 全目录） | ✨🔥📒⛏… | `_applyTemporaryBuff`：按场消耗（默认 3 场）、「N场」卡片、离层全清；goddess/demon 独立字段同通道 | 🆕 通用化：`dungeon_event_buffs.json`（63 条参数真源）＋`ApplyDungeonEventBuff(Id)` 施加通道＋`SyncDungeonBattleTiles` 全量目录门 diff 发布（`N场` 卡片，含 goddessBless/demonPrayer）；逐场消耗走 `CompleteDungeonFormulaBattle` 已有；事件选择 UI 宿主（dungeon-event-system 房间事件）未迁移 ⚠️ | 🆕⚠️ |
| 13 | fear 😨 | 😨 | 失控远离恐惧源、每层 -33% 移速 | `UHandBrainFearComponent`（活状态适配器）＋🆕 statusImmune 拒绝恐惧 | ♻️ |
| 14 | tributeSnowLotus 🪷 … tributeAstrolabe 🌟（10 项） | 🪷🌿🍑💎🌙🪨🩸🚩🗿🌟 | `SPECIAL_BUFFS` 键→卡片映射，文案“跟随献祭倒计时” | 🆕 `SyncTributeTiles`：effects 聚合>1 / specials 原值>0 → `SetPersistent`；献祭过期自动撤卡 | 🆕 |
| 15 | holyRenewal 💚 | 💚 | 每秒 maxHp×1%×层 回复 | `UFPSHolyRenewalComponent` 已有（本次未动，避免双实现） | ♻️ |
| 16 | holyWard 🛡️ | 🛡️ | 最终承伤 ×min(倍率)，卡片 | `AddHolyWard`＋`FinalMultiplier` 双链消费已有；🆕 补卡片 | ♻️+🆕 |
| 17 | chainSpell 🔗 | 🔗 | 下次施法魔伤/MP 按层放大 | 已有（施法端+消费端） | ♻️ |
| 18 | weaponHaste ➤ | ➤ | P4040 命中后移速 +10%，只刷新 | 🆕 `AddWeaponHaste`→`MovementMultiplier` 独立乘区；枪械命中钩子宿主 ⚠️ | 🆕⚠️ |
| 19 | chill ❄️ / frozen 🧊 | ❄️🧊 | 每层 -5%，20 层冻结（清 10 层、冻结期再受寒无效）、冻结受非魔伤 ×1.5 | 已有；🆕 冻结并入 `BlocksMovement`（禁闪避） | ♻️ |
| 20 | burn 🔥 | 🔥 | 独立层、0.5s tick、`floor(Matk×0.5)` 魔伤、statusImmune 拒绝 | `AddBurn` 已有；🆕 卡片（层数=存活层、随消退更新） | ♻️+🆕 |
| 21 | petrified 🗿 | 🗿 | 定格；魔法/电系承伤 ×值(默1.5) | 🆕 `AddPetrify`＋双链承伤消费＋`BlocksMovement` | 🆕 |
| 22 | flameArmor 🔥 | 🔥 | 攻击附魔伤＋0.5s 光环＋火花；卡片计时 | 技能系统已有；🆕 `StartArmor/EndArmor` 挂/撤卡片 | ♻️+🆕 |
| 23 | riposteInspiration ⚔ | ⚔ | 弹反后攻速+20%、耐力消耗-20%，6s 刷新 | 已有 | ♻️ |
| 24 | runeMagicVulnerability ◇ | ◇ | 受魔伤+10% 10s 只刷新 | 已有 | ♻️ |
| 25 | electrified ⚡ | ⚡ | 每层受电伤+3%、满 5 层过载=眩晕1.2s+链击 | 已有；🆕 普通命中眩晕与过载眩晕并入 `AddStun`（出卡片、锁移动） | ♻️+🆕 |
| 26 | haste 💨 | 💨 | 施法加速：每层 +10% 移速（时间=层×秒） | 机制已有（`AddHaste`+`MovementMultiplier`）；🆕 补 JSON 目录条目（此前显示回退 "?"） | ♻️+🆕 |
| 27 | inspire 📣 | 📣 | 激励（工头号召）：移速 ×1.33、攻击 ×1.5，只刷新 | 🆕 `AddInspire`：移速入 `MovementMultiplier`、输出入 `OutgoingDamageMultiplier`（玩家承伤链消费）＋卡片；怪物 AI 号召宿主 ⚠️ | 🆕⚠️ |
| 28 | statusImmune 🔰 | 🔰 | 免疫一切增减益（毒/恐惧/腐蚀/流血/灼烧/寒冷/感电/眩晕/束缚…） | 🆕 `AddStatusImmune(Seconds)`/`SetStatusImmune(bool)`；`IsImmune()` 闸门铺满全部 Add*＋毒/恐惧组件入口＋卡片 | 🆕 |
| 29 | bind ⛓️ | ⛓️ | 移速 0、禁闪避，可施法攻击 | 🆕 `AddBind`→`MovementMultiplier`=0＋`BlocksMovement`＋卡片；旧生产者（束缚陷阱类）宿主 ⚠️ | 🆕⚠️ |
| 30 | marked 🎯 | 🎯 | 受所有伤害 ×(1+value)（取更高 value） | 🆕 `AddMarked`＋`MarkedMultiplier` 双链承伤消费；铁匠铺宿主 ⚠️（内部状态，旧玩家栏不显示，保持一致） | 🆕⚠️ |
| 31 | camelFright 🐪 | 🐪 | 受惊方输出 -(value)（同类取更强、不叠层） | 🆕 `AddCamelFright`＋`OutgoingDamageMultiplier`（怪物打玩家/玩家打怪两条承伤链都按攻击侧折减）；骆驼骑兵宿主 ⚠️ | 🆕⚠️ |
| 32 | magicResistanceShred ✦ | ✦ | 魔防穿透削减（max 比例+时间） | `AddMagicResistanceShred`/`MagicShred` 已有并在 `Defense(...)` 消费；旧无卡片（内部状态），保持无卡 | ♻️ |

**覆盖核对（与源卷一 §1E 对账）**：静态唯一 106 ID = 实体层 28 ＋ HUD 独有 9＋1 ＋ 未注册 5 ＋ 地牢事件 63；上表逐行 + 地牢 63 全目录（`dungeon_event_buffs.json`，由 `Tools/Combat/generate_dungeon_event_buffs.py` 从卷一 1D 表落盘）全部落地。`status_effects.json` 现 **108 条**（45 通用＋63 地牢事件），无重复（脚本校验）。world122Tribute_* 动态族经 `OfferTribute`→`TributeEffect/Specials`→`SyncTributeTiles` 键式通道天然覆盖（不依赖枚举）。

## 2. 承伤链乘区顺序（按旧 `takeDamage`/player 子系统逐段取整复刻）

怪物侧（`CombatFormulaRuntime::MitigateMonster`，武器四分量与单发两路同序）：
`防御(物/魔防+穿透+shred+腐蚀) → 魔法加成 → 魔力易伤 → 石化(魔) → 感电(电) → [射程减免:UE无远程塔宿主,键位保留] → 无人机易伤 → 献祭monsterDamageTakenPercent → 冻结(非魔×1.5) → 暴击 → 来源侧减益(骆驼惊吓等) → 标记 → 圣佑`

玩家侧（`UFPSCombatHealthComponent::DamageAfterArmor`，新增 Attacker 参数；蛆毒照旧不过防御）：
`防御(+shred+腐蚀) → 魔力易伤 → 石化(魔) → 感电(电) → 无人机(仅友方来源,对玩家攻方恒1) → monsterAtkDownPercent(仅非玩家攻方) → 冻结(非魔×1.5) → 攻方骆驼惊吓折减 → 标记 → 圣佑 → 金刚石单次承伤封顶(maxHp×15%)`

玩家死亡链（`OnDamage`）：🆕 月影庇护（首次受击=“参战”，按 special 毫秒数无敌并无效该击，一次献祭一次）→ 🆕 蟠桃续命（`ConsumePeachRevive`：一次机会，原地 `max(1,floor(maxHp×30%))` 站起＋`ClearPoison`＋`PurgeTransient`，不走换 pawn 重生；旧“3 秒后原地复活”简化为即时，见 §4 偏差）。

## 3. 显示语义复刻要点

- 同型刷新保留更长剩余、Stacks 直接覆盖（旧 `updateEffectStacks`/max-remaining 行为）——audit 断言 9 继续成立。
- 致死清空：`Snapshot` 死亡即空栏（audit 17）；🆕 蟠桃原地复活不触发换 pawn，Records 自然保留（与旧 `_reviveInPlace` 保留其它状态、只清毒/腐蚀/眩晕一致——`PurgeTransient` 精确清算这些项）。
- `SetTimedDisplay(slow,🦴/致残/#8a8a7a)` 复刻旧“致残借 slow 计时、显示独立皮肤”。
-  tribute 卡 `SetPersistent(,'跟随献祭倒计时')` 复刻旧 durationText；过期/覆盖献祭自动撤卡（diff 发布，不逐帧广播）。
- 灼烧/流血/腐蚀/无人机卡改为**事件式**发布（层数变化才 SetTimed），倒计时由 `End` 自然同步——避免 60Hz `OnChanged` 广播（性能约束文件要求）。地牢/献祭卡片用 diff 发布（`HasType` 目录门过滤 `dungeon_relay_*` 等动态 ID）。
- 感电过载：🆕 链传导现在会给每个被传导敌人 **+1 感电层**（其自身满层可再过载，级联同旧 `_triggerElectrifiedOverload`）；此前仅传导伤害。
- `Definition()` 进程内 static 缓存：**改 JSON 需重启编辑器才生效**（本次目录从 33 → 108 条：+12 通用条目与 +63 地牢事件条目，下次启动后可见）。

## 4. 已知偏差与待宿主项（如实记录）

| 项 | 偏差 | 原因 |
|---|---|---|
| **HUD 串台缺陷不复刻** | 旧 `applyCripple/applyBleeding` 的 StatusBar 镜像**无阵营守卫**（源卷二 2.2/2.11 定案）：玩家给怪挂致残/流血会让怪物条目出现在玩家自己栏。UE 侧按“修复”迁移：HUD 只绑玩家 pawn，怪物卡片天然隔离 | 迁移决策：旧行为是被确认的缺陷，非规格 |
| **净化白名单** | 🆕 `CleanseDebuffs(Count)`：旧 SUPPORT_CLEANSE_TYPES 11 项精确顺序（poison→bleed→fear→chill→frozen→slow→waxSealSlow→bind→magicVulnerability→droneVulnerability→electrified），感电连 `_electrifiedStacks` 硬置零；毒/恐惧走组件真清 | 宿主=教堂高阶牧师 AI 群体支援（旧 `_applyTierSupport`，aiConfig 门控），UE 友好牧师未迁移 ⚠️；圣所(12项)/圣裁(10项)两套白名单属未迁移系统，成员清单已存档卷三 §3.10 |
| `_synergyPoisonChance` 死字段 | 明确**不接线** | 源卷三 §3.3.2 证实全项目无读取点，从未生效 |
| slow 皮肤（6 种）/bind(4)/drone(2) | 🆕 `SetTimedDisplay` 通道支持任意名/图标/色覆盖（首建写入语义一致）；具体皮肤由生产者传入 | 霜径迟滞/镇暴压制等生产者随各自系统迁移 |
| 蟠桃复活 | 即时原地站起（旧：3 秒后原地） | UE 侧 2s 换 pawn 重生管线不宜叠加 pending 窗口；机制（一次机会/比例/清算）完整 |
| 献祭卡显示 | 献祭生效即出卡（旧：仅地牢内出卡） | UE 献祭=30 分钟全局倒计时，无“本次地牢”门闩语义；文案已按“跟随献祭倒计时” |
| 矿毒僵尸系免疫 | 未实现按家族免疫 | 旧 `hasEnemyFamily('僵尸')` 无 UE 侧家族元数据；statusImmune 通道已通 |
| 点石成金(oreUpgrade)/血藤/狼旗/玉璧双生/星盘/招募/生产资源 | 聚合键+卡片+special 通道完整；挖矿品质、友好吸血、招募、生产等玩法宿主未迁移 | 旧侧宿主为 RTS/村庄系统，UE 尚无对应玩法 |
| 地牢事件 63 buff 参数与卡片 | 参数目录（`dungeon_event_buffs.json`）、施加通道（`ApplyDungeonEventBuff`）、逐场消耗与「N场」卡片全部落地；房间事件选择/成败判定 UI 流程未迁移 | UE 地牢事件玩法宿主（dungeon-event-system 房间流程）尚未接入；接入后一行调用即生效 |
| 无人机标记击杀释放 | `RemoveDroneMark(NAME_None)` 入口就绪；UE 无无人机技能宿主 | 同上 |
| 重甲套自动格挡/女墙掩护 | 装备套装机制，非状态系统；未动 | 范围外（前审计域） |
| 远程减伤 rangedReduction（旧内部状态） | UE 无对应生产者（箭塔体系未迁移）；乘区已保留 | 宿主缺失 |
| 字体依赖 | simhei/seguiemj 绝对路径 | 既有债务，前审计已记录 |

## 5. 回归风险自检

- `UStatusEffectsHUD`/tile 几何/0.1s 刷新/活状态适配器：**未改动**，21 条 `-StatusEffectsAudit` 断言的路径全部保持原语义（新增仅 Records 写入方）。
- `MovementMultiplier()` 由内联改为实现函数（新增 stun/bind/petrify/slow/wax/weaponHaste/inspire 项）；haste/chill/frozen 三项公式逐项未变。
- 灼烧跳伤伤害类保持 `UFireballDamage`（魔防链不变）；仅矿毒使用新 `UStatusMagicDamage` 并注册进 `IsMagic`。
- `FColdSteelFormulaBuff` 新增 `Specials` UPROPERTY：存档 JSON 向后兼容（旧档缺字段=空表）。
- 构建结果：见文末「构建记录」。

## 构建记录

- `FPSGAMEEditor Win64 Development`：**最终全绿**（含全部迁移批次：核心机制、63 地牢目录、地牢卡 diff TMap 化、感电级联传导、`CleanseDebuffs`；`Saved/buff-migration-build.log`，Result: Succeeded）。中途一轮曾被并行编辑器会话的 Live Coding 进程护栏拒写 DLL（瞬态，重试即过），同批源码另以 `FPSGAME Win64 Development` 游戏目标全量编译链接通过（`Saved/buff-migration-build-game.log`）。
- 发布：commit `9c32ad9` → `origin/main`（https://github.com/allang2208/3D-FPS.git）。工作树混有多个并行会话的未提交内容（感染/储物会话/巫婆/手势计费等），本提交按 hunk 级筛选暂存：9 个混合文件从工作树过滤他人行后以 blob 入索引（工作树逐字节未动），他人文件整体不入库。切片树在并行期无法独立编译（基线 HEAD 已引用未发布的 Dungeon 子系统），以全工作树构建绿作为代码正确性证据。
- 按用户规则未做运行/PIE 测试：机制行为以代码级复刻 + 构建通过为准（**未测试**）。
- `Definition()`/事件目录均为进程内 static 缓存：`status_effects.json`（108 条）与 `dungeon_event_buffs.json` 的新增内容在**编辑器重启后**生效。
