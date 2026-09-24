# 卷四 · §4 状态栏 HUD 渲染规格（1:1 复刻级） + §5 隐藏机制清单

来源：`src/ui/status-bar.js`（342 行）、`game-style.css`（:76-188）、`src/ui/panels/hud-core.js`、`src/game.js`。以下数值/字符串全部逐字照抄。

## 4.0 可见性模型
左上角状态栏**只显示玩家自己的状态**（`_faction==='player' && StatusBar` 门禁）——**例外两处（源码逐行复核）**：基类 `applyCripple`（DE:1060-1061）与 `applyBleeding`（DE:1085）无阵营守卫直调 `StatusBar.addEffect` ⇒ 玩家对怪物造成致残/流血时，怪物侧的「致残/流血」条目会写入玩家状态栏（与玩家自身同类按 max 合并、层数覆盖）。反向例外：断索狱卒直调 `addStatusEffect('bind')`（绕过 applyBind）→ 玩家中招无 HUD。其余怪物/友军单位状态通过 RTS 单位详情面板显示（`src/ui/rts-unit-detail-model.js:9-34 STATUS_META`，tone 字段 = buff/debuff 分类，24 ID 子集）。

## 4.1 容器与定位
- DOM 链：`body → #gameContainer(相对,100vw×100vh) → #uiLayer(absolute inset:0, z-index:10, pointer-events:none) → .status-bar-container#statusBarContainer`。
- 创建：`src/ui/panels/hud-core.js:20-23`（`document.createElement('div')`，class `status-bar-container`，id `statusBarContainer`，appendChild 到 uiLayer）。
- CSS（game-style.css:76-96）：
```css
.status-bar-container {
    position: absolute;
    top: 12px;
    left: 104px;            /* 硬编码，紧贴 .back-menu-btn(left:12px, 约80宽) 右侧 */
    width: 252px;
    max-width: 252px;
    max-height: 44px;
    display: flex;
    flex-direction: row;
    flex-wrap: wrap;
    justify-content: space-between;
    gap: 6px;
    align-content: flex-start;
    align-items: flex-start;
    overflow-x: hidden;
    overflow-y: auto;
    z-index: 11;
    pointer-events: none;
    scrollbar-width: thin;
    scrollbar-color: rgba(142, 166, 178, 0.45) transparent;
}
```
- 换行数学：条目 54px + gap 6px → 252px 每行最多 **4 个**（4×54+3×6=234）；`max-height:44px` 恰好一行，第 2 行起靠 `overflow-y:auto` 细滚动条滚动。
- **排序：无任何 sort —— 纯首次施加顺序（数组 push 序），buff/debuff 混排**（SB:308 `for (const effect of this.effects)`）。同 type 刷新是原地合并**不移位**。

## 4.2 条目 `.status-effect-item`（game-style.css:97-123）
```css
.status-effect-item {
    position: relative; display: flex; align-items: center; justify-content: center;
    flex: 0 0 54px; width: 54px; height: 44px; min-width: 0; min-height: 44px;
    padding: 3px;
    background: rgba(42, 37, 32, 0.85);
    border: 2px solid var(--effect-color, #5a4d3f);
    border-radius: 7px;
    color: #d4c5a9; font-size: 12px;
    font-family: SimHei, "Microsoft YaHei", "黑体", sans-serif;
    overflow: hidden; box-sizing: border-box;
    transition: all 0.2s ease;          /* 唯一条目级动效：hover */
    pointer-events: auto;               /* 容器 none / 条目 auto：tooltip 依赖 */
}
.status-effect-item:hover {
    border-color: #c4d3da;
    background: rgba(35, 42, 48, 0.96);
    box-shadow: 0 0 10px rgba(142, 166, 178, 0.34);
}
```
`* { box-sizing: border-box }`（:6）→ 54×44 **含** 边框与内边距。

### 4.2.1 子元素（全部 absolute 角标体系）
| 元素 | 规格 | CSS 行 |
|---|---|---|
| `.status-effect-icon` | 22px，line-height 1，flex-shrink 0 | :124-128 |
| `.status-effect-name` | **display:none**（名字只在 tooltip 出现） | :129-131 |
| `.status-effect-stacks` 层数角标 | bottom:2px left:4px；`#f0f4f6` monospace 9px 700；text-shadow `0 1px 2px #000`；文本 `×N`（U+00D7） | :132-142 |
| `.status-effect-time` 时间角标 | right:3px bottom:2px；`#c3cdd2` monospace 9px；text-shadow 同上 | :143-155 |
| `.status-effect-progress` 进度条 | bottom:0 高 2px；`background: var(--effect-color, #5a4d3f)`；opacity .7；`transition: width 0.1s linear`（唯一倒计时动效，平滑由 CSS 承担） | :156-164 |

`--effect-color` 由 JS 写在内联 style（SB:323）。
**没有 @keyframes**：条目出现/消失/到期/受击均无动画（grep 证实 game-style.css 全部 keyframes 与状态栏无关）；到期即随下次 render 直接消失。

## 4.3 条目模板（SB:322-329 逐字）
```js
html += `
    <div class="status-effect-item" data-effect-type="${effect.type}" style="--effect-color: ${effect.color};">
        <span class="status-effect-icon">${effect.icon}</span>
        <span class="status-effect-name">${effect.name}</span>
        <span class="status-effect-stacks">${stackText}</span>
        <span class="status-effect-time">${timeText}</span>
        <div class="status-effect-progress" style="width: ${progress * 100}%;"></div>
    </div>`;
```

## 4.4 render 算法与文本格式（SB:288-333）
| 条目形态 | HUD 时间文本 | progress | tooltip 时间行 |
|---|---|---|---|
| 毫秒计时 | `` `${Math.ceil(remaining/1000)}s` ``（向上取整+小写 s） | `duration>0 ? remaining/duration : 0` | `` `剩余 ${ceil} 秒` ``（带空格、“秒”） |
| `battleRemaining` 有值（按场） | `` `${n}场` ``（无空格） | **恒 0%** | `` `剩余 ${n} 场` `` |
| `persistent`（永久文本） | `durationText ?? '持续'` | **恒 100%** | `durationText ?? '持续至来源结束'` |
| 层数 | `` `×${stacks}` ``；`stacks===undefined` 时空串 | — | `` 层数：x${stacks} ``（全角冒号+拉丁 x） |
- 空栏：`innerHTML=''; container.style.display='none'`（SB:300-304）；非空先 `display='flex'`（:306）。
- 节流：过期即 `changed` 立即 render；否则 **100ms 至多一次整块 innerHTML 重建**（SB:272-278，`_RENDER_INTERVAL_MS=100` 语义；条目 DOM 无复用）。
- 名字内嵌层数（tooltip 头会看到“中毒 x3”+“层数：x3”双显——原样行为）：新条目 `` `${options.name||config.name} x${stacks}` ``（SB:170-173）；刷新时 `` `${config.name} x${stacks}` ``（**回退 config.name，丢弃自定义名**，SB:162-165）；`updateEffectStacks` 同式（:198-206）。
- 未知 type 回退：`{ icon:'❓', name:type, color:'#8a7d6b' }`（SB:133）；desc 回退 `'持续生效的状态效果。'`（:91）。现存非注册 type 全部显式传 options，不会踩 ❓，但迁移须保留回退。
- addEffect 合并优先级（SB:140-161）：`persistent`（remaining=duration=Infinity）> `battleRemaining`（remaining=0/duration=0，update 跳过倒数）> 毫秒取 `Math.max`。条目 id = `${type}_${Date.now()}_${random}`（:134）。
- update(dt)（SB:197-219）：空数组 return；倒序遍历 `remaining -= dt`；≤0 splice+render；persistent/battleRemaining 条目不倒数。
- 整栏 `clear()` 全项目唯一调用 = 新局 `game.js:264`（上一局不带到新局）；**换场/死亡/离地牢都不整清**。驱动：主循环 `game.js:1794 StatusBar.update(dt)`（每帧）。外部直接 render 仅 `dungeon-event-system.js:473`。
- 隐藏整栏的 body 类（game-style.css:166-188）：`map-mode`（GameScene 全屏地图）/ `expedition-preparing`（出征准备）→ `display:none!important`；`npc-dialogue-active`（NPC 对话，npc-dialogue.js:61）→ 与左侧整套 HUD 同隐。

## 4.5 Tooltip（buff 悬浮提示唯一实现，SB:55-122）
- 元素 `div#statusEffectTooltip` **appendChild 到 document.body**（:69，跳出 uiLayer 堆叠上下文——挂 uiLayer 会被 body 级面板遮挡，已知雷区）。
- 样式（:60-68 逐字）：
```
position: fixed; z-index: 99999; pointer-events: none; display: none;
min-width: 200px; max-width: 300px;
background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(240,240,240,0.9));
border: 2px solid rgba(0,0,0,0.2); border-radius: 8px;
padding: 12px 16px; box-shadow: 0 4px 16px rgba(0,0,0,0.4);
color: #2a2520; font-size: 13px; line-height: 1.6;
font-family: SimHei, "Microsoft YaHei", "黑体", sans-serif;
```
- 内容行序（:100-106）：① `${icon} ${name}`（700 / 15px / margin-bottom 6px）② desc（margin-bottom 6px）③ 层数行 `color:#8a6a3a`（仅 stacks!==undefined 时存在）④ 时间行 `color:#6a5a4a; 12px`。
- 定位（:107-117）：先 `display='block'` 量 `offsetWidth/Height`；`left = rect.right + 10`；若越右界（`left+tipW > innerWidth-8`）翻到条目左侧 `rect.left - tipW - 10`；`top = rect.top`；越下界钳 `innerHeight - tipH - 8`；最终 `max(8, …)` 钳左上。
- 事件：容器 `mouseover/mouseout/mouseleave` **事件委托**（`closest('.status-effect-item')`，render 重建 DOM 不破坏绑定；`mouseout` 需 `!item.contains(relatedTarget)`）。
- 注：`src/ui/status-tooltip-helper.js` 与 buff 无关（角色面板属性条 `.attr-tooltip`，system-ui.js:112-125）；`dungeonMapStatusBar` 是地牢选路 HP/MP 条。

## 4.6 图标渲染
条目图标=纯文本 glyph（emoji 或符号字符）；渲染只插值字符串。**没有 per-status png**。详见卷一 §2（emoji 全表 + 无变体选择符字形风险清单 + `assets/ui/icons/status.png` 系侧栏按钮图标勿混淆）。

---

# §5 隐藏机制清单（有机制代码但**从不进入状态栏**，或根本不走 statusEffects）

### A. 阵营门控导致“玩家看不见”的状态（机制存在、栏永无）
1. `magicVulnerability` 的 `apply`（DE:1099）**根本不写 statusEffects[]/不镜像 HUD**——纯 `_magicVulnerabilityStacks` 字段驱动；HUD 字典项（SB:20）实际只有 RTS 详情面板消费。
2. `magicResistanceShred`、`marked`、`camelFright`：只施加给敌方阵营 → 永不进玩家栏（status-bar 字典里也没有它们）。
3. 武器皮肤型 `slow`/`bind`（月蚀迟滞/星图迟滞/王猎锁定/葬潮束缚/时滞锚定/霜径迟滞❄️#91e9ff(怪→玩家，雪冢驮城兽霜径 value 0.35、≤450ms 逐帧短刷新)/镇暴压制🛡️(友→敌)）施加到敌人时不可见；**两大例外：`applyCripple`（DE:1060）与 `applyBleeding`（DE:1085）无阵营守卫直写玩家 HUD**——玩家给怪挂致残/流血会让怪物侧条目出现在玩家栏（串台缺陷，迁移时按真源阵营重写）；仅玩家被控时（束缚=狱卒/变异体3 对玩家、封蜡=哀蜡者对玩家等）才是设计内镜像。
4. 断链狱卒直调 `target.addStatusEffect('bind', ms)`（enemy-types/broken-cable-gaoler.js:294）——**绕过 applyBind**：玩家被此怪束缚时没有 HUD 条目/没有 ⛓️ 图标（实体名走字典默认“束缚”但 bar 不加）。已知不一致。

### B. 数据层机制（无状态实体，连 statusEffects 都不进）
5. 地牢事件数值本体：`player._dungeonBuffs[id]`（dungeon-event-definitions.js:1901-1935）——栏条目只是显示镜像；`consumeBattleBuffs`/`clearAllBuffs` 管生灭。
6. 献祭效果本体：`aggregateTributeEffects` 的 `_tributeEffects`（经验/承伤上限/生产/招募乘区等，tribute-effects.js），10 个 tribute* 栏条目只是 persistent 指示器；`_moonshadowTimer`、`_surviveCap` 等计时/上限全在数据字段。
7. `marbleHeal` / `ginsengHeal` 栏条目是**击杀触发指示**；真正回血回蓝逻辑在 `_marbleHealTimer/_marbleHealPerTick/_ginsengHealTimer` 字段与玩家 update 驱动（DE:386-420；player/update.js:598/611）。
8. 机制真源字段族（statusEffects 只是镜像！）：`_poisonStacks/_poisonTimer/_poisonTickTimer`、`_bleedStacks/…`、`_corrosionStacks/_corrosionDuration/_corrosionDefenseReductionPerStack`、`_magicVulnerabilityStacks/Timer`、`_chillStacks/_chillTimer/_chillSlowPercent`、`_freezeStacks/_freezeTimer`、`_burnStacks[]`（逐层源快照）、`_electrifiedStacks/Timer/Source`、`_hasteStacks/_hastePerStackMul`、`_weaponHasteMul`、`_inspireMul`、`_chainSpellStacks`、`_holyRenewalStacks/_holyRenewalTimers[]`、`_droneVulnerabilitySources: Map/_droneVulnerabilityData`、`_holyWard.value`、`_fearSource`（DE:88-96/386-420/743+/929+/968+/1023+/1091+/1108+/1170+/1219+/1282+/1340+/1425+）。
9. `statusImmune` 的“永久”变体（MAX_SAFE_INTEGER 条目）虽上栏，但**其效果（拦截）不显示被拦掉的内容**；炼药锅/矿车/墓碑/召唤物恒挂永久免疫（卷三 3.11）。

### C. 类似状态却不是状态的行动/承伤机制（迁移时别建条目）
10. 闪避无敌帧 `_dodgeInvincible`（免伤+免控，subsystems.js:110/571/2877）。
11. 冲刺/位移硬锁 `_dashStunned`（enemy.js:629 计入阻断；玩家 dash 锁见 update.js 移动链尾）。
12. 举盾防御态 `shieldSystem.defending`（移速 ×defenseMoveSpeedMultiplier，update.js:347-349/403-405；破盾走 stun 才算状态）。
13. 重甲套装自动格挡（heavy 30%/−80%、zhenyue 40%/−85%、tiangang 50%/−90%、oracle 60%/−90%；DE:227-239，飘“格挡!”，无状态条目）。
14. 盾兵 50% 格挡判定（DE:160-167，非状态）。
15. `_rangedDamageReduction`（远程物理减免乘区，DE:136-138）。
16. 建筑巨型杀手 `giant_slayer`（ODM 来源侧乘区，非状态）。
17. 女墙方向掩护 50%/传奇盾庇护（DE:252-261，最终减伤区，非状态）。
18. 月相标记/弹射锚计数/枪管校准等**武器内部状态机**（legendary-shotgun.js eclipseMarks、weapon-ricochet.js anchorHits 计数、craft calibrationHits）——阈值到达才转化为一次真实状态施加。
19. 普攻眩晕豁免判定与 `_stunResistFlash`（attack.js:67-104；豁免只有 300ms 闪光无条目）。
20. 毒气区暴露中（进区 <2000ms 的 `record.exposure` 累积期）：无任何状态与 HUD，出区即清零（world126-weather-runtime.js:258-320）。
21. 濒死/复活窗口 `_peachRevivePending`、`_worldPeachReviveUsed`（献祭复活数据位）。
22. 状态反馈漂浮字（`☠️ 中毒 +N层 #39ff14`、`🩸 流血 +N层 #9a3a3a`、`🔮 魔力易伤 +N层`、`⚡ 感电 xN #b98cff`、`❄️ 寒冷 xN`、`💫 眩晕！`、`😱 恐惧！`、`🧊 冻结！`、`🗿 石化！`、`⛓️ 束缚！`、`🦴 致残！`、`战术锁定`——EffectManager.FloatingTextEffect 体系，非状态非 HUD 条目）。

### D. 已注册但**从不被施加**的死条目/死字段
23. `buff`（statusEffects 型占位；仅 dungeon-event-system.js:487-511 遗留清理引用）。
24. `shield`（零施加零引用；护盾机制走 stamina 格挡系统）。
24b. **`_synergyPoisonChance` 死字段**：`ai/synergy-system.js:86/133` 写入、`:97/153` 删除，规则 `:188` 定义 `poisonChance:0.3/poisonStacks:1`，但**全 src 无任何读取点** ⇒ “毒性瘴气”协同的中毒从未生效（只有 `_synergyBleedChance` 被 enemy.js:918 消费）。迁移时不要照接线。
24c. **RTS 平行实现通道**：`world/world122-sim.js:1084-1093/:3406` 的 camelFrightReduction 走模拟层数值管线，**不经过 statusEffects/StatusBar**。

### F. 语义细节（易在重写时丢失）
- 同桶刷新只 max 数值不改名：`addStatusEffect` 的 `name/icon/color` **仅首次创建条目时写入**，后续弱来源无法覆盖强来源的名字（slow 桶 6 种皮肤、bind 桶 4 种皮肤互相按 max 刷新、value 取 max、stacks 覆盖）。UE 侧若按 type 建 GE，需要拆 ID 或带 tag 的独立条目，同时**净化白名单要同步改**（三套集合成员不同：圣光 SUPPORT_CLEANSE_TYPES 11 项含 waxSealSlow 不含 minePoison `holy-light-system.js:47-50`；圣所 12 项=+minePoison `sanctuary-domain-system.js:48-49`；圣裁 10 项不含 waxSealSlow/minePoison `holy-judgment-system.js:59-60`）。
- “永久”有四种写法且读取行为各异：`Infinity`（demonPrayer 实体侧）、`999999`（地牢事件 buff 实体侧、玩家 droneVulnerability）、`Number.MAX_SAFE_INTEGER`（statusImmune 授予）、HUD `persistent:true`（真不倒计时）+`battleRemaining`（不倒数、按场扣）。`getStatusEffectRemaining` 直接返回 remaining 原值。
- 感电净化必须**手工归零 `_electrifiedStacks`**（holy-light-system.js:140-148 与 sanctuary 同款硬置 0）——仅移除 statusEffects 条目不清层数计数，过载阈值判定仍会命中。腐蚀唯一安全清除口是 `clearCorrosion()`（DE:1013，通用到期又对 corrosion 特跳 :683）。
- 玩家眩晕 HUD 生命周期完全在玩家覆写侧（subsystems.js:2884-2886 remove旧+add新；到期清除只在 update.js:91-94）；基类 applyStun 不碰 HUD。侍从(Companion)自带独立 `statusEffects`/`addStatusEffect`（companion.js:136/303，无 HUD 双注册）与独立到期钩子 :344-352；inspire 基类版直接改 data.atk/maxSpeed（到期除回），侍从版走 `_inspireMul` 乘区——两套实现语义不同。

### E. 与旧文档不一致点（以代码为准）
25. `docs/buff-reference.md`（2026-08-26）缺 holyWard/marked/flameArmor/weaponHaste/camelFright/magicResistanceShred 等，且部分描述过时；迁移以本审计（代码快照）为准。
26. SB 无“排序/优先级”逻辑（旧项目里 buff/debuff 分列的想象不存在）；如 UE 侧要分区显示，属于**新需求**而非迁移复刻。
