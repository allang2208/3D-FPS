# 卷二 · §2 逐状态机制实现（46 条：2.1–2.38 状态机制 + 2.39–2.46 系统级）

行号均在 `E:\无尽轮回\长期备份\2026-7-13-1\game-dev`。缩写：**DE** = `src/entities/damageable-entity.js`，**SB** = `src/ui/status-bar.js`，**DF** = `src/combat/defense-formula.js`，**ODM** = `src/combat/outgoing-damage-modifiers.js`，**DP** = `src/combat/damage-pipeline.js`。

通用叠加规则（addStatusEffect，DE:513-523）——**“同类型”一律指同 ID 单条目**：
```js
const existing = this.statusEffects.find(e => e.type === type);
if (existing) {
    existing.remaining = Math.max(existing.remaining, duration);   // 时长取长
    existing.duration  = Math.max(existing.duration, duration);
    if (options.stacks !== undefined) existing.stacks = options.stacks;  // 层数直接覆盖
    if (options.value !== undefined)
        existing.value = Math.max(existing.value ?? 0, options.value);   // 数值取大（2026-08-17）
    return existing;
}
```
`stacks`/`value` 仅是**显示与消费参数字段**，真正的堆叠语义在各 `applyXxx` 里用专用 `_xxxStacks` 字段实现（见各节）。

## 2.1 stun 眩晕（控制）
- 施加：`applyStun(duration)` DE:812-823 → `addStatusEffect('stun', duration)` + `_cancelActionsForStun()` + 眩晕待机动画 + 漂浮字 `💫 眩晕！`。
- 动作中断：DE:825-845 `_cancelActionsForStun` 清主/副手 weaponAnim、攻击预警 `_attackTelegraphTimer`、`_attackAnimTimer`、`_frozenForCast`；玩家覆写 `subsystems.js:2874-2890`（先判 `_isDead||_dodgeInvincible` 则免疫，再 `isStunned=true; stunTimer=duration` + `_cancelAllActionsForStun()` :2893+，并 `StatusBar.addEffect('stun',...)` 记 `_stunEffectId`）。
- 消费：玩家 `player/update.js:84-104` stunTimer 递减期间强制退出防御、只更新子系统后 return（禁移动/攻击/技能/物品）；敌人 `enemy.js:629-633 isCombatActionBlocked()`。
- 特例：`applyStunExtend(base, extend)` DE:851-866 —— 已有眩晕则 `remaining += extend`（**加法延长**，电系改造用），否则加 `base+extend`。
- 普攻眩晕豁免（隐藏控制规则）：`data/combat-config.json` `basicAttackStun.lordResistance`（:20-30，baseChance 0.2 + (体质−30)×0.0125，夹 0.15..0.55，豁免闪光 300ms）；消费 `src/combat/attack.js:67-104`；`rank==='boss'` 完全免疫普攻眩晕。

## 2.2 slow 减速
- 玩家承伤侧消费：`update.js:343` `if (hasStatusEffect('slow')) targetSpeed *= 0.5;`（硬编码 50%，不看 value）。
- 敌人消费：`src/systems/movement-system.js:1010-1017`：
```js
const configuredSlow = slowEffect?.value == null ? 0.5 : Number(slowEffect.value);
const slowReduction = slowEffect ? Math.min(0.9, Math.max(0, configuredSlow)) : 0;
const slowMul = 1 - slowReduction;
```
  即 **value=“减速百分比”**（0.5 → ×0.5），夹 0..0.9，默认 0.5。武器皮肤（月蚀迟滞/星图迟滞）传各自配置的 value。
- 施加：`applyCripple(duration, opts)` DE:1057-1068（type 仍 'slow'，显示 致残🦴#8a8a7a）：**statusImmune 门后先直调 StatusBar.addEffect(:1060-1061，无阵营守卫)再入实体数组(:1064)**；`opts.silent` 抑制飘字（毒液瓶用 silent 致残）。玩家攻击挂点 `attack.js:397-398/:463-464` config.crippleDuration。⚠️ 串台后果：玩家打怪挂致残时玩家自己栏会出现「致残」条目（卷四 §4.0）。

## 2.3 bind 束缚（软控-禁足）
- 施加：`applyBind(duration)` DE:1069-1078（玩家目标 → StatusBar 束缚⛓️；实体数组同 type）。
- 玩家消费：移速 `update.js:345 targetSpeed = 0`（覆盖式归零）；闪避禁用 `subsystems.js:1136`（triggerDodge 前置检查）。
- 敌人消费：`movement-system.js:167` 移动阻断名单 `['stun','frozen','petrified','bind','fear']`；:246 bind 时直接清输入位移。

## 2.4 fear 恐惧（控制）
- 施加：`applyFear(duration, source)` DE:874-890；层数 `stacks = min((existing.stacks||1)+1, 3)`（**上限 3**）；存 `_fearSource`；玩家镜像 StatusBar（带层数）；漂浮字 `😱 恐惧！`。
- 移速：`getFearSpeedMul()` DE:892-896 `max(0.01, 1 - 0.33 × stacks)`。
- 行为：玩家被强制操控——`update.js:124-157` 恐惧分支把输入向量改写为**背离 `_fearSource`** 的方向并按 getFearSpeedMul 限速（仍算“在动”，不是定身）；敌人 `isCombatActionBlocked` 含 fear（enemy.js:632）→ 完全停止攻击/施法。

## 2.5 petrified 石化（控制）
- 施加：`applyPetrify(duration, options)` DE:613-645：`addStatusEffect('petrified', duration, { stacks:1, value: options.magicDamageTakenMultiplier ?? 1.5 })`（:620-625）+ vx/vy=0 + 玩家镜像 + 漂浮字 `🗿 石化！`。
- 行为：定格当前动画帧（渲染冻结）、禁一切行动与格挡/闪避、免疫击退（DE:459 `hasStatusEffect('petrified') return`）；`enemy.js:648` 石化即时打断已排程动作。
- 承伤乘区：DE:122-129 **魔法/电系 ×value(默认1.5)**：`floor(baseDamage * Math.max(1, Number(petrified?.value) || 1.5))`。
- 死亡清理：DE:346-347（`_onDeath` 中 removeStatusEffect('petrified'/'frozen') + `_freezeStacks=0`），伙伴 companion.js:271-272 同。

## 2.6 frozen 冻结（控制 + 增伤）
- 施加：`applyFreeze(duration=3000)` DE:1296-1327：statusImmune 门禁 → `_cancelAllActionsForStun()/_cancelActionsForStun()` → `_freezeStacks=1; _freezeTimer=duration` → **玩家额外 `isStunned=true; stunTimer=max(stunTimer, duration)`**（:1307-1309）→ removeStatusEffect('frozen') 再 add（**新条目置顶重播动画**，:1312-1314）→ StatusBar 镜像 → 音效 `assets/sounds/skills/frozn.mp3`。
- 承伤乘区：DE:154-157 **非魔法非电系 ×1.5**（`damageType !== 'magic' && !== 'electric'`）。
- 计时：`_updateFreeze` DE:1282-1294 单一 `_freezeTimer`，归零清 frozen 状态与 HUD。`isFrozen()` :1329-1331。
- 与寒冷互斥：chill 期间被冻结 → chill 继续独立衰减；冻结期间 applyChill 直接 return（DE:1234）。

## 2.7 chill 寒冷（可转冻结）
- 施加：`applyChill(stacks=1, duration=3000, slowPercent=0.05)` DE:1231-1279：
```js
if (this.hasStatusEffect('frozen')) return;            // 冻结期间不再叠层 :1234
if (this._chillStacks > 0) { this._chillStacks += stacks; this._chillTimer += duration; }
else { this._chillStacks = stacks; this._chillTimer = duration; this._chillSlowPercent = slowPercent; } // slowPercent 首层定值
if (this._chillStacks >= 20) {                          // 20 层 → 冻结转化 :1244-1257
    this._chillStacks -= 10; if (<0) = 0;
    this.applyFreeze(duration);                         // 冻结时长 = 本次寒冷持续时间
    if (this._chillStacks === 0) { 清计时、removeStatusEffect('chill')、清 HUD }
}
```
- 计时：`_updateChill` DE:1219-1230 **单一共享 `_chillTimer`**（与 poison 的逐层衰减不同——新施加整体续 `_chillTimer += duration`，归零一次清空全部层）。
- 移速：`getChillSpeedMul()` DE:1333-1337 `max(0.01, 1 − _chillStacks × (_chillSlowPercent||0.05))`；玩家链 `update.js:382-383`；敌人链 `movement-system.js:1005-1008`（chillMul）。
- HUD/数组同步：DE:1269-1279（effect.stacks/remaining/duration=max(旧, 新)）。

## 2.8 burn 灼伤（DoT，逐层独立源快照）
- 施加：`applyBurn(source, stacks=1, duration=3000, damageMul=0.5, tickMs=500)` DE:1374-1398：每层 push `{ source, matk: source.data.matk（施加瞬间快照）, damageMul, remaining: duration }` 入 `_burnStacks[]`；`_burnTickMs = tickMs`（首个 tick 400ms 内起效，取 tickMs）。
- tick：`_updateBurn` DE:1340-1373：每 `_burnTickMs`(默认 **500ms**) 对**所有存活层**求和 `Σ max(1, floor(stack.matk × stack.damageMul))`，一次 `takeDamage(total, source, 'magic', false)` —— **走完整防御公式的魔法伤害**（吃 mdef/魔抗蚀刻/魔力易伤/石化加成）。来源死亡后层照常结算（matk 已快照）。
- 消退：每层 `remaining -= dt` 独立 filter（DE:1343-1345），层间互不影响；全空时 removeStatusEffect('burn') + 清 HUD。
- damageMul 真源：meteor 爆炸 0.5 / 熔岩 0.3（skills.json:1063/1066）；火球/吊坠 `ce.fireBurnDamageMul`（bolt-skill-system.js:500-514）。

## 2.9 poison 中毒（DoT，固定值直扣）
- 施加：`applyPoison(stacks)` DE:929-938：`_poisonStacks += stacks; _poisonTimer = 5000;`（**每次施加把共享消退计时重置回 5000**），`_poisonTickTimer<=0` 时置 1000；漂浮字 `☠️ 中毒 +N层` #39ff14。
- tick：`_updatePoison` DE:898-927 每 **1000ms** `this.hp -= _poisonStacks`（**固定伤害、直接扣血、不经 takeDamage、不吃任何防御/加成**；玩家覆写在 subsystems.js:571+，走 data.hp 口径），归零调用 onDeath。
- 消退：共享 `_poisonTimer` 每 5000ms 退 **1 层**并重置计时；退光才清 HUD（DE:916-927）。→ 语义：最后一层获得 5s，其余各层再各撑 5s。
- 施加入口见卷三（喷吐/毒瓶/附魔/改造）。

## 2.10 minePoison 矿毒（环境 DoT）
- 驱动：`src/world/world126-weather-runtime.js` `_updatePoisonGas` :258-320（矿洞地图）。毒区参数在 `data/game-config.json` `poisonGas`：`exposureMs 2000 / tickMs 1000 / damageRatio 0.005 / lingerMs 3000`；区域生成 max4、半径 260 起步 5s 成长、存活 40s、间隔 12s。
- 机制：暴露满 2000ms → `entity.addStatusEffect('minePoison', cfg.lingerMs)`（:300）；玩家镜像 `StatusBar.addEffect('minePoison', lingerMs)`（:303）且**身处区内时把 HUD remaining 持续钉在 lingerMs**（:304-305，出区后才真实倒数——“残留 3 秒”）。
- tick：感染期间每 1000ms `DamagePipeline.applyHit(..., { damage: Math.max(0.1, maxHp×0.005), damageType:'magic', isMelee:false })`（:310-315，按最大生命 0.5% 走防御）。
- 免疫：`_isZombieFamily`、建筑/防御塔、`statusImmune`（:284/:298 直接 remove）。可被圣所净化（CLEANSE_TYPES 含之）。

## 2.11 bleed 流血（DoT，当前生命百分比直扣）
- 施加：`applyBleeding(stacks)` DE:1079-1089：statusImmune 门 → `_bleedStacks += stacks; _bleedTimer = 10000;` tickTimer<=0 时置 1000；**DE:1085 无条件 `StatusBar.addEffect('bleed', 10000, {stacks})`——全项目唯一连 `if (StatusBar)` 都不判的镜像点，无阵营守卫**（源码逐行复核）。后果：玩家（旋风斩流血改造、镂空工艺）给怪挂流血时，怪侧层数会直接写进玩家状态栏条目（同类 max 合并、层数覆盖）；到期由 `_updateBleed` DE:1023-1055 每 10s 减一层并回写 `StatusBar.addEffect('bleed',10000,{stacks})`（:1047）。
- tick：`_updateBleed` DE:1023-1039 每 **1000ms** `dmg = max(1, floor(this.hp × 0.01 × _bleedStacks))`，**直接扣当前 HP，不吃防御**；飘 `-N` #9a3a3a；致死触发 onDeath。
- 消退：`_bleedTimer` 每 10000ms 退 1 层重置（每层最多 10s）。

## 2.12 corrosion 腐蚀（防御削减 debuff）
- 施加：`applyCorrosion(stacks=1, duration=5000, defenseReductionPerStack=0.05)` DE:968-1005：`_corrosionStacks += stacks`；`_corrosionDuration = max(1, duration)`；**`_corrosionDefenseReductionPerStack` 取历史最大值**（:974-977）；注册/刷新 statusEffects+HUD（stacks 名 `腐蚀 xN`）。
- 数值消费：**只削物理防御**，接入点 DF:19：
```js
if (!magic) def = Math.max(0, Math.floor(def * (target.getCorrosionDefenseMul?.() ?? 1)));
```
  `getCorrosionDefenseMul()` DE:1007-1012 `max(0, 1 − stacks × perStack(默认0.05))`。魔法/电系完全不吃腐蚀。
- 消退：`_updateCorrosion` DE:940-967 共享 `_corrosionTimer`（初值=duration）到期退 1 层并重置；通用 `updateStatusEffects` **显式跳过 corrosion**（DE:683）防止双计时。`clearCorrosion()` DE:1013-1021（净化入口）。
- 施加入口：毒液/酸液怪攻击、腐蚀地块（见卷三）。

## 2.13 magicVulnerability 魔力易伤
- 施加：`applyMagicVulnerability(stacks)` DE:1099-1106：`_magicVulnerabilityStacks += stacks; _magicVulnerabilityTimer = 5000;`（共享消退计时）。漂浮字 `🔮 魔力易伤 +N层`。
- 消费：DE:117-121 `magic|electric` 伤害 `×(1 + stacks×0.05)`，可被 `hitContext.ignoreMagicVulnerability === true` 绕过（特定来源防双算）。
- 消退：每 5000ms 退 1 层（DE:1091-1098）。
- 注：**该 apply 不写 statusEffects[]**，纯字段驱动；HUD 字典项仅存在于历史/RTS 面板（`STATUS_META` 有它）。迁移时机制以字段为准。

## 2.14 magicResistanceShred 魔抗蚀刻
- 施加：`applyMagicResistanceShred(ratio, duration, source)` DE:575-587：value = clamp 0..0.95；死亡/0血/免疫拒绝；`addStatusEffect('magicResistanceShred', durationMs, {value})` → 通用规则**时长取长、value 取大**（不叠层）；记录最后 source。
- 消费：DF:8-10（仅 magic/electric）：
```js
if (magic) {
    const shred = Math.max(0, Math.min(0.95, Number(target.getMagicResistanceShredRatio?.()) || 0));
    def = Math.floor(def * (1 - shred));
}
```
- 唯一施加入口：盾牌弹反反击改造 arcaneRetort → `shield-system.js:426-432 attacker.applyMagicResistanceShred(retort.magicResistanceShred, retort.shredDurationMs, this.player)`（**打在敌人身上**，所以玩家栏不显示）。

## 2.15 droneVulnerability 无人机易伤（多源独立标记 + 最强快照）
- 施加：`applyDroneVulnerability(options)` DE:1136-1157：以 `sourceId` 为键写入 `_droneVulnerabilitySources: Map<sourceId, {sourceId, damageBonusPercent(默认10), critBonusPercent(默认10), owner, remaining(默认2000)}>`；数字入参兼容旧语义 `{sourceId:'legacy-drone', 10, 10, 2000}`；实体显示名 **战术弱点标记 ⌖ #66dbe8**（DE:1152）；首挂漂浮字“战术锁定”。
- 更新/消费：`_updateDroneVulnerability` DE:1108-1135：每源独立倒计时删过期源；存活源按 `damageBonusPercent` 再 `critBonusPercent` **降序排序取最强作当前快照** `_droneVulnerabilityData`（后到但更强者即时接管）；`stacks=1`；总 `remaining=max(各源)`。
- 伤害：DE:140-144 受 **所有伤害** ×(1 + damageBonusPercent/100)，受益阵营白名单 `DRONE_BENEFICIARY_FACTIONS`（玩家/同伴/友军，部署快照共享）；另攻击方暴击 +critBonusPercent（DE:196-198）。玩家侧同款消费 `subsystems.js:266-274`。
- 移除：`removeDroneVulnerability(sourceId, {immediate})` DE:1158-1163 —— 不传 sourceId 清全部；`immediate:false` 只停止续期，已挂快照自然残留至到期。无人机塔 HUD：`subsystems.js:346 StatusBar.addEffect('droneVulnerability', 999999)`（无限时长显示）。
- 免疫：死亡/0hp/statusImmune 拒绝（DE:1137）。

## 2.16 marked 标记（黑匠能力）
- 施加：`src/combat/mark-arrow-effect.js tryApplyMarkArrow`（:19-40）：按铁匠铺 ability `mark_arrow` 概率触发；已有 marked 时 **value 更大者保留**（preserveStronger），否则只刷时长；`addStatusEffect('marked', duration, { value: damageAmplify })`（只挂敌人，玩家栏不显示）。
- 消费：DE:243-247 `baseDamage = floor(baseDamage × (1 + (marked.value ?? 0.15)))`（注释：默认 15%）。射手 AI 入口 `ai/hamster-scout-ai.js:400`、`ai/hamster-musketeer-ai.js:291`。

## 2.17 camelFright 骆驼惊吓（来源侧输出削减）
- 施加：`applyCamelFright(duration, reduction=0.1)` DE:648+：同类刷新**取更强 value**，不叠层、不进 statusEffects 之外的流程、无 HUD（目标恒为敌方攻击者）。
- 消费：ODM:42-48（唯一入口，source 侧）：
```js
if (source && source._faction === 'enemy' && typeof source.hasStatusEffect === 'function'
    && source.hasStatusEffect('camelFright')) {
    const effect = source.statusEffects.find(e => e.type === 'camelFright');
    const value = Math.max(0, Math.min(0.9, Number(effect?.value) || 0));
    multiplier *= (1 - value);
}
```
  随后统一 `applyOutgoingDamageModifiers` ODM:53-58 `max(1, floor(amount × multiplier))`（在 DE:223 消费）。

## 2.18 holyWard 圣佑（最终承伤乘区）
- 施加：`applyHolyWard(duration, damageTakenMultiplier=0.75)` DE:548-572：死亡/0hp/时长≤0 拒绝；multiplier clamp **0.05..1**；“同名效果只刷新/覆盖，不叠乘；最新施法值是唯一真源”（DE:563-564）；玩家镜像（先 remove 旧 `_holyWardEffectId` 再加）。
- 消费：`applyHolyWardDamageMultiplier` DE:597-605 `floor(damage × clamp(value,0.05,1))`，在 DE:249 —— **防御、全部易伤、格挡之后、女墙/传奇盾庇护之前**的统一“最终承伤倍率”区。伙伴 companion.js:218-260 同式独立实现。
- 来源：大主教（holy-light/holy-judgment aiConfig `holyWardDurationMs`/`holyWardDamageTakenMultiplier`，holy-light-system.js:100-104/157-158）。

## 2.19 holyRenewal 圣光续疗（HoT）
- 施加：`applyHolyRenewal(stacks, duration, healPercent=0.01)` DE:1189-1218：`_holyRenewalStacks += stacks`；每层独立计时（追加式，DE:1204 附近 push）；statusEffects 与 HUD 同步（DE:1209/:1212）。
- tick：`_updateHolyRenewal` DE:1170-1188 每 **1000ms** 回 `maxHp × healPercent × 层数`（封顶 maxHp）；每 5s 语义为逐层消退（与中毒同族的“每层独立消退计时”——DE:1190-1200 计时组）。
- 来源：圣光技能 + 改造 `holyLightHoTStacks/holyLightHoTSeconds`（holy-light-system.js:271-277）。

## 2.20 haste 加速（可叠层限时）
- 施加：`applyHaste(duration, {perStackMul|speedMul})` DE:743-765：**stacks+1，`remaining += duration`、`duration += duration`（时长按来源追加）**；`perStackMul` 兼容式 `speedMul ? speedMul-1 : 0.10`；仅首次写 `_hastePerStackMul`（后来的不同 perStack 被忽略——已知怪癖）；玩家镜像 SB（DE:759-764）。
- 消费：玩家 `update.js:373-376` `targetSpeed *= (1 + 0.10 × stacks)`（基类字段 `_hasteStacks/_hastePerStackMul`）；到期钩子 `_onHasteEnd` DE:768-770 清 stacks。
- 移除：圣域结束 `removeStatusEffect('haste')` + 蛇池祝福按类型清。

## 2.21 weaponHaste 命中动能（P4040）
- 施加：`applyWeaponHaste(duration=2000, speedPercent=0.10)` DE:773-790：`_weaponHasteMul = 1+speedPercent`；已有条目 **`remaining = duration`（重置，不追加）**；玩家镜像。
- 消费：`update.js:378-380` `targetSpeed *= this._weaponHasteMul || 1.10`；到期 `_weaponHasteMul = 1`（DE 通用到期钩子）。
- 入口：DP:120-128 —— P4040 命中获得（`onHitSpeedBuff durationMs??2000, speedPercent??0.10`；“命中获得”改造 `calibrationHitsRequiredDelta` 影响所需连中数，craft-effect-registry.js:689）。

## 2.22 inspire 激励（怪物鼓号/萨满；数据层直乘型 buff）
- 施加：`applyInspire(duration, {speedMul=1.33, atkMul=1.5})` DE:705-724：已有条目**只刷时长、不再乘属性**（防双算，:707-711）；直接 `this.data.atk = floor(data.atk × atkMul)`、`maxSpeed/speed ×= speedMul`；玩家镜像 📣。
- 到期：`_onInspireEnd` DE:798-807 **除回**（`atk = max(1, round(atk / atkMul))`，速度 `/speedMul`）——迁移注意：数据层互乘期间若有其他 ±修正会被连带缩放。

## 2.23 chainSpell 链式强化（施法消费型）
- 施加：`addChainSpellStack()` `src/utils/magic-craft-helper.js:186-208`（松木握柄改造 `castHaste` 族之外的 `chainSpellOnCast`）：statusImmune 守卫；每层独立计时（haste 同款“计时数组”）。
- 消费：`consumeChainSpellBonus` magic-craft-helper.js:159-168：施法时 `damage ×(1 + stacks×chainSpellDamagePercent)`、`mpCost ×(1 + stacks×chainSpellMpCostPercent)`，随后 removeStatusEffect('chainSpell') 全清。
- 到期钩子：`_onChainSpellEnd` DE:793-795 `_chainSpellStacks=0`。

## 2.24 flameArmor 灼锋焰甲（光环 buff）
- 施加：`src/entities/components/flame-armor-system.js:93-98`：`addStatusEffect('flameArmor', effect.duration*1000, {name 灼锋焰甲 🔥 #ff7a3a})` + 玩家镜像（`_statusBarEffectId`）；时长 skills.json:1104 `12+floor((lv-1)*18/19)` 秒。
- 机制：① 物理命中附魔伤：DP:74-78 → `source.flameArmorSystem.onPhysicalHit(target, source)`（组件 :117 起，追加 `hitDamageBase+matk×ratio` 魔法伤害 + 火花）；② 光环灼烧 `_auraTick`（组件 :136-159，每 `auraTickMs=500` 对 `auraRadius(130+lv×6)` 内敌人 magic 伤害）；③ 到期经验：DE:693-694 钩子 → subsystems.js:585-588 → `SkillManager.addFlameArmorExp`。
- HUD 清理：组件 :205-206/:224-225。

## 2.25 electrified 感电（5 层过载反应）
- 施加：`applyElectrified(stacks=1, duration=4000, source)` DE:1425-1459：`_electrifiedStacks += stacks; _electrifiedTimer += duration`（追加式）；**≥5 层** → 清 stacks/timer/HUD + `_triggerElectrifiedOverload(source)` 并 return（:1432-1441）。
- 承伤：DE:131-133 电系伤害 ×(1+stacks×0.03)。
- 过载：`_triggerElectrifiedOverload` DE:1461-1502：`applyStun(1200)` + 以本体为圆心 150px、视线检查（`hasRangedLineOfSight`）后对**每个敌对单位** `floor(20 + srcMatk×1.2 + srcInt×1.2)` 电伤并**各自 +1 层感电（3000ms）**（可链式连锁）；伤害归属 `_electrifiedSource`（最后有效施加者快照，DE:1430）。
- 到期：共享 timer 归零清空（同 chill 模式）。
- 来源：lightning-strike（1 层/次，skills.json:650-651 duration 4000）、thunder-lance（2 层/次 5000ms，并吃 `electrifyDamagePerStack=0.1` 递增自身伤害，thunder-lance-system.js:325-338）、storm-domain（每跳 1 层 + 250ms 眩晕，strikeInterval 900ms）。

## 2.26 statusImmune 状态免疫（全局闸门）
- 施加：`applyStatusImmune(duration, options)` DE:727-741 → `addStatusEffect('statusImmune', ...)`。
- 拦截：DE:510 `if (type !== 'statusImmune' && this.hasStatusEffect('statusImmune')) return null;` —— **拒绝一切后续状态（含增益）**；且各 apply* 入口另有前置 `hasStatusEffect('statusImmune') return`（chill :1232/freeze :1297/petrify :614/corrosion :969/stun :814/stunExtend :853/fear :876/haste :744/weaponHaste :774/poison :930/bleed :1080/magicVuln :1100/bind :1070/cripple :1058/droneVuln :1137/camelFright :649/shred :581/electrified :1427）。
- 用户：矿洞/墓碑/炼药锅等机制授予 `Number.MAX_SAFE_INTEGER` 永久免疫；僵尸族对矿毒直接 remove（weather :298）。

## 2.27 waxSealSlow 封蜡减速（诅咒）
- 施加：`src/combat/wax-seal-status.js`（TYPE='waxSealSlow'）：value clamp 0..0.9、**重复命中只刷新**；调用 `src/effects/wax-seal-effect.js:121`（skill.slowDurationMs/slowReduction，默认 2000ms/20%）。
- 消费：玩家 `update.js:407` `targetSpeed *= 1 − value(默认0.2)`；敌人 `movement-system.js:1033` `waxSealSpeedMultiplier(enemy)`。
- 移除联动：DE:670 —— `removeStatusEffect('waxSealSlow')` 时自动 `StatusBar.removeEffectByType('waxSealSlow')`（净化/到期都不留影）。

## 2.28 marbleHeal 大理石守护（击杀触发指示）
- DE:386-400：玩家阵营实体击杀时（onDeath 侧 source 分支）`_marbleHealTimer = 1000` + `StatusBar.addEffect('marbleHeal', 1000)`；窗口内玩家 `update.js:598` 驱动按秒回血（heal 来源 `_marbleHealPerTick`）。指示型条目，机制在计时器字段。

## 2.29 ginsengHeal 人参回气（击杀触发指示）
- DE:402-420：同上结构，`_ginsengHealTimer=1000` + `StatusBar.addEffect('ginsengHeal', 1000, {🌿 人参回气 #6a9a5a})`；`update.js:611` 驱动窗口内回 MP（每次击杀 5% maxMp，由 tributeGinseng 献祭激活）。

## 2.30 shield（占位）、2.31 buff（占位）
- 无施加机制。`buff` 仅剩遗留清理引用：dungeon-event-system.js:487-511 `clearAllBuffs` 里 `removeEffectByType('buff')` + 清 `_dungeonBuffs.buff`。迁移可删。

## 2.32 goddessBless 女神祝福（地牢事件通道产物，按场）
- `dungeon-event-system.js:315-353 applyGoddessBless`：`_goddessBlessRemaining = choice.buff.battles ?? 3`；atk/matk ×(1+15%)（`blessAtkPercent` 配置:107）；HUD `StatusBar.addEffect('goddessBless', battleRemaining 显示)`。
- 消耗：`consumeBattleBuffs` :451-481 —— 每场战斗结束 `battleRemaining--`；归零 removeEffect + 还原属性；:473 直接 `StatusBar.render()`。

## 2.33 demonPrayer 恶魔祈祷（永久文本条目）
- `dungeon-event-system.js:359-397`：atk/matk ×(1+33%)（`demonBuffAtkPercent` :168）；HUD `persistent:true, durationText:'持续至本次地牢结束'`（HUD 时间位显示该文本，progress 恒 100%）；离开地牢 `clearAllBuffs` 结算。

## 2.34 地牢临时 buff 通道（62 个事件 ID 共用）
- `_applyTemporaryBuff(player, buffCfg)` dungeon-event-definitions.js:1901-1935：写 `player._dungeonBuffs[buffCfg.id] = { remainingBattles: durationBattles(默认3), baseStats, statBonuses, statsApplied, buff }`；HUD `StatusBar.addEffect(type, battleRemaining, {icon/name/color/durationText:'N场'})`；数值：`floor/ceil(stat × percent/100)` 加算进面板并随 battle 结算还原；`consumeBattleBuffs` 每场 −1。type = buffCfg.id 本身（**不写实体 statusEffects**，纯数据 + HUD 镜像）。
- 描述文本生成 `_buffDescription` :1937-1945。

## 2.35 献祭 buff 通道（10 个 tribute* ID）
- `syncTributeBuffs(player)` tribute-effects.js:362-400：条件驱动（效果数值存在且未消耗才挂），全 `persistent + durationText:'跟随献祭倒计时'`；`clearTributeBuffs` :403-413 地牢结束统一清。机制本体（经验+25%/承伤上限 15%/复活/生产等）在各自数据消费点，条目仅是指示器。
- `rollTributeDrop` :305-323 决定获得哪个。

## 2.36 位面献祭通道（world122Tribute_*）
- `src/world/world122-tribute-system.js:223-258`：type = `world122Tribute_<key>`；`StatusBar.addEffect(type, 剩余ms, { name '位面献祭·<item>', icon item.icon||'🕯️', color '#7ab8ff', durationText: 分:秒倒计时 })`；`_syncMoonshadow` :249-258 同步隐藏月影计时；30 分钟现实倒计时。

## 2.37 驱散/净化白名单矩阵（唯一三处）
| 入口 | 文件:行 | 白名单 | 节奏 |
|---|---|---|---|
| 圣所领域（己方） | `sanctuary-domain-system.js:48-49` | poison, minePoison, bleed, fear, chill, frozen, slow, waxSealSlow, bind, magicVulnerability, droneVulnerability, electrified（每跳每友军清 1 个，electrified 同时清 `_electrifiedStacks`，:233-236） | 每 `cleanseIntervalMs=2000` |
| 圣裁（己方） | `holy-judgment-system.js:59-60`（消费 :319-328） | poison, bleed, fear, chill, frozen, slow, bind, magicVulnerability, droneVulnerability, electrified（**一次全清**，少 minePoison/waxSealSlow） | 施法瞬间 |
| 玩家主动清毒 | `player/subsystems.js:440-447` | `clearPoison()`：poison + minePoison + 解毒道具消费入口 | 手动 |
| 腐蚀专清 | DE:1013 `clearCorrosion()`（圣水/事件奖励调用） | — | — |
| 死亡兜底 | DE:346-347；companion.js:271-272 | petrified、frozen（清 + `_freezeStacks/_freezeTimer=0`） | 死亡 |
| 全局 | DE:510 statusImmune 闸门 | 拦截新增，不删已有 | — |

## 2.38 敌方施加的“配置驱动”状态（怪物攻击块 schema）
- `enemy.js:915` `attack.poisonStacks → applyPoison`；:919 `attack.bleed → applyBleeding`；另支持 `stunMs/cripple/bind` 字段（各 enemy-types 配置，见卷三表）。控制抵抗：time-agent-shield 弹体瓶用 `hasStatusEffect('stun')` 防重（不叠加，只补感电）；snowfield-lords frostMarkStun 以“现有眩晕剩余”为门；deep-vein-mother `stunResistRatio`（部分时段按概率减免眩晕时长）。

## 2.39 元素/状态相互作用清单（全部现存交互，DE 内）
| 反应 | 规则 | 位置 |
|---|---|---|
| chill → frozen | 层数≥20 触发冻结（时长=本次 chill duration），寒冷 −10 层 | DE:1244-1257 |
| 冻结期间 | applyChill 直接 return（不再叠层） | DE:1234 |
| frozen × 物理 | 冻结目标受非魔非电 ×1.5 | DE:154-157 |
| petrified × 魔法 | 石化目标受 magic/electric ×1.5(value) | DE:122-129 |
| electrified → 过载 | 5 层 → 眩晕1200 + 150px 电击传导（传导再 +1 层，链式） | DE:1432-1502 |
| thunder-lance × electrified | 伤害随目标感电层数 ×(1+stacks×0.1) | thunder-lance-system.js:325-338 |
| burn × 防御 | 灼伤是 magic 伤害，吃 mdef/魔抗蚀刻/魔力易伤/石化增伤 | DE:1366 |
| statusImmune × 一切 | 拦截所有新状态（含 buff） | DE:510 |
| **不存在**的反应 | burn 不蒸发冻结、冻结不强化燃烧、无“融化/引爆/蒸发”组合（grep 证实全项目无元素反应系统；燃烧/沼气“点燃”是地牢事件文案与流体特效，与状态层无关） | — |

## 2.40 takeDamage 乘区总顺序（状态消费的唯一主干，DE:97-301）
```
0) 过滤:友军免伤/怪物互免/近战承载面 (:99-103)
1) applyDefenseToDamage (DF:1-23):
     mdef×(1−magicResistanceShred) [magic/electric] → def×corrosionMul [非magic]
     → ×(1−penetration) → 减伤 = max(floor(atk·(1−def/(def+60))), floor(atk·0.1))
2) ×(1+magicDamageBonus)  [法袍套, 非状态] (:110-115)
3) ×(1+0.05×magicVulnerabilityStacks)  [magic|electric, 可 ignore] (:117-121)
4) petrified: ×1.5(value)  [magic|electric] (:122-129)
5) electrified: ×(1+0.03×stacks)  [electric] (:131-133)
6) ×(1−rangedDamageReduction) [非状态] (:136-138)
7) droneVulnerability: ×(1+bonus%)  [受益阵营白名单] (:140-144)
8) tribute monsterDamageTakenMul / surviveCap (:146-153)
9) frozen: ×1.5  [非magic非electric] (:154-157)
10) 盾兵格挡50% (:160-167) → 暴击判定(含 droneVuln critBonus :196-198) (:169-216)
11) applyOutgoingDamageModifiers (camelFright; ODM:40-58) (:223)
12) 重甲套装自动格挡 (:227-239)
13) marked: ×(1+value‖0.15) (:243-247)
14) holyWard: ×clamp(value,0.05,1) (:248-249 → :597-605)
15) 女墙方向掩护/传奇盾庇护 (:252-261) → 扣血/吸血 (:271-285)
```
（`Math.floor` 逐区取整；迁移时保持顺序即数值一致。）

## 2.41 通用到期钩子（updateStatusEffects，DE:678-698）
每帧遍历 statusEffects：`remaining -= dt`；corrosion **跳过**（自带逐层计时，:683）；归零 splice 并按 type 触发钩子：inspire→`_onInspireEnd`（还原乘区）、haste→`_onHasteEnd`、weaponHaste→`_weaponHasteMul=1`、chainSpell→`_onChainSpellEnd`、flameArmor→`_onFlameArmorEnd`（经验结算）。玩家镜像条目由 SB.update 独立倒数（两套计时并存——已知不精确点，见总卷 §2.6）。

## 2.42 玩家移速乘区完整顺序（player/update.js:341-417）
`冲刺基速 → slow ×0.5 (:343) → bind =0 (:345) → 举盾 defenseMoveSpeedMultiplier (:347-349) → 惩罚/锻造/手枪精通 → haste (1+stacks×0.10) (:373-376) → weaponHaste ×_weaponHasteMul (:378-380) → chill getChillSpeedMul() (:382-383) → 道路加成 → fear getFearSpeedMul()（逃离分支限速）→ waxSeal ×(1−value) (:407) → dash 锁`。
**bind 归零在其后所有乘法之前；haste 与 chill 是乘算而非抵消。**

## 2.43 敌人移速乘区（movement-system.js:1005-1034 `_getEnemyBaseSpeed`）
`base × chillMul × slowMul(1−clamp(value,0,0.9)) × inspireMul × friendlyMul(祭品+狼烟结界光环半径判定) × waxSealSpeedMultiplier`；另 :167 移动阻断名单（stun/frozen/petrified/bind/fear → 速度清零+中断移动状态机），:246 bind 特判清输入。

## 2.44 控制矩阵（行动阻断对照）
| 状态 | 玩家 | 敌人/同伴 | 附加 |
|---|---|---|---|
| stun | update.js:84-104 全锁+中断动作 | isCombatActionBlocked (enemy.js:629-633) | 打断预警/施法/攻击动画 |
| frozen | 同上（isStunned 并道）+ 非魔承伤×1.5 | 同列 + 死亡强清 | 冰块视觉/音效 |
| petrified | update.js:74-80 早返回（保留攻击动画不重置） | enemy.js:648/677-687 | 动画定格、免击退 |
| bind | targetSpeed=0 + 禁闪避 (subsystems.js:1136) | 移动阻断 :167 | 不禁攻击——半软控 |
| fear | 强制逃离+减速 (update.js:124-157) | isCombatActionBlocked（**完全停手**） | 层数≤3 |
| （玩家快捷物品栏） | frozen/stun 时禁止喝药（quick-bar 检查） | — | 注意与旧文档“眩晕不能喝药”一致仅限这两个 |
| （快速施法） | 眩晕/冻结/石化期间技能队列挂起 | 同 | — |

## 2.45 地牢 buff 的“按场”生命周期（consumeBattleBuffs，dungeon-event-system.js:451-481）
每场战斗结束：`_dungeonBuffs[id].remainingBattles--`；同步 HUD 条目 `battleRemaining--`（≤0 removeEffect）；`demonPrayer/goddessBless` 走独立字段；`clearAllBuffs`（离层/团灭）:487-511 全清并还原面板 + `removeEffectByType` 逐个移除。

## 2.46 StatusBar 条目自身的叠加/倒计时语义（SB:131-219）
与实体层同构但独立：`addEffect` 同 type 合并优先级 `persistent > battleRemaining > 毫秒取 max`（:140-161）；`update(dt)` 跳过 persistent/battleRemaining 条目的倒数（:197-219）；条目 id = `${type}_${nextId++}` 风格唯一串（:134）。**HUD 是镜像不是真源**：实体侧 `_poisonStacks` 等才是数值；机制迁移可整体抛弃此层，仅复刻显示语义（见卷四）。
