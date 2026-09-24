# 卷一 · §1 完整状态目录 + §6 图标资源清点

审计根：`E:\无尽轮回\长期备份\2026-7-13-1\game-dev`（只读）。行号 = 该快照物理行号。
- 实体层字典：`src/entities/damageable-entity.js` `addStatusEffect` 内 `STATUS_CONFIG`（**:477-506**，28 键）；未知 type 回退 `{ icon: '❓', name: type, color: '#8a7d6b' }`（**:507**）。
- HUD 层字典：`src/ui/status-bar.js` `STATUS_CONFIG`（**:10-42**，31 键，含 tooltip `desc` 原文）；未知 type 回退同 ❓/#8a7d6b（**:133**）；无 desc 回退 `'持续生效的状态效果。'`（**:91**）。

## 1A. 实体层注册状态（28 个 ID，逐一）

“HUD 列”指该 type 出现在玩家状态栏时的实际显示（bind/inspire/haste/statusImmune 无 HUD 字典项，由调用点显式传 options；magicResistanceShred/marked/camelFright 只施加给非玩家阵营，从不进栏；⚠️ applyCripple/applyBleeding 两处镜像无阵营守卫，怪物侧致残/流血会串入玩家栏，见卷四 §4.0）。

| # | ID | 实体名/图标/色（:477-506） | 类别 | HUD 显示 | desc 原文（status-bar.js:11-41） | 时长/叠加语义 | 定义行 |
|---|---|---|---|---|---|---|---|
| 1 | `stun` | 眩晕 💫 #9a7a5a | 控制 | 有（玩家被晕时） | 无法移动、攻击、使用技能与物品。 | 时长由调用方给（弹反 1000ms+、过载 1200ms、 lightning 750+lv×20ms…）；同类型剩余取长；`applyStunExtend` 特例为**加法延长**；无层数 | :478 |
| 2 | `poison` | 中毒 ☠️ #7a9a5a | debuff·DoT | 有（玩家中毒时） | 每秒受到层数点毒素伤害。 | 层数无上限；**每层独立 5000ms**，到期只退一层；1000ms tick 固定扣 `层数` 点 HP（直接扣血不吃防御） | :479 |
| 3 | `minePoison` | 矿毒 ☣ #a1b052 | debuff·DoT(环境) | 有 | 矿洞毒气：每秒以最大生命0.5%为基准结算魔法伤害；离开毒区后最多残留3秒，可净化。 | 单层；入区暴露 ≥2000ms 才感染；出区残留 `lingerMs=3000` 后清除；1000ms tick `max(maxHp×0.005, 0.1)` 魔法伤害（走防御） | :480 |
| 4 | `slow` | 减速 🐌 #5a7a9a | debuff | 有 | 移动速度降低 50%。 | 单层；剩余取长、`value` 取大；移速 ×(1−value)，玩家侧硬编码 ×0.5（update.js:343）；同一 type 有多种显示皮肤（见 1A-注①） | :481 |
| 5 | `bind` | 束缚 ⛓️ #7a5a8a | 控制(锁移速) | 有（玩家被缚时，显式 options） | —（走 desc 回退文案） | 单层；剩余取长；玩家 targetSpeed=0 且禁闪避；敌人列入移动阻断名单 | :482 |
| 6 | `buff` | 增益 ✨ #9a9a5a | buff·占位 | 有字典项 | 获得临时增益效果。 | **全项目已无施加者**（仅 dungeon-event-system.js:487-511 的遗留清理 `removeEffectByType('buff')` 还在引用） | :483 |
| 7 | `shield` | 护盾 🛡️ #5a8a9a | buff·占位 | 有字典项 | 获得护盾，减免受到的伤害。 | **无任何施加入口**（盾机制走 stamina 格挡，不注册此状态）；预留 ID | :484 |
| 8 | `bleed` | 流血 🩸 #9a3a3a | debuff·DoT | 有 | 持续流失生命值。 | 层数无上限；每层独立 10000ms 到期退一层；1000ms tick `max(1, floor(当前HP×1%×层数))` 直接扣血 | :485 |
| 9 | `corrosion` | 腐蚀 🧪 #9ab84f | debuff·降防 | 有 | 每层使物理防御降低 5%；每次倒计时结束只消退 1 层。 | 层数无上限；**共享 5000ms 倒计时**、到期退一层并重置；物防 ×(1−层×perStack)，perStack 默认 0.05 且跨施加取历史最大；防御乘区下限 0（伤害侧另有 10% 地板） | :486 |
| 10 | `inspire` | 激励 📣 #ffb347 | buff(怪物) | 有（玩家被激励时，显式 options） | — | 单层仅刷新时长；施加时直接乘属性 `atk×1.5`、`maxSpeed/speed×1.33`（options 可改），到期钩子除回 | :487 |
| 11 | `magicVulnerability` | 魔力易伤 🔮 #8a5a9a | debuff·增伤 | 无（只给敌方；HUD 字典有项但玩家侧无入口） | 每层使受到的魔法伤害提高 5%。 | 层数无上限；每层独立 5000ms 退一层；魔/电承伤 +5%/层；**机制层数不写 statusEffects**（apply 只动 `_magicVulnerabilityStacks`），HUD 字典项实际难被触发 | :488 |
| 12 | `magicResistanceShred` | 魔抗蚀刻 ✦ #9f7cff | debuff·降魔抗 | 无（仅施加给敌方） | — | 单层；不叠层，`value`(削减比例 ≤0.95) 取更强、时长取长；魔法/电系伤害的 mdef ×(1−value) | :489 |
| 13 | `droneVulnerability` | 无人机易伤 🛸 #5a7a9a（施加时 options 改名 战术弱点标记 ⌖ #66dbe8，:1152） | debuff·增伤 | 有（玩家被标记时） | 每层使受到的所有伤害提高 10%。 | 按 `sourceId` 独立计数（Map），显示层数恒 1；多源并存时取“伤害加成最高”快照；全伤害 ×(1+damageBonusPercent/100)（默认 +10%）+ 攻击方暴击 +critBonusPercent；“非立即移除”只停刷新不清已挂快照 | :490 |
| 14 | `fear` | 实体 😱 #7a5ac8 ／ HUD 😨 #6a5a8a | 控制·减益 | 有（玩家被恐惧时） | 失控地远离恐惧源，每层移速再降 33%（上限 99%）。 | 层数上限 **3**（重复 +1）；移速 ×max(0.01, 1−0.33×层)；被控强制背向逃离；敌方行动被阻断 | :491 |
| 15 | `statusImmune` | 状态免疫 🔰 #5ac8c8 | buff·闸门 | 有（显式 options） | — | 单层取长；持有期间 `addStatusEffect` 拒绝一切其他状态（连 buff 也拒）；永久变体 `applyStatusImmune(Number.MAX_SAFE_INTEGER)` | :492 |
| 16 | `haste` | 加速 💨 #5ac85a | buff·移速 | 有（显式 options） | — | 层数无上限；**每层独立计时（remaining/duration 加法追加）**，到期退一层；移速 ×(1+层×perStackMul)，perStack 默认 0.10（圣辉术 0.25、蛇池术 0.10） | :493 |
| 17 | `weaponHaste` | 命中动能 ➤ #69e7e3 | buff·移速 | 有 | P4040命中后移动速度提高10%；再次命中刷新持续时间。 | 单层；重复命中**只重置**为本次时长（不追加）；移速 ×(1+speedPercent)，默认 0.10 | :494 |
| 18 | `holyRenewal` | 圣光续疗 💚 #7aff9a | buff·HoT | 有 | 每秒恢复最大生命值 1%×层数 的生命值。 | 层数无上限；每层独立计时、到期退一层；1000ms tick 回 `maxHp×healPercent(默认0.01)×层数` | :495 |
| 19 | `holyWard` | 圣佑 🛡️ #ffe7a3 | buff·减伤 | 有 | 持续期间降低受到的最终伤害。 | 单层；同名只刷新/覆盖**不叠乘**，value（承伤乘区，clamp 0.05..1，默认 0.75）以最新施法为准；死亡/≤0hp 拒绝施加 | :496 |
| 20 | `chainSpell` | 链式强化 🔗 #8a7a6a | buff·触发 | 有 | 下次施法的魔法伤害与 MP 消耗按层数提高。 | 层数无上限；每层独立计时（追加式）；每次施法消费全部层：伤害 ×(1+层×chainSpellDamagePercent)、MP 耗 ×(1+层×MpCostPercent)，消费后清状态 | :497 |
| 21 | `chill` | 寒冷 ❄️ #7ab8e0 | debuff·移速 | 有 | 每层降低 5% 移动速度；层数加法叠加，最终乘算。 | 层数无上限（但 **≥20 层 → 转冻结并扣 10 层**）；每层独立计时、到期整体清空；移速 ×max(0.01, 1−层×slowPercent)，slowPercent 取首次施加（配置默认 0.05，暴风雪/冰墙实配 0.035）；冻结期间拒绝叠层（:1234） | :498 |
| 22 | `burn` | 灼伤 🔥 #ff6b35 | debuff·DoT | 有 | 每 0.5 秒受到施法者魔法攻击×0.5 的魔法伤害。 | **每层独立对象**（快照施加者 matk、damageMul、remaining），无上限；500ms tick 逐层 `max(1, floor(matk×damageMul))` 合计后**走 takeDamage（魔法，吃防御）**；各层独立到期 | :499 |
| 23 | `frozen` | 冻结 🧊 #a0d8ff | 控制 | 有 | 无法移动、攻击、使用技能与物品；受到的非魔法伤害提高 50%。 | 单层；时长调用方给（冰系；chill 转化时=本次 chill 时长）；控制等同眩晕+非魔非电承伤 ×1.5；玩家冻结同时置 isStunned；死亡强制清除 | :500 |
| 24 | `petrified` | 石化 🗿 #929292 | 控制 | 有 | 持续期间停在当前动画帧，无法移动或执行任何动作；受到的魔法伤害提高 50%。 | 单层；时长调用方给（冰锥/石系）；动画定格+禁一切+免疫击退；魔/电承伤 ×value(默认1.5)；死亡强制清除 | :501 |
| 25 | `flameArmor` | 灼锋焰甲 🔥 #ff7a3a | buff·光环 | 有 | 攻击附带魔法伤害并迸发火花；每 0.5 秒灼烧周围敌人；武器持续上浮火焰粒子。 | 单层仅刷新；时长=技能 `effect.duration×1000`（12s+lv）；期间物理命中追加魔法附伤 + 每 500ms 半径灼烧；到期触发技能经验结算钩子 | :502 |
| 26 | `electrified` | 感电 ⚡ #b98cff | debuff·增伤(反应) | 有 | 每层使受到的电系伤害提高 3%；叠满 5 层触发过载：眩晕并释放电弧传导。 | 层数无上限、**5 层过载清空**；每层独立计时（追加式）；电系承伤 +3%/层；过载=眩晕1200ms+对 150px 内敌人传导 `floor(20+matk×1.2+int×1.2)` 电伤 | :503 |
| 27 | `marked` | 标记 🎯 #ffd700 | debuff·增伤 | 无（仅施加给敌方；HUD 无字典项） | — | 单层；剩余取长、`value`(全伤害放大, 默认 0.15) 取大；“保留更强标记”规则见 mark-arrow-effect.js | :504 |
| 28 | `camelFright` | 骆驼惊吓 🐪 #c99b5d | debuff(来源侧) | 无（仅施加给敌方攻击者） | — | 单层；重复施加**只刷新且取更强**（value 更大者生效，不叠乘）；持有者（敌方阵营）输出 ×(1−value)，默认 0.10/光环 0.20 | :505 |

> 注①（同 type 多皮肤）：`slow`/`bind`/`droneVulnerability` 通过 options 覆盖显示：
> **slow 桶 6 皮肤**——减速 🐌（默认）、致残 🦴 #8a8a7a（applyCripple :1061-1064）、月蚀迟滞 ☾ #6ebcff（legendary-shotgun.js:119-128，value=配置 slowReduction）、星图迟滞 ✦ #65d8ff（weapon-legendary-lmg.js:195-203）、霜径迟滞 ❄️ #91e9ff（snowfield-lords.js:636-638，value 0.35、≤450ms 逐帧刷新）、镇暴压制 🛡️ #7aa6bd（hamster-riot-squad-ai.js:156-164，value=attackSlowPercent）；**bind 桶 4 皮肤**——束缚 ⛓️（applyBind :1071-1074）、王猎锁定 ♛ #c52c42（legendary-shotgun.js:223-229）、葬潮束缚 ◈ #7b61ff（mythic-shotgun.js:105-131）、时滞锚定 ◉ #54e6ff（weapon-ricochet.js:121-150）；**droneVulnerability 2 皮肤**——无人机易伤 🛸、战术弱点标记 ⌖ #66dbe8（damageable-entity.js:1152）。机制不变，仅名称/图标/颜色；**皮肤名只在条目首建时写入，后续刷新不改名**。

## 1B. HUD 层独有的 10 个状态（status-bar.js:11-41；实体字典无 → 实体侧如走 addStatusEffect 会得 ❓ 回退）

| ID | 图标 | 名称 | 颜色 | desc 原文 | 语义 |
|---|---|---|---|---|---|
| `waxSealSlow` | 🕯️ | 封蜡减速 | #ba9272 | 封蜡诅咒使移动速度降低20%，持续2秒；再次命中只刷新时间，不叠层。 | 诅咒技能（wax-face-mourner）施加到玩家；value 默认 0.20、clamp 0..0.9、时长 skill.slowDurationMs（默认 2000）；只刷新不叠层；**特殊移除语义**：实体 removeStatusEffect('waxSealSlow') 联动清 HUD（damageable-entity.js:670）。定义 src/combat/wax-seal-status.js |
| `marbleHeal` | 🗿 | 大理石守护 | #8a9a8a | 击杀目标后 1 秒内回复生命值。 | 大理石献祭的击杀触发器指示（1000ms），实际回血由玩家侧驱动；直接 StatusBar.addEffect，不进实体 statusEffects（damageable-entity.js:386-420，player/update.js:598） |
| `goddessBless` | ✨ | 女神祝福 | #e8c878 | 本场战斗攻击/防御/移速提升，按场消耗。 | **按场制**：`battleRemaining`（默认 3 场，choice.buff.battles 可配）；atk/matk +15%（goddessBlessAtkPercent）；dungeon-event-system.js:315-353 |
| `demonPrayer` | 🔥 | 恶魔祈祷 | #9a3a3a | 攻击力大幅提升的恶魔交易，伴随代价。 | **永久文本**：`persistent:true, durationText:'持续至本次地牢结束'`；atk/matk +33%（demonBuffAtkPercent）；dungeon-event-system.js:359-397 |
| `tributeSnowLotus` | 🪷 | 雪莲祝福 | #9ad0ff | 本次地牢获得经验 +25%。 | persistent，durationText `跟随献祭倒计时`（tribute-effects.js:348-400） |
| `tributeGinseng` | 🌿 | 人参回气 | #6a9a5a | 本次地牢击杀目标后 1 秒内回复最大魔法值 5%。 | persistent 指示；触发器实体为 `ginsengHeal`（见 1C） |
| `tributePeach` | 🍑 | 蟠桃续命 | #e8a06a | 本次地牢死亡后 3 秒以 30% 最大生命原地复活一次。 | persistent；消耗后指示消失（syncTributeBuffs 条件刷新） |
| `tributeDiamond` | 💎 | 金刚不坏 | #7ab0e0 | 单次受到的伤害不超过最大生命值的 15%。 | persistent；承伤上限在 takeDamage 数据侧消费 |
| `tributeMoonstone` | 🌙 | 月影庇护 | #b0a0e0 | 进入战斗获得无敌；Boss/精英战斗中物理魔法伤害 +5%。 | persistent + `_moonshadowTimer` 隐藏计时 |
| `tributePhilosopher` | 🪨 | 点石成金 | #e0c060 | 获得随机传说祭品（若为传说祭品则额外再得一份）。 | persistent 指示，效果为拾取时立即结算型 |

## 1C. 未注册但会出现在状态栏的 ID（依赖显式 options；tooltip 走 desc 回退文案）

| ID | 图标/色 | 名称 | 语义 | 定义处 |
|---|---|---|---|---|
| `ginsengHeal` | 🌿 #6a9a5a | 人参回气 | 击杀后 1000ms 回复窗口（每窗口回 5% 最大 MP）；直接 StatusBar.addEffect | damageable-entity.js:410-416 |
| `tributeBloodVine` | 🩸 #d06060 | 血藤寄生 | persistent；友军击杀吸血（friendlyLifestealPercent，承伤处结算） | tribute-effects.js:355 |
| `tributeWolfBanner` | 🚩 #c0a060 | 狼烟结界 | persistent；部队光环移速+（friendlyAuraMoveSpeedPercent，movement-system 消费） | tribute-effects.js:356 |
| `tributeJadeTwins` | 🗿 #7ad0a0 | 双身募兵 | persistent；招募数量 ×recruitCountMul | tribute-effects.js:357 |
| `tributeAstrolabe` | 🌟 #e8d060 | 风调雨顺 | persistent；生产资源 +productionResourcePercent% | tribute-effects.js:358 |
| `world122Tribute_<key>`（动态族） | 物品 icon，缺省 🕯️；色 #7ab8ff | 位面献祭·<物品名> | 122 世界祭坛；30 分钟现实倒计时（durationText 实时刷新） | world122-tribute-system.js:223-242 |

## 1D. 地牢事件 buff 全量目录（66 处出现 / 64 种参数组合 / 63 个唯一 ID）

来源 `src/world/dungeon-event-definitions.js`；施加通道 `_applyTemporaryBuff`（:1901-1935）。**全部 `durationBattles: 3`（按场消耗）**；数值字段仅 `atkPercent/matkPercent/defPercent/moveSpeedPercent` 四种；成功块施加 = success.buff，失败块 = fail.buff。

| ID | 名称 | 图标 | 颜色 | 数值 | 定义行 | 触发 |
|---|---|---|---|---|---|---|
| foremanDebtMark | 工头债印 | 📒 | #7a5a3a | matk −15% | :350 | fail |
| minersGratitude | 矿工谢意 | ⛏ | #c6a56b | def +10% | :351 | success |
| minersCadence | 掘进节拍 | ⚙️ | #b48a5a | atk +10%, 移速 +10% | :378 | success |
| deepShaftEcho | 深井回声 | 🕳️ | #52515f | def −15% | :386 | fail |
| reedLament | 芦苇哀鸣 | 🌾 | #8b9670 | 移速 −15% | :417 | fail |
| bogHunterInstinct | 沼猎直觉 | 🏹 | #a59a62 | atk +10%, 移速 +10% | :489 | success |
| hunterBurden | 猎手重负 | 🦴 | #786b55 | def −10%, 移速 −10% | :490 | fail |
| druidShelter | 林神庇护 | 🌿 | #65a86f | def +10% | :501 | success |
| swampWhisper | 沼语侵扰 | 🌀 | #63745b | matk −10% | :502 | fail |
| wildSap | 野性树液 | 🍂 | #91a34f | atk +10% | :506 | success |
| marshGasNumbness | 沼气麻痹 | ☁️ | #9a9b45 | 移速 −20% | :524 | fail |
| livingRootWard | 活根护符 | 🌱 | #6f9550 | def +15%, matk +10% | :540 | success |
| blackwaterChill | 黑水寒意 | 🕯️ | #55777c | atk −10%, matk −10% | :553 | fail |
| waterloggedArmor | 浸水护甲 | 💧 | #4c6f78 | def −15%, 移速 −10% | :558 | fail |
| graveMurmur | 墓洲低语 | 🪦 | #7d8862 | matk −10% | :570 | fail |
| frogBoneCurse | 蛙骨诅咒 | 🦴 | #7f8b56 | def −10% | :587 | fail |
| witchDistillate | 女巫馏液 | ⚗️ | #8d75a6 | matk +15% | :620 | success |
| bogWitchTonic | 沼巫强壮剂 | 🥄 | #778f5a | atk +10%, def +10% | :625 | success |
| failedWitchBrew | 失败药剂 | 🧪 | #66576f | def −15%, 移速 −15% | :626 | fail |
| crocodileHideWard | 鳄神厚皮 | 🐊 | #536d4f | def +15% | :642 | success |
| ancientSpell | 古代咒语 | 🔮 | #8a7aff | matk +25% | :704 | success |
| bloodFury | 血怒 | 🩸 | #aa3333 | atk +20% | :761 | success |
| cursedArmorShell | 诅咒板甲 | 🛡️ | #7a7a7a | def +20% | :863 | success |
| armorCurse | 板甲诅咒 | 💀 | #5a5a5a | def −20% | :875 | fail |
| steadyMind | 稳定心神 | 🍃 | #7abaff | 移速 +15% | :943 | success |
| madVision | 疯狂幻象 | 👁️ | #8a5a9a | 移速 −25% | :1134 | fail |
| steadyMind（第2档） | 稳定心神 | 🍃 | #7abaff | 移速 +25% | :1122, :1156 | success |
| madVision（重复定义，同值） | 疯狂幻象 | 👁️ | #8a5a9a | 移速 −25% | :1168 | fail |
| corpseWaxSeal | 尸蜡封层 | 🕯️ | #c8b997 | def +15% | :1215 | success |
| waxStiffness | 尸蜡僵结 | 🕯️ | #81745f | 移速 −20% | :1216 | fail |
| funeralTempo | 送葬节拍 | 🎼 | #9aa7b5 | atk +20%, matk +20% | :1244 | success |
| discordantEcho | 失谐回声 | 🎵 | #746879 | matk −20% | :1250 | fail |
| plagueAntiserum | 净化血清 | 🧬 | #78a995 | def +20% | :1261 | success |
| plagueExposure | 瘟疫暴露 | ☣️ | #76834f | atk −20%, def −20%, 移速 −15% | :1267 | fail |
| frostDisorientation | 霜途迷向 | 🧭 | #8aa8ba | 移速 −15% | :1279 | fail |
| iceBridgePoise | 冰桥定势 | 🧊 | #83b4ca | def +15%, 移速 +15% | :1338 | success |
| iceBridgeNumbness | 寒桥麻木 | 🥶 | #6d91a8 | 移速 −15% | :1339 | fail |
| iceBridgeDetourChill | 绕路失温 | 🥶 | #6d91a8 | 移速 −10% | :1346 | fail |
| frostberryVigor | 霜莓活力 | 🫐 | #668bb5 | def +15% | :1390 | success |
| frostberryChill | 霜莓寒毒 | 🫐 | #526b92 | 移速 −15% | :1391 | fail |
| whiteStagStride | 白鹿轻步 | 🦌 | #b7d7e4 | 移速 +20% | :1418 | success |
| whiteStagMercy | 白鹿善意 | 🦌 | #b7d7e4 | def +10%, 移速 +10% | :1430 | success |
| auroraCadence | 极光律动 | 🌌 | #77c6d7 | matk +15%, 移速 +15% | :1441 | success |
| auroraFrostbite | 极光冻伤 | 💠 | #7199b8 | 移速 −15% | :1452 | fail |
| shroudedAurora | 极光残扰 | 🌌 | #718da9 | matk −10% | :1460 | fail |
| avalancheBrace | 抗崩架势 | 🏔️ | #879ba7 | def +20% | :1481 | success |
| crevasseWhispers | 冰隙低语 | 🗣️ | #7796aa | matk −15%, 移速 −15% | :1528 | fail |
| glacierLungs | 冰川吐息 | 🌬️ | #6fa0bd | def +20% | :1537 | success |
| crevasseNumbness | 冰隙失温 | 🥶 | #63869c | 移速 −20% | :1538 | fail |
| crevasseDetourNumbness | 冰隙寒侵 | 🌬️ | #63869c | 移速 −15% | :1545 | fail |
| frozenSanctuary | 寒堂圣佑 | ❄️ | #b7dce8 | def +20%, matk +20% | :1556 | success |
| rejectedPrayer | 冰堂拒斥 | 🕯️ | #778ca0 | matk −20% | :1557 | fail |
| reliquaryBurden | 圣匣重压 | ⛓️ | #70889a | 移速 −20% | :1567 | fail |
| drenchedInIcewater | 冰水浸身 | 💧 | #557f9a | 移速 −20% | :1579 | fail |
| signalFlamePace | 烽火引路 | 🔥 | #d7a76b | 移速 +20% | :1606 | success |
| blizzardFireguard | 暴雪火卫 | 🔥 | #cb8e64 | def +20% | :1611 | success |
| shutterBruise | 风板挫伤 | 🌀 | #6e8798 | atk −15%, 移速 −15% | :1617 | fail |
| frostSpiritMark | 寒灵印记 | 👻 | #75b9d2 | matk +20% | :1634 | success |
| frostSpiritRage | 寒灵震慑 | 👻 | #637e9b | matk −20% | :1635 | fail |
| crystalBackflow | 寒晶逆流 | 💎 | #658da7 | atk −20%, def −20% | :1645 | fail |
| frostSpiritRejection | 寒灵拒斥 | 👻 | #637e9b | matk −15% | :1653 | fail |
| auroraOmen | 极光战兆 | 🌠 | #8cc8d8 | atk +20%, matk +20% | :1669 | success |
| falseOmen | 伪星兆 | 🌑 | #686f91 | atk −20%, matk −20% | :1670 | fail |
| starfallFracture | 坠星震裂 | ☄️ | #747fa0 | def −20% | :1675 | fail |
| observatoryFrostFracture | 星镜霜裂 | ☄️ | #747fa0 | def −15% | :1682 | fail |

（数值为 ±百分比；同一 ID 多档（steadyMind）按事件独立定义。）

## 1E. 总数与分类汇总（精确）

| 集合 | 总数 | buff | debuff | 其中控制 |
|---|---|---|---|---|
| 实体层注册 28 | 28 | 10（buff, shield, inspire, statusImmune, haste, weaponHaste, holyRenewal, holyWard, chainSpell, flameArmor） | 18 | 5（stun/frozen/petrified/bind/fear） |
| HUD 层独有 10 | 10 | 10（goddessBless, demonPrayer, 6×tribute, marbleHeal 计增益；waxSealSlow 计减益 → 实为 9 buff + 1 debuff） | 1 | — |
| 未注册显示 ID 5 | 5 | 5 | 0 | — |
| 地牢事件 63 唯一 | 63 | 28 | 35 | — |
| **静态合计（并集口径）** | **106** | **52** | **54** | **5（另 electrified 过载衍生 stun）** |
| 动态族 world122Tribute_* | 不定（随 122 物品表） | 全部（增益） | 0 | — |

- HUD 层独有修正明细：buff = marbleHeal, goddessBless, demonPrayer, tributeSnowLotus, tributeGinseng, tributePeach, tributeDiamond, tributeMoonstone, tributePhilosopher（9）；debuff = waxSealSlow（1）。上表 10/0 行应读作 9+1。
- 校验：1A 内 buff 10 + 1B 的 9 + 1C 的 5 = 24 buff（注册+静态未注册）+ 地牢 28 = **52**；debuff 1A 18 + 1B 1 = 19 + 地牢 35 = **54**；24+19=43 静态核心 + 63 地牢 = 106。
- 两个注册但**从不被施加**的占位 ID：`buff`（仅遗留清除引用）、`shield`（无任何调用）。

## 2. §6 图标资源清点

**结论：buff 图标 100% 为 emoji/文本 glyph，经 `<span class="status-effect-icon">${icon}</span>` 文本节点渲染；状态栏不存在任何 png/`<img>` 图标。**

### 2.1 全量 emoji/文本图标 → 使用处
| glyph | 用于（type · 显示名） |
|---|---|
| 💫 | stun 眩晕 |
| ☠️ | poison 中毒 |
| ☣ | minePoison 矿毒 |
| 🐌 | slow 减速（默认） |
| ⛓️ | bind 束缚（默认）；⛓️ 另用于 reliquaryBurden 圣匣重压 |
| ✨ | buff 增益（占位）；goddessBless 女神祝福 |
| 🛡️ | shield 护盾（占位）；holyWard 圣佑；cursedArmorShell 诅咒板甲 |
| 🩸 | bleed 流血；bloodFury 血怒；tributeBloodVine 血藤寄生 |
| 🧪 | corrosion 腐蚀；failedWitchBrew 失败药剂 |
| 📣 | inspire 激励 |
| 🔮 | magicVulnerability 魔力易伤；ancientSpell 古代咒语 |
| ✦ | magicResistanceShred 魔抗蚀刻（实体层） |
| 🛸 | droneVulnerability 无人机易伤（默认） |
| ⌖ | droneVulnerability 战术弱点标记（options 覆盖） |
| 😨 | fear 恐惧（HUD 层） |
| 😱 | fear 恐惧（实体层 + 漂浮字 `'😱 恐惧！'` :888） |
| 🔰 | statusImmune 状态免疫 |
| 💨 | haste 加速 |
| ➤ | weaponHaste 命中动能 |
| 💚 | holyRenewal 圣光续疗 |
| 🔗 | chainSpell 链式强化 |
| ❄️ | chill 寒冷；frozenSanctuary 寒堂圣佑 |
| 🔥 | burn 灼烧；flameArmor 灼锋焰甲；demonPrayer 恶魔祈祷；signalFlamePace/blizzardFireguard |
| 🧊 | frozen 冻结；iceBridgePoise 冰桥定势 |
| 🗿 | petrified 石化；marbleHeal 大理石守护；tributeJadeTwins 双身募兵 |
| ⚡ | electrified 感电 |
| 🎯 | marked 标记 |
| 🐪 | camelFright 骆驼惊吓 |
| 🕯️ | waxSealSlow 封蜡减速；world122 祭品缺省图标；blackwaterChill/corpseWaxSeal/waxStiffness/rejectedPrayer |
| 🦴 | 致残（options）；hunterBurden；frogBoneCurse |
| 🌿 | tributeGinseng/ginsengHeal 人参回气；druidShelter 林神庇护 |
| 🪷 | tributeSnowLotus 雪莲祝福 |
| 🍑 | tributePeach 蟠桃续命 |
| 💎 | tributeDiamond 金刚不坏；crystalBackflow 寒晶逆流 |
| 🌙 | tributeMoonstone 月影庇护 |
| 🪨 | tributePhilosopher 点石成金 |
| 🚩 | tributeWolfBanner 狼烟结界 |
| 🌟 | tributeAstrolabe 风调雨顺 |
| 📒⛏⚙️🕳️🌾🏹🌀☁️🌱💧🪦⚗️🥄🐊👁️🎼🎵🧬☣️🧭🥶🫐🦌🌌💠🏔️🗣️🌬️👻🌠🌑☄️ | 地牢事件 buff 各自图标（见 1D 表逐行） |
| ❓ | **未知 type 回退图标**（entity :507 / bar :133） |

### 2.2 无 png 的佐证
- `StatusBar.render()` 模板（status-bar.js:323-329）只插值 `effect.icon` 文本；全项目 grep 无 buff 相关 `<img>`。
- `assets/ui/icons/status.png` **存在但与 buff 栏无关**：它是侧边菜单“角色状态 (CapsLock)”面板按钮图标（`src/ui/panels/hud-panels-misc.js:18`；遗留模板 `ui/components/hud-layer.html:206` 同引用）。迁移时不要把它当状态图标。
- 文本型 glyph 风险点：`☣`（U+2623 无变体选择符，Windows 下黑白）、`⛏`/`⚗`（同上）、`➤`/`✦`/`⌖`/`◈`/`◉`/`☾`（几何符号，非 emoji，UE 侧需替换为等价字形或图集）。
