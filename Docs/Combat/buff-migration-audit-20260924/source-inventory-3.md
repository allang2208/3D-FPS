# 卷三 · §3 全部施加/移除入口（应用点普查）

方法：对 `src/` 全量穷举 `apply*( / addStatusEffect(' / StatusBar.addEffect(' / removeStatusEffect(' / removeEffect(ByType)(`（含 `?.()` 可选链形式），合并人工核对。**共 100+ 离散调用点、6 个数据驱动通道**。目标阵营决定 HUD 可见性：玩家阵营 → 镜像上栏；敌人/友方单位 → 仅实体数组 + RTS 详情面板。

## 3.1 武器与武器改造（施加者=玩家武器系统）

| 武器/改造 | 状态 | 参数 | 调用点 |
|---|---|---|---|
| 传说霰弹枪（月相标记） | `slow` · 月蚀迟滞 ☾ #6ebcff | value=configuredSlowReduction(默认0.5)，markDurationMs 默认 3000，月相附加 lunarSlowDurationMs 默认 500 | `src/combat/legendary-shotgun.js:124-128` |
| 传说霰弹枪（王猎） | `bind` · 王猎锁定 ♛ #c52c42 | bindDurationMs 默认 400 | `legendary-shotgun.js:226-229` |
| 神话霰弹枪（葬潮） | `bind` · 葬潮束缚 ◈ #7b61ff | bindDurationMs 默认 500 | `src/combat/mythic-shotgun.js:129-131` |
| 弹射改造（锚定阈值） | `bind` · 时滞锚定 ◉ #54e6ff | 每目标累计 anchorHitsRequired 次首段弹射后施加 anchorDurationMs 并清零计数 | `src/combat/weapon-ricochet.js:144-150` |
| 传说轻机枪（星图） | `slow` · 星图迟滞 ✦ #65d8ff | constellationSlowDurationMs | `src/combat/weapon-legendary-lmg.js:198-203` |
| P4040 命中动能 | `weaponHaste`（来源=自己） | durationMs??2000、speedPercent??0.10；每发弹丸至多一次 | `src/combat/damage-pipeline.js:120-128`（调用于 :125） |
| 黑匠「标记」 | `marked` | 概率=ability(mark_arrow)×chanceMultiplier、时长=ability.durationMs‖options、value=damageAmplify（默认承伤+15%）、同类型取强（preserveStronger 弱不覆盖强） | `src/combat/mark-arrow-effect.js:7-44`（写入 :35）；斥候穿透弹带全套 options 且受 `aiConfig.appliesMarkArrow!==false` 门（`ai/hamster-scout-ai.js:399-406`）、赏金猎人**无 options 纯建筑能力值**（`ai/hamster-musketeer-ai.js:291`） |
| 封蜡（敌方诅咒到玩家，列此因经武器技能管线） | `waxSealSlow` | value 夹 0..0.9（默认 0.20）、durationMs=skill.slowDurationMs；只刷新 | `src/combat/wax-seal-status.js:8`；调用 `src/effects/wax-seal-effect.js:121` |
| 改造·毒附魔（附魔系）| `poison` | effects.poisonStacks‖1 | `src/combat/attack.js:37`（EnchantOnHitRegistry.poisonOnHit :34-43） |
| 改造 bleedingOnHit | `bleed` +1 | 固定 1 层 | `damage-pipeline.js:110` |
| 改造 magicVulnerabilityOnHit | `magicVulnerability` | stacks=ce.magicVulnerabilityStacks‖2 | `damage-pipeline.js:114`；同源 `components/rune-sword-system.js:251`、`components/special-attack-system.js:237` |
| 改造 castHaste（檀木握柄） | `haste`（自己） | ce.castHasteDuration‖5000，perStack 默认 0.10 | `src/utils/magic-craft-helper.js:178` |
| 改造 chainSpellOnCast（松木握柄） | `chainSpell`（自己） | durationMs；每层独立计时 | `magic-craft-helper.js:205` |
| 改造 iceChill（冰锥吊坠） | `chill` 1 层 | ce.iceChillDuration‖3000, ce.iceChillSlowPercent | `components/ice-spike-system.js:144` |
| 改造 electricStunExtendMs（爆鸣雷铃） | `stun` 延长 | applyStunExtend(stunMs, extend) | `components/lightning-strike-system.js:187/209` |
| 普攻致残（武器配置） | `slow`(致残) | config.crippleDuration | `attack.js:398`、`attack.js:464` |
| 普攻眩晕（玩家→敌，含领主豁免/首领免疫） | `stun` | stunMs | `attack.js:103`（门控 :67-104） |

## 3.2 技能与技能组件（施法管线）

| 技能 | 状态 → 目标 | 参数（skills.json 实配） | 调用点 |
|---|---|---|---|
| 暴风雪 | `chill` 敌 | chillStacks 1, durationMs 2500, slowPercent **0.035**（每 tick 施加） | `components/blizzard-system.js:166` |
| 冰墙（光环） | `chill` 敌 | radius 100、interval 1000ms、stacks 1、slowPercent 0.035、duration 2500 | `components/ice-wall-system.js:375`（写入 :202-206） |
| 冰锥 | `chill` 敌（带改造才施） | 见 3.1 | `components/ice-spike-system.js:144` |
| 陨石 | `burn`+`stun` 敌；熔岩 `burn` | 爆炸 burnStacks 3/3500ms/×0.5；stunMs 2000；熔岩 lavaBurnStacks 1/2500ms/×0.3；tick 均 500 | `components/meteor-system.js:164/168/201` |
| 雷击 | `electrified`+`stun(Extend)` 敌 | stacks 1/4000ms；stunMs=750+lv×20 | `components/lightning-strike-system.js:204/209/211` |
| 雷枪蓄力 | `electrified` 敌 | stacks 2/5000ms；伤害吃目标层数 ×(1+层×0.1) | `components/thunder-lance-system.js:348`（乘区 :325-338） |
| 风暴领域 | `electrified`+`stun` 敌 | stacks 1/4000ms + stun 250ms，每 900ms 一跳 | `components/storm-domain-system.js:199/202` |
| 火球/法爆（改造 fireBurn） | `burn` 敌 | ce.fireBurnDamageMul/Duration‖3000/TickMs‖500，1 层 | `components/bolt-skill-system.js:514` |
| 灼锋焰甲 | `flameArmor` 自己 | duration=effect.duration×1000 | `components/flame-armor-system.js:93`（HUD :98） |
| 圣光 | `holyRenewal`(改造层数)+`haste`(ce.lightHaste)+`holyWard` 友方 | HoT healPercent 0.01；haste duration ce.lightHasteDuration‖5000；ward=aiConfig.holyWardDurationMs/Multiplier | `components/holy-light-system.js:272/277/158`（另 :360/:365/:449/:454 分支） |
| 圣裁 | **驱散**（全清负面）+ holyWard? | CLEANSE_TYPES 10 种，一次全清 | `components/holy-judgment-system.js:59-60, 319-328` |
| 圣所领域 | **驱散**（每 2000ms 每友军 1 个） | CLEANSE_TYPES 12 种（含 minePoison/waxSealSlow） | `components/sanctuary-domain-system.js:48-49, 233-236, 267-270`；附赠 castHaste :126 |
| 旋风斩 | `stun` 敌 +`bleed`(改造) | stunDuration 2500 | `components/whirlwind-system.js:193/198` |
| 冲锋（玩家推斩改造） | `stun` 敌 | stunDuration | `components/push-strike-system.js:164` |
| 符文剑/夜火剑（特殊攻击） | `magicVulnerability` 敌 | stacks=ce.magicVulnerabilityStacks‖2（nightFlame: magicVulnStacks 2） | `rune-sword-system.js:251`、`special-attack-system.js:237` |
| 寒灵/冰锥石化（怪物侧见 3.3；玩家侧 petrify 唯一入口=改造） | — | — | — |
| 电系感电（chill 转化 freeze 属机制内生，非入口） | `frozen` | chill≥20 | `damageable-entity.js:1247` |

## 3.3 怪物与 AI（施加者=敌方/友方单位）

### 3.3.1 通用攻击配置 schema（`src/entities/enemy-types.js`，全部怪物共享字段）
| `attack.poisonStacks` | `poison` | `enemy.js:915`（legacy 毒液僵尸近战；远程 spit 必中经 projectile.js:124） |
| `attack.bleed`（boolean） | `bleed` +1 | `enemy.js:919`（协同系统消费点） |
| `stunMs`（攻击/碰撞段） | `stun` | `enemy-types.js:2988/4753/5419/6063` |
| `bindMs`（默认 3000） | `bind` | `enemy-types.js:3050`（紫蚀古树藤牢，施加前显式查 statusImmune :3049） |
| `petrifyDuration + magicDamageTakenMultiplier` | `petrified` | `enemy-types.js:4180`（美杜莎石化凝视，**全项目唯一敌方石化**） |
| `stealthStrike.crippleMs` | `slow`(致残) | `enemy-types.js:4455/4754`（狼人王潜影爪击/飞扑破影） |
| 冲锋撞墙自晕 `wallSelfStunMs`（默认 600） | `stun` **给自己** | `enemy-types.js:5389`（泥沼冲城独角仙王） |

### 3.3.2 专属怪物/首领（enemy-types 单文件；经子代理穷尽审计核对归属）
| 单位 | 状态 | 调用点与参数 |
|---|---|---|
| **红狼王 BlackWolf**（血烟飞扑 + 猩红嚎叫） | `slow`(致残) 3000ms（飞扑命中未弹反，原眩晕改致残）；`inspire` 全场敌营 30000ms（atk×1.5 speed×1.33，CD 30s，含自身） | `enemy-types.js:347-348`（pounceCrippleMs；BlackWolf 共享状态机仅 `_usesPounce` 激活）；`:1141-1146`（嚎叫 applyInspire）。⚠️ 勘误：:1142 不是僵尸工头；工头号召在 `foreman-zombie.js:304` |
| 突变体3 | `stun` 2000（硬编码，飞扑命中）；`bind` 500/每段（连击五段，硬编码） | `enemy-types/mutant-3.js:175/341` |
| 僵尸工头 | `bleed` +1（鞭击，bleedStacks 1 config）；`inspire` 15000ms 全场敌营 | `foreman-zombie.js:276/304`；召唤矿洞带 statusImmune `:392-401` |
| 寒渊裂晶兽（精英） | `corrosion` 2 层/6000ms/0.06 每层（普攻确认命中） | `enemy-types.js:2504-2515` |
| 食人花 | `corrosion` 1 层/5000ms/0.05（每次命中） | `enemy-types.js:3170-3181` |
| 棕蛇 | `poison` +1（每次实际命中且未弹反） | `enemy-types.js:3243-3248` |
| 黑色眼镜蛇王 | `poison` 3（普咬 poisonOnHit）/ 5（紫雾毒液喷射 venomSpray：伤害 0.85×matk、CD 9s、射程 420、扇 82°） | `enemy-types.js:3839-3846`（层数经 context.poisonStacksOverride） |
| 芦苇影镰螳 | `bleed` +3（镰扇横扫技能） | `enemy-types.js:3589-3598` |
| 紫蚀古树 | `stun` 1500（古岩投掷，180px 椭圆）；`bind` 3000（紫蚀藤牢 220px + VineEntangleEffect） | `enemy-types.js:2986-2988/3047-3053` |
| 美杜莎 | `petrified` 5000ms、魔伤倍率 1.5（石化凝视：射程 500、弧 80°、CD 14s，对 player/companion/友军） | `enemy-types.js:4107-4183` |
| 狼人王 | 潜行首击 `slow`(致残) 3000 + 伤害×2；猎王飞扑 `stun` 2000（+破影再致残 3000） | `enemy-types.js:4449-4456/4733-4756` |
| 泥沼冲城独角仙王 | `stun` 1250（冲锋命中）；`stun` 自身 600（撞墙） | `enemy-types.js:5406-5419/5386-5389` |
| 腐潮蟾祖·格罗玛 | `stun` 900（撞身落砸）；`poison` 2（毒液喷吐）；`stun` 400（召唤鸣叫）；另生成 190px/6.5s 毒液区（tick 700ms、0.32 伤害、poison +1、致残 2s 静默刷新） | `enemy-types.js:6036-6063`（毒液区 `_shared/venom-bottle.js`） |
| 空腔之卵 | `stun` 650（壳脉冲 270px） | `hollow-ovum.js:167-184` |
| 蝇手 | `stun` 1000（砸地/灭世重砸；重砸必召 3 蝇群；锤击仅击退） | `fly-hand.js:219-225` |
| 重甲骑士 | `stun` 2500（持盾冲锋+击退 200）；弹反 `stun` 2000+击退 100（仅近战；`_parryImmune` 冲锋期免疫弹反） | `armored-knight.js:510-522/589-598/416/530` |
| 黑肺提灯长 | 致残 2500（沉镐镇压）；`poison` 3 + 致残 3000（黑肺咳雾）；`corrosion` 2/6500ms/0.05（提灯过载） | `black-lung-lamp-keeper.js:241-315` |
| 断索狱监 | `bind` 2000（投钩收绞，拉回 320px；**直调 addStatusEffect 绕过 applyBind** → 玩家中招无 HUD）；`stun` 900（囚笼镇压） | `broken-cable-gaoler.js:293-294/329-332` |
| 封井岩魇 | 致残 2200（晶臂砸击）；致残 3000（岩脉震荡）；`stun` 1800（钻头旋冲+击退 240） | `sealed-shaft-rock-wraith.js:344-354/368-378/392-399` |
| 雪冢驮城兽 | `slow` · 霜径迟滞 ❄️ value 0.35（冲锋霜径：半径 70、寿命 4000ms、贴身每帧刷新 remaining≤450ms）——**slow 的又一显示皮肤** | `snowfield-lords.js:623-640` |
| 白寂鸣钟鹿 | 致残 1000（鹿角剜击）；`stun` 700（长音贯雪 620×120 直线钟波） | `snowfield-lords.js:1362-1369/1420-1429` |
| 首脑（shounao） | `fear`（嚎叫：每 500ms 一次 600px 魔伤 tick，**每次 tick 都叠恐惧** ≤3 层；fearMs 3000） | `shounao.js:320-339`；全项目唯一敌方恐惧来源 |
| 矿石蜘蛛 | `stun` 2000（起跳下砸，命中未弹反） | `ore-spider.js:336-359` |
| 时空特工·突击 | 致残 3000（斧劈）；`stun` 2000（闪光弹 125px 圈，登记 `AgentLinkSystem.notifyFlashStun` 使盾卫暂缓盾击） | `time-agent-assault.js:688-698/747-767` |
| 时空特工·盾位 | `stun` 2000（盾击 200×160 正面）；弹反 `stun` 2000+击退 100；受远程伤害减半（非状态） | `time-agent-shield.js:442-449/410-419/391-405`；弹体瓶 `:440-455` 防重 |
| 巫婆 / 煮锅 / 蟾祖毒液区（共享） | `poison` 1 + 致残 2000（**silent 无飘字**，区内持续刷新、离场仍存 2s） | `_shared/venom-bottle.js:85-113`；巫婆 200px/6s/投程 800/CD 8s（`witch.js:148-149/313`）；煮锅每 15s 投 2 瓶（`cauldron.js:118`，自身免疫但毒区照常） |
| 毒蛆 | `poison` +1（毒球命中 33% 概率；isSpit 且 chance=0 必中） | `poison-maggot.js:160-192` + `projectile.js:121-125` |
| 吐丝僵尸 | `poison` +1（远程吐液必中，chance=1） | `spitter-zombie.js:291-310` + `projectile.js:121-124` |
| 狼群战术协同（黑狼×3） | `bleed` +1（命中玩家 20% 概率） | `ai/synergy-system.js:82-87/128-134` |
| 毒性瘴气协同（黑狼×2） | `poison` +1（30% 概率） | `ai/synergy-system.js` + `enemy.js:918-919` |
| 丛林/沙漠牧师（友方 AI 对敌） | `electrified` +1/4000ms（闪电；5 层→过载） | `ai/jungle-priest-ai.js:276-291` |
| 敌方法师闪电（祷徒/大司祭/熊德鲁伊，共用玩家组件管线） | `stun`+`electrified` | 祷徒 350ms/1层2500；大司祭 450/1层2800；熊德鲁伊 600/1层（`lightning-strike-system.js:203-211`；config `enemy-types.js:2166/2536/6207+`） |
| 骆驼骑兵（友方光环→敌） | `camelFright`（每 200ms 刷新、半径 600、时长 350ms、reduction=兵营配置 ≤0.9） | `entities/hamster-camel-cavalry.js:55-74` |
| 仓鼠牧师（友方） | `inspire`（激励魔法 radius 300、CD 30s、speedMul 1.33 atkMul 1.5，含自身） | `ai/hamster-priest-ai.js:308-346` |
| 仓鼠射手（友方） | `poison` +1（毒箭铁匠升级，按概率、自限 maxStacks 不削他源层数） | `ai/hamster-shooter-ai.js:376-401` |
| 仓鼠战士/捷豹战士（友方） | 致残 3000（每击命中，jaguar 读 configData.crippleDurationMs） | `ai/hamster-warrior-ai.js:267-274`；`jaguar-warrior.js:16` |
| 仓鼠骑士（友方） | `stun` 2500×lord 修正（对 rank==='lord' ×lordStunDurationMultiplier 默认 0.25 → 625ms；弹反免除） | `ai/hamster-knight-ai.js:421-441` |
| 防暴小队（友方） | `slow` · 镇暴压制 🛡️（value=attackSlowPercent ≤0.9，时长 attackSlowDurationMs；扇形每目标命中）——**slow 友方皮肤** | `ai/hamster-riot-squad-ai.js:144-164` |
| 伊莉丝等队友 | `stun` attackStunMs（普攻，**仅 rank==='normal'**） | `ai/companion-ai.js:1389-1411（风车 2500）/1483-1488` |
| 伙伴通用 | `stun` parryStun??2000（弹反） | `entities/companion.js:569` |
| 战术小队（无人机标记） | `droneVulnerability`（旧签名 10%/10%/2000ms）/按源移除 | `ai/tactical-squad-ai.js:268/234/277` |
| 投射物毒链（吐丝僵尸/毒蛆/巫师僵尸/legacy 毒液僵尸） | `poison` | `spitter-zombie.js:309`（isSpit:true ⇒ chance=0 也必中）、`poison-maggot.js:188-189`（poisonChance??0.33/stacks??1）、`zombie-wizard.js:328`、`enemy.js:88`（isSpit: name==='毒液僵尸'）→ 统一落地 `combat/projectile.js:121-126`（chance=(isSpit&&poisonChance===0)?1:poisonChance，掷骰后 target.applyPoison(stacks)） |
| 狼群战术协同（黑狼×3，speedMul 1.2） | `bleed` +1（命中玩家 20% 概率） | `ai/synergy-system.js:83/129` 写 `_synergyBleedChance` → `enemy.js:918-920` 消费 |
| 毒性瘴气协同（黑狼×2） | poison——**死字段，从未生效** | `synergy-system.js:86/133` 写 `_synergyPoisonChance`（规则 `:188` poisonChance 0.3/stacks 1），全 src 无读取点；迁移勿接线 |
| 敌方法师复用玩家雷击组件（极夜祷徒/大司祭/熊德鲁伊对玩家） | `stun`+`electrified` | 同一管线 `components/lightning-strike-system.js:204-211`；祷徒 stunMs 350/electrify 1层2500ms、大司祭 450/1层2800ms、熊德鲁伊 600/1层（skills.lightningStrike 配置 `enemy-types.js:2166/2536/6207+`）。冰锥/火球敌方版**不挂** chill/burn（此两态仅玩家改造触发） |
| 无状态施加确认（穷尽 grep） | bomb-zombie、shroud-thrall、coffin-ward、ossuary-caster、knell-attendant、stitchface-headsman、pleat-devourer、support-beam-brute、core-drill-worm、miner-zombie、lantern-miner-zombie、mine-small-monsters、fly-swarm、amalgam-zombie（冲锋期弹反免疫≠状态免疫）、普通僵尸、battle-commander、tactical-squad-role-switch | — |
| 无状态施加（穷尽核对） | bomb-zombie、shroud-thrall、coffin-ward、ossuary-caster、knell-attendant、stitchface-headsman、pleat-devourer、support-beam-brute、core-drill-worm、miner-zombie、lantern-miner-zombie、mine-small-monsters、fly-swarm、amalgam-zombie（冲锋期弹反免疫≠状态免疫）、普通僵尸、battle-commander、tactical-squad-role-switch | — |

### 3.3.3 玩家侧专属入口（被施加者=玩家）
- 中毒：玩家 `applyPoison` 覆写 `player/subsystems.js:570-582`（`_isIncomingHitBlocked()` 闪避无敌可免毒！+ statusImmune；HUD 镜像 :579）。
- 流血 HUD 同步：`player/update.js:226-230`；中毒同步 :183-190。
- 眩晕：`player/subsystems.js:2874-2890`（闪避无敌直接免疫眩晕）。
- 训练假人 `target-dummy.js:141`（假人中毒镜像，仅调试）。

## 3.4 药水 / 消耗品 / 快捷栏规则
- **没有任何药水直接施加 status ID**（治疗/法力的回复是即时结算）；消耗品与状态的关系只有两条：
  1. **解毒类** → `clearPoison()`（`player/subsystems.js:440-447`：清 poison + minePoison + HUD）。
  2. 快捷栏使用限制：**frozen 或 stun 时禁止使用物品**（quick-bar 检查这两个 type；bind/fear/petrified 不禁物品）。
- 圣水池/事件奖励类“净化”→ 直接调 `clearCorrosion()` 等（DE:1013）。

## 3.5 附魔（EnchantOnHitRegistry）
- 附魔「毒」→ `attack.js:34-43` `target.applyPoison(effects.poisonStacks || 1)`（近战/远程命中管线内，武器附魔数据源 `data/enchantments.json`）。
- 附魔「魔剑/enchantedBlade」→ 不施加状态，追加一次魔法伤害（DP:116-119）。

## 3.6 献祭与祭坛（3 通道）
| 通道 | 状态 ID | 机制 |
|---|---|---|
| 地牢献祭（SPECIAL_BUFFS） | tributeSnowLotus / tributeGinseng / tributePeach / tributeDiamond / tributeMoonstone / tributePhilosopher / **tributeBloodVine / tributeWolfBanner / tributeJadeTwins / tributeAstrolabe**（10 个 persistent 指示器） | `tribute-effects.js:348-400 syncTributeBuffs` 条件挂载/移除；`clearTributeBuffs` :403-413 地牢结束清；效果数值在数据消费点生效（经验、承伤上限、复活、生产…）；触发型击杀回血/回蓝指示 marbleHeal/ginsengHeal 见 DE:386-420 |
| 位面祭坛（122 世界） | `world122Tribute_<key>` 动态族 | `world122-tribute-system.js:223-258`：30 分钟现实倒计时、durationText 分:秒；`_syncMoonshadow` 同步隐藏计时 |
| 地牢事件 | 63 个事件 buff ID | 见 3.7 |

## 3.7 地牢事件通道（62→63 唯一 ID）
- 定义：`dungeon-event-definitions.js`（1D 全表；success.buff / fail.buff 两型）。
- 施加：`_applyTemporaryBuff`（**:1901-1935**）：写 `player._dungeonBuffs[id]` + `StatusBar.addEffect(id, …, {battleRemaining})` + `addStatusEffect(id, 999999)` 占位（供 `hasStatusEffect(id)` 查询）+ 面板数值加成。
- 独立双状态：`goddessBless`（按场 3，DE 侧 `player.addStatusEffect('goddessBless', 999999)` dungeon-event-system.js:340 + HUD :330-334）与 `demonPrayer`（`addStatusEffect('demonPrayer', Infinity)` :384 + persistent HUD :373-377）。
- 消耗：`consumeBattleBuffs`（:451-481，每场 -1、HUD `battleRemaining--`、:473 强制 render）；离场：`clearAllBuffs`（:487-511，含 legacy `'buff'` 清理）。

## 3.8 套装 / 盾牌 / 铁匠能力
| 来源 | 状态 | 调用点 |
|---|---|---|
| 盾牌弹反（parryStun） | `stun` 攻击者 | `components/shield-system.js:374`（默认 1000ms+技能加成） |
| 盾牌弹反反击改造 arcaneRetort | `magicResistanceShred` 攻击者 | `shield-system.js:426-432` |
| 破盾自晕（stunOnExhaustion 1500/1650/1800） | `stun` **玩家自己** | `shield-system.js:240` |
| 圣佑（大主教随员） | `holyWard` | `companion.js:224`（同公式独立实现）；玩家侧来源=圣光组件 3.2 |
| 黑匠「标记」 | `marked` | 见 3.1 |

## 3.9 天气与世界
- 矿毒毒区：`world126-weather-runtime.js:258-320`（施加 :300，HUD :303，清除 :134-135/:279-280/:317-320；tick :310-315；僵尸/建筑/statusImmune 免疫 :284/:298）。
- 122 献祭：3.6。
- 封蜡诅咒（wax-face-mourner 技能）→ 3.1 末行（施加到玩家）。

## 3.10 移除/驱散入口全表
| 入口 | 作用 | 位置 |
|---|---|---|
| 通用到期 | `updateStatusEffects` splice（corrosion 除外）+ 钩子还原 | DE:678-698 |
| 圣光支援净化 | 白名单 11 逐个清（**含 waxSealSlow、不含 minePoison**）+ 硬置 `_electrifiedStacks=0` | `components/holy-light-system.js:47-50, 140-148` |
| 圣所领域 | 白名单 12 逐个清（=圣光 11 + `minePoison`）+ `_electrifiedStacks=0` | `sanctuary-domain-system.js:48-49, 221-241, 267-270` |
| 圣裁 | 白名单 10 全清（**不含 waxSealSlow/minePoison**）+ purify-kill 分支 | `holy-judgment-system.js:59-60, 319-328, 346-352` |
| 焰甲到期/强清 | flameArmor 回收+HUD remove；clearBuff 另调 removeStatusEffect | `flame-armor-system.js:200-216, 219-234` |
| 无人机离圈 | removeDroneVulnerability(sourceId) | `drone-system.js:245/248` |
| clearPoison（解毒道具/事件） | poison+minePoison+HUD | `player/subsystems.js:440-447` |
| clearCorrosion（圣水类事件） | corrosion 全清 | DE:1013-1021 |
| consumeChainSpellBonus | chainSpell 消费即清 | `magic-craft-helper.js:159-168` |
| 死亡 | petrified/frozen 强清（尸体不继承定格） | DE:346-347；companion.js:271-272 |
| 蟠桃原地复活 | poison 三字段清零(:394-396)、clearCorrosion(:397)、isStunned/stunTimer(:398-399)、过热四字段(:400-403)、动作标记复位；**保留地牢 buffs** | `player/subsystems.js:386-423` |
| 重生 respawn | poison 三字段(:437-439)、clearCorrosion(:440)、HUD poison 条目 remove(:441-444)、dash 眩晕(:446-447)、过热清零(:451-454)、其余 HUD 散点清理(:354/:480) | `player/subsystems.js:425-490` |
| 矿毒复曝/获免疫 | 状态已不在→重置 exposure/tick + remove HUD(:292-296)；僵尸家族或获得免疫→removeStatusEffect('minePoison')(:298)；离区/死亡→remove HUD+删记录(:277-282/:317-320) | `world126-weather-runtime.js` |
| removeStatusEffect('waxSealSlow') 联动 | 实体清除时自动 `StatusBar.removeEffectByType` | DE:670 |
| removeDroneVulnerability(sourceId,{immediate}) | 按源移除/全清/停续期 | DE:1158-1163；调用 `tactical-squad-ai.js:234/277`、`update.js:249`（玩家塔标记到期） |
| 地牢 consumeBattleBuffs / clearAllBuffs | battleRemaining 逐条清 | dungeon-event-system.js:451-511 |
| clearTributeBuffs | 10 个献祭指示 | tribute-effects.js:403-413 |
| world122 倒计时到期 / 换层 | `StatusBar.removeEffect` | world122-tribute-system.js:223-242 |
| StatusBar.clear() | **全项目唯一整栏清空 = 新局 Game.start()** | `game.js:264`（换场/死亡不整清） |

## 3.11 免疫 / 抵抗（不施加或减免路径）
| 免疫方 | 被免内容 | 位置 |
|---|---|---|
| statusImmune 持有者 | 一切新状态（含 buff） | DE:510 总闸 + 各 apply* 门禁（:554/621/649/706/744/774/813/853/876/930/1058/1070/1232/1297 等）；紫蚀藤牢额外显式预查 enemy-types.js:3049 |
| 永久授予：炼药锅 / 矿车 / 墓碑 | `applyStatusImmune(MAX_SAFE_INTEGER)` | `cauldron.js:32`、`mine-cave.js:48`、`tombstone.js:31` |
| 召唤物（**仅工头召矿洞一路**） | `summonMonster({statusImmune:true})` | `_shared/summon-helper.js:217-218`；唯一 true 调用方 `foreman-zombie.js:392-401`；矿区天气复活的矿洞同样免疫 `world126-weather-runtime.js:428` |
| 僵尸族 / 建筑 / 防御塔 | minePoison（并直接 remove） | `world126-weather-runtime.js:284/298` |
| 首领（rank==='boss'） | 玩家普攻眩晕（完全免疫；**仅此一项**，不存在按 rank 的石化/冻结免疫表） | `attack.js:91-104` |
| 领主（rank==='lord'） | 普攻眩晕按体质概率豁免（0.2+（体质−30）×0.0125，夹 0.15..0.55，豁免白闪 300ms）；另仓鼠骑士冲锋眩晕 ×0.25（lordStunDurationMultiplier） | `attack.js:97-102` + `data/combat-config.json:20-30`；`ai/hamster-knight-ai.js:436-441` |
| 队友伊莉丝普攻眩晕 | 仅对 rank==='normal' 生效 | `ai/companion-ai.js:1483-1488` |
| 深脉母体 | 眩晕按 stunResistRatio 减免 | `deep-vein-mother.js:317` 邻域 |
| 时间司铎·盾 | 眩晕不叠加（`hasStatusEffect('stun')` 防重，已晕只补感电） | `time-agent-shield.js:440-455` |
| 冲锋期单位（铠甲骑士/集合体僵尸） | 弹反免疫 `_parryImmune`（控制相关，非状态免疫） | `armored-knight.js:416/530`；amalgam-zombie |
| 闪避无敌帧（玩家） | stun 与 poison 直接免疫 | `subsystems.js:2877`、`:571` |
| 冻结中 | applyChill 直接 return（不再叠层）；石化免疫击退 | DE:1234、:459 |
| 死亡实体 | holyWard/magicShred/droneVuln/corrosion 拒绝施加（hp≤0 判定） | DE:551/579/1137/969 |
| 怪物互伤 / 友军误伤 | 不结算（也就无状态） | DE:99-103 |

### 控制刷新/递减语义（旧项目规则，UE 平衡决策输入）
- 同类控制**不累计**：addStatusEffect 孰长刷新（DE:515）——连续眩晕只延长不叠加；**唯一真累加路径是电系 `applyStunExtend`**（:856-857，`remaining += extend`）。
- 恐惧是唯一“多层递进”控制（≤3 层，各层 -33% 移速）。
- 各管桩怪的控制中断口径统一（stun/frozen/petrified 清速+return；fear 交 MovementSystem 逃跑分支；petrified 保持姿势、其余回 idle）：`enemy.js:661-687`；单文件同款 `cauldron.js:72-73`、`armored-knight.js:113-126`、`broken-cable-gaoler.js:121-126`、`black-lung-lamp-keeper.js:126-131`、`deep-vein-mother.js:56/156`、`sealed-shaft-rock-wraith.js:504-507`、`snowfield-lords.js:267-272`、`horror-normal-enemy.js:65-70`、`foreman-zombie.js:482-496`、`mutant-3.js:311-315`（大帧跨点被控终止连段）、`bomb-zombie.js:78-80`（被控冻结引信）。
- 死亡清控防定格卡动画：`deep-vein-mother.js:381-382`、`sealed-shaft-rock-wraith.js:528-529`、`enemy-types.js:3695-3696`（黑王蛇）+ 通用 DE:346-347。
