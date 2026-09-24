# 旧项目（无尽轮回 Phaser/JS）Buff/Debuff 体系迁移审计 — 源清点总卷

- 审计根（**只读**，未做任何修改）：`E:\无尽轮回\长期备份\2026-7-13-1\game-dev`
- 审计日期：2026-09-24（快照内所有行号对应该 checkout）
- 分卷：
  - `source-inventory-1.md` — §1 完整状态目录（38 注册 ID + 5 未注册显示 ID + 64 条地牢事件 buff + world122 动态族）＋ §6 图标资源
  - `source-inventory-2.md` — §2 逐状态机制实现（DoT/HoT、属性乘区、控制、proc、光环、驱散、交互）
  - `source-inventory-3.md` — §3 全部施加/移除入口（武器、技能、怪物、药水、附魔、献祭、地牢、套装）
  - `source-inventory-4.md` — §4 状态栏 HUD 1:1 渲染规格 ＋ §5 隐藏机制清单

## 0. 架构总览（迁移必读）

状态体系是**两层双写**结构，没有统一数据模型：

1. **实体层（机制真源）**：`DamageableEntity.statusEffects[]`（`src/entities/damageable-entity.js`），所有战斗机制通过 `hasStatusEffect(type)` / 专用 `_xxxStacks` 字段查询。另有 8 个状态**不进数组、只存专用计数/对象字段**（poison、bleed、corrosion、magicVulnerability、chill、burn、electrified、haste、droneVulnerability 的机制真源都是 `_poisonStacks` 等字段，`statusEffects`/StatusBar 只是显示镜像）。
2. **HUD 层（仅玩家可见）**：全局单例 `StatusBar.effects[]`（`src/ui/status-bar.js`）。绝大多数镜像点有 `this._faction === 'player' && StatusBar` 守卫，敌方/友方单位的可见状态走 RTS 单位详情面板（`src/ui/rts-unit-detail-model.js` 的 `STATUS_META`，第三套分类字典）。**两处例外（旧项目串台缺陷，源码逐行复核确认）**：基类 `applyCripple`（DE:1060-1061）与 `applyBleeding`（DE:1085）的 `StatusBar.addEffect` **无阵营守卫**——玩家给任意怪物挂致残/流血时，怪物身上的「致残🦴/流血🩸」条目会真实出现在玩家自己左上角状态栏（按剩余时长取 max 与玩家自身同类合并）。反向串台一处：断索狱卒直调 `addStatusEffect('bind')` 绕过 applyBind → 玩家被它束缚时无 HUD 条目（卷三 3.3.2）。

权威定义文件（4 处）：
| 文件 | 内容 |
|---|---|
| `src/entities/damageable-entity.js` | 实体层 STATUS_CONFIG（28 键，:477-506）+ 全部 apply*/_update* 机制 + takeDamage 消费乘区 |
| `src/ui/status-bar.js` | HUD 层 STATUS_CONFIG（31 键，:10-42，含 tooltip 描述文案）+ addEffect/update/render/tooltip 全部逻辑 |
| `game-style.css` | 状态栏全部 CSS（:76-188） |
| `src/world/dungeon-event-definitions.js` + `src/config/tribute-effects.js` | 地牢事件 buff（64 条）与献祭 buff（10 条）的 ID/图标/颜色/数值 |

## 1. 统计口径（精确总数，无"等"）

### 1.1 状态 ID 总数
| 集合 | 数量 |
|---|---|
| 实体层注册 ID（damageable-entity STATUS_CONFIG） | **28** |
| HUD 层注册 ID（status-bar STATUS_CONFIG） | **31** |
| 两者交集 | 21 |
| 两者并集（"注册 ID"） | **38** |
| 实体层独有（bar 无 desc，需显式传 options 或走 options 覆盖） | bind, inspire, magicResistanceShred, statusImmune, haste, marked, camelFright（7） |
| HUD 层独有（实体字典无） | waxSealSlow, marbleHeal, goddessBless, demonPrayer, tributeSnowLotus, tributeGinseng, tributePeach, tributeDiamond, tributeMoonstone, tributePhilosopher（10） |
| 未注册但会出现在状态栏的静态 ID（靠 options 显式传 icon/name/color） | ginsengHeal, tributeBloodVine, tributeWolfBanner, tributeJadeTwins, tributeAstrolabe（5） |
| 地牢事件 buff（`buff:{id,...}`） | **66 处出现 / 64 种参数组合 / 63 个唯一 ID**（steadyMind×3 处两档数值、madVision×2 处同值；全部 `durationBattles: 3`） |
| 动态族 `world122Tribute_<key>`（key 随祭坛物品种类，不定） | 1 族 |
| **全部可枚举唯一 HUD 可见标识** | 38 + 5 + 63 = **106 个静态唯一 ID + 1 动态族** |

### 1.2 buff / debuff / 控制分类（38 个注册 ID）
分类依据：`src/ui/rts-unit-detail-model.js` `STATUS_META`（:9-34，游戏自带的 buff/debuff tone 字典，24 条）+ 未覆盖 ID 的符号判断。

- **纯增益 buff：注册 38 内 19** = buff（占位）、shield（占位）、inspire、statusImmune、haste、weaponHaste、holyRenewal、holyWard、chainSpell、flameArmor（以上实体层 10）+ marbleHeal、goddessBless、demonPrayer、tributeSnowLotus、tributeGinseng、tributePeach、tributeDiamond、tributeMoonstone、tributePhilosopher（以上 HUD 独有 9）；再加未注册但上栏的 5 个（ginsengHeal、tributeBloodVine、tributeWolfBanner、tributeJadeTwins、tributeAstrolabe）→ **24**。含 2 个从未被施加的占位 ID `buff`/`shield`。
- **减益 debuff（19）**：stun、poison、minePoison、slow、bind、bleed、corrosion、magicVulnerability、magicResistanceShred、droneVulnerability、fear、chill、burn、frozen、petrified、electrified、marked、camelFright、waxSealSlow。
- 其中**控制类**（阻断行动）：stun、frozen、petrified、bind、fear（5）；electrified/chain 的过载会**衍生** stun。
- 地牢事件 63 唯一 ID：**28 增益 / 35 减益**（数值正负即类别，见分卷 1 附录表）。
- **机制条目数（§2 覆盖）**：38 个注册状态逐一有机制实现（2.1–2.38），另含 8 个系统级机制条目（全局免疫闸门、通用到期钩子、takeDamage 乘区总顺序、玩家移速乘区链、敌方移速乘区链、地牢按场消耗通道、献祭同步通道、驱散白名单矩阵）→ **46 条机制实现条目**，全部有 file+line+代码片段。

### 1.3 施加/移除入口计数（§3）
- 施加调用点：武器/改造 18、技能组件 16、怪物/AI 离散 25 + 通用攻击 schema 7 字段、消耗品→净化 2、附魔 1、套装/盾牌/铁匠 5、世界/天气 2、statusImmune 授予 4 —— **约 105 个离散调用点 + 4 个数据驱动通道**（地牢事件 64 条定义、献祭 10 条、world122 动态族、enemy attack 配置块）。
- 移除/驱散入口：死亡清理、净化（sanctuary/holy-judgment/clearPoison/clearCorrosion）、复活、地牢结算、献祭结算、waxSeal 特例 —— 全列于分卷 3。

## 2. 不确定点 / 需要产品决策处

1. **同名 ID 两处字典 icon/颜色不一致**：`fear` 实体层 😱 `#7a5ac8` vs HUD 层 😨 `#6a5a8a` vs RTS 面板 😱；`magicResistanceShred` 实体层 ✦ `#9f7cff` vs 无 HUD 注册；`camelFright` 实体 `#c99b5d` vs HUD 层无（RTS 用 `#c9a227` 变体记录）。迁移时需各选一套为唯一真源。
2. **同一 type 多种显示身份**：`slow` 有 6 种显示名（减速🐌 / 致残🦴 / 月蚀迟滞☾ / 星图迟滞✦ / 霜径迟滞❄️ / 镇暴压制🛡️）；`bind` 有 4 种（束缚⛓️ / 王猎锁定♛ / 葬潮束缚◈ / 时滞锚定◉）；`droneVulnerability` 有 2 种（无人机易伤🛸 / 战术弱点标记⌖）。机制同型、皮肤不同；皮肤名只在条目首建时写入。
3. `docs/buff-reference.md`（2026-08-26）为过时文档，缺 holyWard/marked/flameArmor/weaponHaste/camelFright/magicResistanceShred 等，仅可当历史注解，本报告以代码为准。
4. 状态栏注释与实现相符（无排序、纯插入序），但条目 DOM 每次整块 innerHTML 重建，UE 复用时用增量列表即可，注意"hover 中条目被重建导致 tooltip 竞态"已由事件委托规避。
5. 感电过载的传导伤害 `floor(20+matk*1.2+int*1.2)` 中 matk/int 取**过载触发瞬间传导源**（最后施加者快照 `_electrifiedSource`）的属性，非链式各跳重算。
6. `poison` 的 HUD 计时镜像与实体 `_poisonStacks` 是两套计时（实体 5s/层衰减；HUD 条目在玩家分支由 update.js:183-190 同步），存在极端情况下显示与机制差 1 tick 的原生不精确——迁移时建议单真源。
7. 地牢事件 buff 的 `atkPercent` 等支持小数（如 12.5），取整方式为 `Math.ceil(atk × pct / 100)`（dungeon-event-definitions.js:1918-1921）。
8. `world122Tribute_<key>` 的 key 集合依赖祭坛物品配置（9 种物品 → 9 个具体 ID），未在本快照 JSON 内固化，迁移需按目标工程物品表重新枚举。
9. **HUD 串台缺陷（需产品决策“复刻或修复”）**：`applyCripple`（DE:1060-1061）与 `applyBleeding`（DE:1085）镜像无阵营守卫——玩家给怪挂致残/流血时玩家栏会出现对应条目；反向：断索狱卒 bind 直调 addStatusEffect 使玩家中招时不上栏。建议 UE 侧统一按受控者阵营路由。
10. **死字段**：协同“毒性瘴气”的 `_synergyPoisonChance/_synergyPoisonStacks` 有写无读（synergy-system.js:86/133/188，全 src 无消费点），该协同中毒从未生效——迁移不要照接线；`hollow-ovum.js:183` stunMs 无默认（缺配置=0 时长）。
