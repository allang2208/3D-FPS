# UE 侧 StatusEffects（左上角 buff/debuff 栏）现状盘点

审计日期：2026-09-24 ｜ 审计范围：`D:\FPS3D\FPSGAME`（UE 5.8.2 工程）
性质：**只读盘点**，未修改任何工程文件（本报告为唯一写入物）。
对账用途：与旧 Phaser 项目 `gamedev/public/status-effects.*` 等比对，制定 100% 迁移清单。

关键源文件：

| 角色 | 文件 |
|---|---|
| 数据目录 | `Content\ColdSteelData\status_effects.json` |
| 显示组件 | `Source\FPSGAME\UI\StatusEffectsComponent.h/.cpp` |
| HUD | `Source\FPSGAME\UI\StatusEffectsHUD.h/.cpp`（含 `UStatusEffectTile`、`UStatusEffectsHUDSubsystem`） |
| 战斗机制中枢 | `Source\FPSGAME\Combat\CombatStatusFormula.h/.cpp` |
| 数值消费 | `Source\FPSGAME\Combat\CombatFormulaRuntime.cpp`、`Movement\FPSCharacterMovementComponent.cpp`、`Weapons\MeleeWeaponStats.cpp`、`Monsters\FPSCombatHealthComponent.cpp`、`Skills\ColdSteel*Model.cpp` |
| 数据层 buff（祭品/地牢） | `Combat\ColdSteelFormulaBonuses.cpp`、`UI\ColdSteelInventoryTypes.h`（`FColdSteelFormulaBuff`）、`Dungeon\DungeonAssembler.cpp` |
| 自动化验收 | `Source\FPSGAME\UI\StatusEffectsAudit.h/.cpp` |

---

## 1. 状态目录（status_effects.json）

- 实际路径与预期一致：`Content\ColdSteelData\status_effects.json`。
- 结构：顶层 `{ "effects": [ … ] }`，每条含 `type / icon / name / description / color` 五字段（color 为 `#rrggbb`，经 `FColor::FromHex` + SRGB 转换）。
- 加载点：`UStatusEffectsComponent::Definition()`（StatusEffectsComponent.cpp:13-23）。**static TMap 进程内缓存、只加载一次**；改 JSON 需重启进程生效。
- 条目总数：**33**。

| # | type | icon | name | color | description（摘要） |
|---|---|---|---|---|---|
| 1 | stun | 💫 | 眩晕 | #9a7a5a | 无法移动、攻击、使用技能与物品 |
| 2 | poison | ☠️ | 中毒 | #7a9a5a | 每秒受到层数点毒素伤害 |
| 3 | minePoison | ☣ | 矿毒 | #a1b052 | 矿洞毒气：每秒最大生命0.5%魔法伤害；离区残留≤3s，可净化 |
| 4 | slow | 🐌 | 减速 | #5a7a9a | 移动速度降低 50% |
| 5 | waxSealSlow | 🕯️ | 封蜡减速 | #ba9272 | 移速-20%持续2s；再命中只刷新不叠层 |
| 6 | buff | ✨ | 增益 | #9a9a5a | 获得临时增益效果 |
| 7 | shield | 🛡️ | 护盾 | #5a8a9a | 获得护盾，减免受到的伤害 |
| 8 | bleed | 🩸 | 流血 | #9a3a3a | 持续流失生命值 |
| 9 | corrosion | 🧪 | 腐蚀 | #9ab84f | 每层物理防御-5%；每次倒计时结束消退1层 |
| 10 | magicVulnerability | 🔮 | 魔力易伤 | #8a5a9a | 每层受魔伤+5% |
| 11 | droneVulnerability | 🛸 | 无人机易伤 | #5a7a9a | 每层受所有伤害+10% |
| 12 | marbleHeal | 🗿 | 大理石守护 | #8a9a8a | 击杀后1s内回复生命 |
| 13 | goddessBless | ✨ | 女神祝福 | #e8c878 | 本场战斗攻/防/移速提升，按场消耗 |
| 14 | demonPrayer | 🔥 | 恶魔祈祷 | #9a3a3a | 攻力大幅提升的恶魔交易，伴随代价 |
| 15 | fear | 😨 | 恐惧 | #6a5a8a | 失控远离恐惧源，每层移速再-33%（上限99%） |
| 16 | tributeSnowLotus | 🪷 | 雪莲祝福 | #9ad0ff | 本次地牢经验+25% |
| 17 | tributeGinseng | 🌿 | 人参回气 | #6a9a5a | 本次地牢击杀后1s回复最大MP5% |
| 18 | tributePeach | 🍑 | 蟠桃续命 | #e8a06a | 本次地牢死亡后3s以30%HP原地复活一次 |
| 19 | tributeDiamond | 💎 | 金刚不坏 | #7ab0e0 | 单次受伤不超过最大生命15% |
| 20 | tributeMoonstone | 🌙 | 月影庇护 | #b0a0e0 | 进战斗无敌；Boss/精英战物理魔法+5% |
| 21 | tributePhilosopher | 🪨 | 点石成金 | #e0c060 | 随机传说祭品（若已是传说则再得一份） |
| 22 | holyRenewal | 💚 | 圣光续疗 | #7aff9a | 每秒恢复最大生命1%×层数 |
| 23 | holyWard | 🛡️ | 圣佑 | #ffe7a3 | 期间降低受到的最终伤害 |
| 24 | chainSpell | 🔗 | 链式强化 | #8a7a6a | 下次施法魔伤与MP消耗按层数提高 |
| 25 | weaponHaste | ➤ | 命中动能 | #69e7e3 | P4040命中后移速+10%；再命中刷新 |
| 26 | chill | ❄️ | 寒冷 | #7ab8e0 | 每层-5%移速；层数加法叠加，最终乘算 |
| 27 | burn | 🔥 | 灼烧 | #ff6b35 | 每0.5s受施法者魔攻×0.5魔伤 |
| 28 | frozen | 🧊 | 冻结 | #a0d8ff | 无法行动；受非魔法伤害+50% |
| 29 | petrified | 🗿 | 石化 | #929292 | 停当前帧无法动作；受魔伤+50% |
| 30 | flameArmor | 🔥 | 灼锋焰甲 | #ff7a3a | 攻击附魔伤+火花；每0.5s灼烧周围；武器火焰粒子 |
| 31 | riposteInspiration | ⚔ | 反击激励 | #d8b882 | 弹反成功：近战攻速+20%、攻防耐力消耗-20%，6s，再弹反刷新 |
| 32 | runeMagicVulnerability | ◇ | 导魔易伤 | #e7e9ed | 受魔伤+10%持续10s；再命中刷新不叠层 |
| 33 | electrified | ⚡ | 感电 | #b98cff | 每层受电伤+3%；满5层过载：眩晕+电弧传导 |

icon 形态全部为 **emoji 或单字符文本字形**（💫 ☠ ☣ 🐌 🕯 ✨ 🛡 🩸 🧪 🔮 🛸 🗿 😨 🪷 🌿 🍑 💎 🌙 💚 🔗 ➤ ❄ 🔥 🧊 ⚔ ◇ ⚡），没有任何贴图路径。

---

## 2. 组件与 HUD 实现规格

### 2.1 `UStatusEffectsComponent`（StatusEffectsComponent.h/.cpp）

`FStatusEffectView` 字段（非 USTRUCT，普通 struct）：

```cpp
FName Type; FString Icon, Name, Description, DurationText;
FLinearColor Color = (0.5, 0.5, 0.4);           // 目录缺失时的默认色
float Remaining = 0, Duration = 0;
int32 Stacks = -1, Battles = -1;                 // -1 = 不适用
bool Persistent = false;
FString TimeText() const;
```

`TimeText()` 格式（.cpp:12）：
- Persistent → `DurationText`，空则 `"持续"`；
- Battles ≥ 0 → `"%d场"`；
- 否则 → `"%ds"`，取 `ceil(max(0, Remaining))`。

内部记录 `FRecord { FStatusEffectView View; double End; }`，成员 `TArray<FRecord> Records`；变更广播 `OnChanged`（`FStatusEffectsChanged` 多播）。

方法语义：
- `GetOrCreate(Owner)`（静态）：懒加挂组件（`NewObject`+`AddInstanceComponent`+`RegisterComponent`），任意 Actor 可用。
- `Notify(Owner)`：仅 `GetOrCreate` + 广播 `OnChanged`（供"活状态"组件驱动刷新）。
- `SetTimed(Type, Seconds, Stacks=-1)`：`Seconds<=0` ⇒ 等价 `Remove`。已存在同 Type 且原本是计时记录 ⇒ `End=max(旧End, Now+Seconds)`、`Duration=max(旧Duration,Seconds)`（**保留更长时长**）；若原为 persistent/battles ⇒ 重置为 `End=Now+Seconds`、`Duration=Seconds`。**Stacks 一律直接覆盖为入参**。转计时态（Persistent=false、Battles=-1），广播。
- `SetPersistent(Type, DurationText="持续", Stacks=-1)`：先删同 Type，再插入 Persistent 记录（无 End 语义），广播。
- `SetBattles(Type, RemainingBattles, Stacks=-1)`：先删同 Type；`Battles>0` 才插入；`Battles<=0` ⇒ 只删不插，广播。
- `Remove(Type)` / `Clear()`：删记录 + 广播。`Clear()` 在现有代码中**无游戏调用方**。

`Snapshot()` 过滤与排序（.cpp:27-35），HUD 唯一数据源：
1. **死亡即空栏**：Owner 的 `UFPSCombatHealthComponent::IsDead()` ⇒ 返回空数组（所有条目消失，含活状态）。
2. 活状态适配器先入：`UMaggotPoisonComponent.Stacks>0` ⇒ `poison` 卡片（Stacks、Duration=5、Remaining=`GetDecayRemaining()`，Description 追加 `" 每 5 秒消退 1 层；倒计时为下一次减层时间。"`）；`UHandBrainFearComponent.Stacks>0` ⇒ `fear` 卡片（Duration=3、Remaining=`GetRemainingSeconds()`）。
3. 然后遍历 Records：计时记录按 `End-Now` 计算 Remaining，`<=0` 即被跳过（**过期只在读取时隐藏，不主动删除**）；`Battles==0` 跳过。
4. 按 Type 去重（活状态优先于同名 Records）。
5. **无排序逻辑** = 呈现顺序为 poison → fear → Records 插入序。

过期驱动：组件自身不 Tick；计时过期靠下一次 `Snapshot` 过滤 + `UCombatStatusFormula::TickComponent` 的 `Expire` lambda 归零时调 `Remove`；HUD `NativeTick` 每 **0.1 s** 累积 `Clock` 触发一次 `Refresh`。

### 2.2 `UStatusEffectsHUD` / `UStatusEffectTile` / `UStatusEffectsHUDSubsystem`（StatusEffectsHUD.h/.cpp）

全部控件为运行时 `WidgetTree->ConstructWidget` 纯 C++ 构建，无 BP 资产。

**挂载与位置**
- `UStatusEffectsHUDSubsystem::OnWorldBeginPlay`：仅 GameWorld、非专用服务器；**0.25 s 重复定时器** `EnsureHUD`（等 Possess/重生）。
- `EnsureHUD`：首次 `CreateWidget<UStatusEffectsHUD>` + **`HUD->AddToViewport(45)`**（ZOrder 45）；`BoundPawn != PC->GetPawn()` 时 `BindPawn` 重绑（换 pawn/复活自动重连，HUD 实例复用）。
- `BindPawn`：解绑旧 `OnChanged`，`UStatusEffectsComponent::GetOrCreate(Pawn)` 后订阅 `Refresh`。
- **左上角**：HUD 根为全屏 `UCanvasPanel`，`Scroll` 画布槽位 `Position=(104,12)`、`Size=(252,44)` —— 即视口左上角偏移 **X=104px、Y=12px**（左侧让位给 HP/MP 球区域）。
- `RebuildWidget()` 包一层 `SDPIScaler`，`DPIScale = 1/ViewportScale`：**无视游戏 DPI 曲线，恒定 CSS 像素尺寸**（720p/1080p 可读尺寸一致）。

**格子（UStatusEffectTile）**
- `USizeBox` 包裹：`WidthOverride=54`、`HeightOverride=44`（**54×44 确认**）。
- 根 `UBorder Surface`（SelfHitTestInvisible）内容 Canvas：
  - `Icon` UTextBlock（是文本，不是 UImage！）：emoji 字体 22px（`C:/Windows/Fonts/seguiemj.ttf`，实际字号 ×0.75=16.5），居中，白色，矩形 `{0,2} 54×28`；
  - `StackText`：`ColdSteelUI::NumberFont(6.75, bold=true)`，色 `#F0F4F6FF`，`{4,30} 26×11`，文本 `×N`（`Stacks<0` 空）；
  - `TimeText`：`NumberFont(6.75)`，色 `#C3CDD2FF`，右对齐，`{20,30} 30×11`；
  - `Progress`：`UImage`（默认白刷被 `V.Color` 以 opacity 0.7 染色），`{2,40} 50×2`，宽度 `50*Ratio`；`Ratio`：Persistent=1、Battles≥0=0、否则 `Clamp(Remaining/Duration,0,1)`。
  - 子控件全部 `HitTestInvisible`。
- Surface brush = `ColdSteelUI::RoundedBrush(填充, 圆角7, 描边=V.Color, 描边厚2)`；填充常态 `#2A2520D9`、hover `#232A30F5`；描边 hover 时改 `#C4D3DAFF`。
- `NativeOnMouseEnter/Leave`：置 `Hover` → `Update(View)` → `HUD->ShowTip/HideTip`。
- 无任何 Tween/动画：唯一动效是 hover 换色 + 进度条随 0.1s 刷新步进。

**布局**
- `UWrapBox`：`bExplicitWrapSize=true`、`WrapSize=252`、`InnerSlotPadding=(12,6)` ⇒ 每行 4 格（54×4+12×3=252）。
- `UScrollBox`：固定高 44 ⇒ **常态只显示 1 行 4 格**；`ScrollbarThickness=(3,3)`、无 overscroll、`ScrollbarPadding=0`；条目数 **>4** 时滚动条 `Visible`（否则 Collapsed）；**条目数 =0 时整个 Scroll Collapsed（空栏隐藏）**。

**Tooltip（悬停浮层）**
- `UBorder Tooltip`：brush `RoundedBrush(#F8F8F8F2, 圆角8, 描边#00000033, 厚2)`，`Padding=(16,12)`；初始 `Collapsed`；画布槽 `ZOrder=2`，初值 `{168,12,260×160}`。
- 内容 `UVerticalBox` 四行（Noto→实际为 `simhei.ttf` 中文合成字体，AutoWrap，行底距 6px）：
  - `TipTitle` 15px（×0.75） `#2A2520FF` = Name；
  - `TipDescription` 13px `#2A2520FF` = Description；
  - `TipStacks` 13px `#8A6A3AFF` = `"层数：x%d"`（`Stacks<0` Collapsed）；
  - `TipTime` 12px `#6A5A4AFF` = Persistent→`DurationText`/`"持续至来源结束"`；Battles→`"剩余 %d 场"`；否则 `"剩余 %d 秒"`（ceil）。
- 定位（`ShowTip`）：高度 = 有层数 160 / 无层数 142；默认放 tile 右侧 `+10px`；`P.X+260 > Viewport.X-8` ⇒ 翻到左侧（`P.X -= tileW+280`）；`P.X∈[8, Viewport.X-268]`、`P.Y∈[8, Viewport.Y-H-8]`。
- `NativeTick` 中：玩家 `bShowMouseCursor=false` 时自动 `HideTip`（Alt 隐藏光标即收 tooltip）。
- `Refresh()`：条目数或 Type 序列变化才重建 tile，否则仅 `Update`；重建时 `HideTip` 并把 HoverTile 重挂 `ShowTip`。

---

## 3. 机制接入点全清单（按状态 ID 归组）

`Source\FPSGAME` 全量 grep `UStatusEffectsComponent / SetTimed / SetPersistent / SetBattles / Remove / Notify / GetOrCreate`，引用文件共 8 个：`CombatStatusFormula.cpp`、`HandBrainFearComponent.cpp`、`PlayerGuardBreakComponent.cpp`、`PoisonMaggotProjectile.cpp`、`FPSHolyRenewalComponent.cpp`、`StatusEffectsAudit.cpp`、`StatusEffectsComponent.cpp`、`StatusEffectsHUD.cpp`。*.uasset 文本检索无蓝图调用（ripgrep 对二进制可能不报告，标注为"未发现"）。

> 重要区分：HUD 只绑定**玩家 Pawn** 的组件。施加到怪物身上的显示记录（chill/frozen/electrified/runeMagicVulnerability）机制真实存在但**当前无可见 UI**（怪物无 HUD）。

### 玩家可见 / 玩家侧记录

| ID | 施加/移除（文件:行） | 机制（真实效果） | 完成度 |
|---|---|---|---|
| `stun` | 施加：`UPlayerGuardBreakComponent::Apply`（PlayerGuardBreakComponent.cpp:25 SetTimed）。调用方：`RuneSwordGuard.cpp:145`（格挡耐力耗尽破防 `BreakStunSeconds`）、`Mutant3Feral.cpp:215`（飞扑 `PounceStunSeconds`）。解除：`Release()`（timer）——**注意 Release 不 Remove 记录，靠计时过期隐藏**；`EndPlay` 清 timer | 完整：`SuspendWeaponForMenu`、`StopJumping`、`ConsumeMovementInputVector`、`StopMovementImmediately`、`SetIgnoreMoveInput/LookInput(true)`、`DisableInput`；恢复后若 RMB 仍按住自动 `BeginGuard` | 完整实现（机制+显示） |
| `poison` | 活状态只读：`Snapshot` 合成（StatusEffectsComponent.cpp:30）；`UMaggotPoisonComponent::AddStack/Tick` 仅 `Notify`（PoisonMaggotProjectile.cpp:103/108/117）。来源：毒蛆弹 `PoisonChance` 命中（:90） | 完整 DoT：每秒 `Stacks` 点伤害（`UMaggotPoisonDamage::StaticClass`），上限 20 层，每 5s 消退 1 层；死亡清零；**无 Remove/净化 API** | 完整实现（机制+显示，走适配器） |
| `fear` | 活状态只读：`Snapshot` 合成（:31）；`UHandBrainFearComponent::Apply/Tick/Release` 仅 `Notify`（HandBrainFearComponent.cpp:23/34/41）。来源：`HandBrainMonster.cpp:159` | 完整：`SetIgnoreMoveInput(true)`、`MaxWalkSpeed×max(0.01,1-0.33×Stacks)`、强制反向 `AddMovementInput` 远离威胁、取消 traversal、3s/层（≤3 层） | 完整实现（机制+显示，走适配器） |
| `riposteInspiration` | `UCombatStatusFormula::GrantRiposteGuard`（CombatStatusFormula.cpp:47 SetTimed(stacks=1)）；`TickComponent:63` 归零。调用：`RuneSwordGuard.cpp:130`（成功弹反，参数来自武器 `MeleeModifiers.RiposteSeconds/Speed/Stamina`） | 真实：`MeleeWeaponStats.cpp:69` 消费 `RiposteAttackSpeed()` 与 `RiposteStaminaMultiplier()`（攻速/耐力消耗） | 完整实现 |
| `chainSpell` | `AddChainSpell`（:129，+10s/层）、`ConsumeChainSpell`（:132 Remove）、Expire（:59）。调用：`FPSFireMagicComponent.cpp:118/138`、`FPSHolyLightComponent.cpp:106/125`、`FPSLightningComponent.cpp:104/174`、`FPSIceSpikeVolley.cpp:288`（施法者侧）；消费：`ColdSteelFireMagicModel.cpp:46`、`ColdSteelHolyLightModel.cpp:41`、`ColdSteelIceSpikeModel.cpp:41`、`ColdSteelLightningModel.cpp:40` 的 `ChainSpellStacks()` | 真实：下次施法魔伤与 MP 按层数放大，施法即消耗 | 完整实现 |
| `haste` | `AddHaste`（:124，时间+=Stacks×Seconds）、Expire（:59）。调用：`ColdSteelHolyLightModel.cpp:117`（治疗加速）、`FPSFireMagicComponent.cpp:138`、`FPSHolyLightComponent.cpp:125`、`FPSLightningComponent.cpp:174`、`FPSIceSpikeVolley.cpp:288`（施法加速天赋） | 真实：`MovementMultiplier ×(1+0.1×Stacks)` | **机制+显示完整，但 JSON 无 `haste` 条目**（见 §4） |
| `holyRenewal` | `UFPSHolyRenewalComponent::Apply`（FPSHolyRenewalComponent.cpp:16 SetTimed(Remaining,Count)）；`Tick` 归零 Remove（:24）。来源：`ColdSteelHolyLightModel.cpp:116`（圣光 RenewalStacks） | 真实 HoT：每秒 `最大HP×1%×Count`；免疫检查 `IsImmune`；死亡停 | 完整实现 |

### 施加到怪物（目标侧）——机制真实，显示记录存在但当前无 HUD 可见

| ID | 施加/移除 | 机制 | 完成度 |
|---|---|---|---|
| `runeMagicVulnerability` | `AddRuneMagicVulnerability`（:35-40 SetTimed(stacks=1)，只刷新不叠层）。来源：`RuneSwordComponent.cpp:428/432/923`、`RuneSwordWhirlwind.cpp:192`（导魔符文命中） | 真实：`MagicVulnerabilityMultiplier ×(1+Ratio)`（`CombatFormulaRuntime.cpp:62/81`、`FPSCombatHealthComponent.cpp:44`） | 机制完整；显示仅怪物记录（不可见） |
| `chill` / `frozen` | `AddChill`（:96-111 SetTimed；≥20 层⇒`frozen` SetTimed、扣 10 层；4 种怪物 `InterruptAttack`）；Expire（:58-59 Remove chill/haste/chainSpell/electrified）。来源：`ColdSteelIceSpikeModel.cpp:92`（冰锥，1 层/次） | 真实：`MovementMultiplier=max(0.01,1-0.05×Stacks)`；frozen ⇒ 移速 0（`FPSCharacterMovementComponent.cpp:39`）、非魔法伤害 ×1.5（CombatFormulaRuntime:62/83、FPSCombatHealthComponent:83 路径）、冻结参与受击控制时长（MonsterCombatComponent:143） | 机制完整；显示仅怪物记录 |
| `electrified` | `AddElectrified`（:112-120 SetTimed；满阈值清层并返回 true）。来源：`FPSLightningComponent.cpp:167`。过载：`FPSLightningComponent::Overload`（:115-126）→ `ReceiveStun`（怪物受击眩晕，**不挂 `stun` 显示**）+ 范围内电弧传导伤害 | 真实：`ElectricMultiplier=1+0.03×Stacks`（CombatFormulaRuntime:82）；过载眩晕+传导。注：**玩家被感电过载路径未见**（仅怪物目标） | 机制完整；显示仅怪物记录 |

### 有 CombatStatusFormula 机制、完全未接显示记录（无 SetTimed）

| ID | 机制入口 | 施加方 | 完成度 |
|---|---|---|---|
| `burn` | `AddBurn`（DoT：每 `TickSeconds(0.5)` 发一次魔攻×0.5 魔伤，多条独立计时）；调用 `FPSMeteorStrike.cpp:83`（陨星/焰甲相关）；消费在 CombatStatusFormula.cpp:88-93 | 仅 meteor | 机制完整，**状态栏无显示** |
| `bleed` | `AddBleeding` + Tick 每 1s 按 `HP×1%×层数` 物理跳伤、10s/层消退（CombatStatusFormula.cpp:41,74-87） | **无任何调用方** | 机制已写未接线，无显示 |
| `corrosion` | `AddCorrosion` + `CorrosionMultiplier`（每层物理 def -5%，倒计时逐层消退，CombatFormulaRuntime:61/78 消费） | **无任何调用方** | 机制已写未接线，无显示 |
| `magicVulnerability` | `AddMagicVulnerability`（每层受魔伤+5%，5s 逐层消退） | `RuneOrbBladeProjectile.cpp:119`（符文魔能弹） | 机制已接线，无显示 |
| `holyWard` | `AddHolyWard` + `FinalMultiplier`（最终伤害乘算减免，CombatFormulaRuntime:55/91 消费） | **无任何调用方** | 机制已写未接线，无显示 |
| （非目录）`MagicResistanceShred` | `AddMagicResistanceShred` + `MagicShred()`（穿透式魔防削减，CombatFormulaRuntime:61/78 消费） | **无任何调用方** | 机制已写未接线（本就不是 tile，对账时注意它没有 JSON 条目） |
| `flameArmor` | 技能侧真实：`FPSFireMagicComponent`（StartArmor/TickArmor :140-209：光环周期伤害、命中火花、Niagara aura+weapon FX、免疫检查、`ColdSteelQuickSlot.cpp:168` 剩余时间显示） | 火系技能施放 | 机制完整，**状态栏无显示**（JSON 有定义） |

### 数据层 buff（祭品 / 地牢）——完全绕开 StatusEffects 显示系统

`FColdSteelFormulaBuff`（ColdSteelInventoryTypes.h:61-70）：`Id / Effects(FName→float) / RemainingSeconds / Rarity / Battles / bTribute`。宿主 `FColdSteelProfile.FormulaBuffs`（:105）。

- 施加：`UColdSteelStatusModel::OfferTribute`（ColdSteelFormulaBonuses.cpp:62，物品 `category=="tribute"`，读 item JSON `effects` 表，**RemainingSeconds=1800s**，同 Rarity 互斥替换；BlueprintCallable，C++ 内未发现调用方，疑为 BP/UI 调用）；`ApplyDungeonFormulaBuff`（:72，Battles 场次）；`DungeonAssembler.cpp:436` 直接注入 `dungeon_relay_<RunId><RoomId>`（2 场、`defPercent +10`）。
- 消耗：`TributeEffect`（乘算/`*Flat` 加算，:34）、`DungeonEffect`（:40）→ `AdjustCombatStat`（atk/matk/def/mdef/crit 的 `%Percent` 键，:44-51）、`CombatMoveMultiplier`（:60，moveSpeedPercent）。
- 计时：`TickFormulaBuffs`（:84，祭品按秒衰减→过期 `SyncRuntime+ApplyToPawn`）；场次消耗在 `DungeonAssembler.cpp:388-394` 与 `CompleteDungeonFormulaBattle`（:78）。
- **结论：这些 buff 有真实数值机制（经验、回蓝、复活、减伤等效果键在 items.json 中定义），但从不调用 `UStatusEffectsComponent` 的 SetTimed/SetPersistent/SetBattles——左上角状态栏完全看不到祭品/地牢增益。** `tributeSnowLotus` 等 6 个 JSON 目录条目与 `goddessBless`/`demonPrayer`/`marbleHeal`/`tribute*` 家族处于"目录有、机制半有（键驱动）、显示无"状态。

### 其余检查结论

- `StatusEffectsHUD` 的 `UStatusEffectsHUDSubsystem` 是唯一 HUD 创建者（`AddToViewport(45)`），无第二处状态栏。
- `UStatusEffectsComponent::Clear()`：仅定义，无游戏内调用（死亡复活依赖换 pawn 后 `GetOrCreate` 新组件天然清空，见 §6 respawn 断言）。
- 玩家 `slow`（-50%）无真实机制来源；`weaponHaste`/`minePoison`/`waxSealSlow`/`droneVulnerability`/`petrified` 在整个 `Source\FPSGAME` **零引用**（含大小写变体 grep）。

---

## 4. 缺口视角（目录 ↔ 代码对账）

代码中实际出现的状态 ID 全集（去重，14 个）：

`stun, poison, fear, runeMagicVulnerability, riposteInspiration, frozen, chill, electrified, haste, chainSpell, holyRenewal, buff, shield, slow`
（后三个目前仅 `StatusEffectsAudit` 合成使用；`slow` 同时是 JSON 死条目。）

**A. 代码施加但 JSON 未定义（Definition 回退 `icon="?"`、`name=ID`、默认橄榄色 (0.5,0.5,0.4)、desc 空）：**
1. `haste` —— 唯一命中项。神圣治愈/施法加速真实使用，状态栏显示 "?" 卡。迁移时需在 JSON 增补（或改名为 weaponHaste？——不建议，语义不同：JSON `weaponHaste`=P4040 命中动能，未实现；`haste`=+10%/层移速，已实现）。

**B. JSON 定义但无任何代码施加（死条目，按严重度分组）：**
- 目录死条目（机制与显示皆无）：`minePoison`、`waxSealSlow`、`droneVulnerability`、`marbleHeal`、`goddessBless`、`demonPrayer`、`tributeSnowLotus`、`tributeGinseng`、`tributePeach`、`tributeDiamond`、`tributeMoonstone`、`tributePhilosopher`、`petrified`、`weaponHaste`（共 14）。
- 有机制、缺显示接线（半死条目）：`burn`（meteor 在用）、`magicVulnerability`（符文魔能弹在用）、`flameArmor`（技能在用）、`holyWard`、`bleed`、`corrosion`（后三者连施加方都没有）。
- 仅测试夹具：`buff`、`shield`（audit 专用 SetTimed/SetPersistent 载体）；`slow`（audit 专用 SetBattles 载体，且无 -50% 减速机制）。
- 注：祭品家族的"机制"以 `FormulaBuffs.Effects` 键值形式半存在（atkPercent 等通用键），与 JSON 的 `tribute*` type 字符串之间**没有任何映射代码**。

---

## 5. 图标现状与占位符最省事方案

- `icon` 字段 = emoji/单字符文本，存 JSON，`FStatusEffectView::Icon`（FString）。
- 渲染方式：`UStatusEffectTile::Icon` 是 **`UTextBlock`**，用 `seguiemj.ttf` 合成字体 22px（×0.75）绘制文本；**没有任何 UImage brush 参与图标**（唯一的 `UImage` 是进度条，用默认白刷 + `SetColorAndOpacity(V.Color×0.7f)` 染色）。
- 目录缺失回退同样走文本 "?"。
- **占位符图标最省事方案：直接往 `status_effects.json` 的 `icon` 写任意 emoji 或单字符（含 CJK 字符），零资产、零管线**。若旧 Phaser 项目用 SVG/PNG，UE 侧现阶段没有贴图通路；要上真贴图需把 tile Icon 改为 `UImage` 并按路径加载（参考 `ColdSteelSkillPage.cpp:118` 的 `FFileHelper::LoadFileToArray + FImageUtils::ImportBufferAsTexture2D` 从 `Content/ColdSteelData/<icon path>` 读图的既有做法）。
- 字体注意：HUD 内嵌绝对路径 `C:/Windows/Fonts/simhei.ttf`（中文）与 `seguiemj.ttf`（emoji），打包到非 Windows 或无这些字体的机器会掉字，迁移对账时可标记为已知债务。

---

## 6. 审计工具 StatusEffectsAudit（`-StatusEffectsAudit`）

- `UStatusEffectsAudit : UWorldSubsystem`；命令行含 `-StatusEffectsAudit` 且 GameWorld 时启动；BeginPlay+4s 起、0.05s 步进的 8 阶段状态机；**45s 超时** ⇒ 记 `completed_in_time` FAIL。
- 输出：`Saved/StatusEffects/<name>.png` 截图（`four-effects-hover`、`poison-decay`）；`Saved/StatusEffects/acceptance.json`（passed/failed/complete）；日志 `STATUS_ASSERT PASS|FAIL <name>`；结束 `RequestExitWithStatus`（全过=0，否则=1）。
- 前置：冻结毒蛆怪 AI、清弹幕；在玩家 pawn 上动态挂 `UMaggotPoisonComponent`（3 层）与 `UHandBrainFearComponent`（2 层）；合成 `buff`(SetTimed 12s)/`shield`(SetPersistent)/`slow`(SetBattles 2)/`stun`(SetTimed 1.5s)；模拟真实指针 hover 与滚轮、`LeftAlt` 按下/释放切换光标。

断言清单（迁移后必须继续全部成立）：

1. `empty_bar_hidden` — 开局 `VisibleEffectCount()==0`
2. `four_cards_from_live_poison_fear_and_display_records` — 活状态(poison/fear)+记录(buff/shield)混合渲染成 4 卡
3. `live_poison_stack_decay_countdown` — poison Stacks=3、Remaining>4、Duration=5
4. `live_fear_stack_countdown` — fear Stacks=2、Remaining>2、Duration=3
5. `original_persistent_label` — persistent 卡时间文本恒 `"持续"`
6. `original_104_12_position_54_44_tile_12_gap` — 首卡绝对位 (104,12)、尺寸 54×44、水平步距 66（54+12）
7. `real_pointer_hover_opens_poison_tooltip` — 真实鼠标 hover 打开对应 tooltip
8. `tooltip_within_viewport` — tooltip 位置 X,Y≥8
9. `refresh_merges_type_preserves_longer_duration` — 同 Type 再 SetTimed 合并且**保留更长剩余时间**、Stacks 覆盖
10. `overflow_and_battle_count` — 6 卡溢出 + `"2场"` 场次文本
11. `real_mouse_wheel_reveals_overflow_row` — 滚轮可见第二行（随后 ScrollToStart）
12. `alt_release_hides_tooltip` — 释放 Alt（光标隐藏）收起 tooltip
13. `expired_effects_removed` — fear/stun/slow/buff 到期后消失
14. `poison_decay_updates_existing_tile` — 消退在原卡上更新（不重建）
15. `poison_still_applies_real_damage` — 显示期间真实掉血 >10、`TicksApplied>=5`
16. `fear_releases_movement_input` — fear 结束恢复移动输入
17. `death_hides_all_effects_and_tooltip` — 死亡清空全部卡与 tooltip（`ApplyDamage` + `UMaggotPoisonDamage`）
18. `actual_respawn_rebinds_same_hud` — 真实重生后**同一 HUD 实例**自动换绑新 pawn 且空栏
19. `respawn_new_effect_appears` — 新 pawn 上 SetTimed 立即出卡
20. `countdown_expiry_hides_empty_bar` — 短暂 buff 自然过期后空栏隐藏
21. `completed_in_time` — 45s 预算（超时报错路径）

---

## 附：与旧 Phaser 对账时的重点差异备忘（事实性）

- UE 侧状态栏 = "显示层 Records + 两个活状态适配器（poison/fear）"；机制层几乎全部在 `UCombatStatusFormula`（挂在受击者身上、纯 C++ 字段计时），两者只有 8 个 ID 有桥（runeMagicVulnerability、riposteInspiration、frozen、chill、electrified、haste、chainSpell、stun、holyRenewal —— 其中 5 个的目标是怪物，当前不可见）。
- `poison`/`fear` 不是 Records：由组件 `Snapshot` 实时合成，`Remove` 对它们无效（由各自组件的生命周期决定）。
- 死亡=全隐藏（含 Records），复活换 pawn=全清空。
- 场次（Battles）显示只有测试在写；`goddessBless` 一类"按场消耗"的真实数据走 `FormulaBuffs.Battles`，与状态栏无连接。
- 玩家护盾/格挡、矿毒区域、封蜡诅咒、无人机易伤、大理石守护、恐惧外其余控制类（petrified）在 UE 源码内零实现，需要与 Phaser 侧逐条确认"旧项目是否真的存在"再列迁移。
