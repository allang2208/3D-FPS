# PKM 开火声接入与数值调参（2026-09-22）

## 1. 开火声

PKM 原先没有任何自己的开火声：`InitializeWeaponVisuals()` 统一走 `LoadAKMSound("S_AKM_Fire")`，
而 `LoadAKMSound` 对 PKM 分支返回 `/Game/Weapons/AKM/Audio/S_AKM_Fire`。也就是说旧 PKM 用的是 AKM 枪声。

- 源：`E:/无尽轮回/长期备份/2026-7-13-1/game-dev/assets/sounds/weapons/pkm_half_sec.wav`
  （原型内六处引用一致，确为 PKM 专用开火声；`pkm_ammo_steam_mixed.wav` 是过热/蒸汽音，未导入）。
- 源文件实测：PCM 16-bit，单声道，44.1 kHz，0.5000 s，峰值满刻度，全段 RMS 0.171177（−15.33 dBFS）。
- 与现有枪声参考 `S_AKM_Fire`（48 kHz 双声道，0.395 s，RMS 0.169819 / −15.40 dBFS）比较，
  全段 RMS 只差 **+0.07 dB**，因此**不做任何电平补偿、不改 WAV 内容**，直接用交付原文件。
- 导入资产：`/Game/Weapons/PKMLowpoly20260922/Audio/S_PKM_Fire`，`volume`/`pitch`/`sound_class_object`
  沿用 AKM 开火声设置，`looping=false`，`loading_behavior=FORCE_INLINE`。
  来源、散列与电平记录：`SourceAssets/PKMLowpolyAudio20260922/provenance.json`。

代码接入（`Source/FPSGAME/FPSGAMECharacter.cpp`）：读取 AKM 家族回退之后，PKM 命中时用专属路径覆盖
`FireSound`；资产缺失则保持 AKM 回退（不静音、不报错）。路径常量在
`Source/FPSGAME/Weapons/PKMLowpolyWeaponAssets.h::FireSoundPath`。

`SuppressedFireSound` 仍沿用既有的 M4 消音声路由，未改；PKM 没有专属消音录音，不做虚构资产。

## 2. 数值调参

口径：参考当前伤害最高的步枪 ASH-12（`base.damage=48`、射击间隔 0.13 s、射速 461 发/分），
机枪按用户指定把成长属性换成**力量 + 精神**，射速固定 **650 发/分**，腰射扩散保持比步枪高一档，
后坐与步枪同档。

| 项 | 旧值 | 新值 | 说明 |
| --- | --- | --- | --- |
| `fire_interval` | 0.1 s（600 发/分） | **0.092308 s（650 发/分）** | 用户指定的射速 |
| `damage` | 7 | **30** | 与公式 base 同口径，单发落入 ASH-12 同档 |
| `recoil` | 110 | **100** | 与步枪同档 |
| `camera_shake` | 110 | **100** | 与步枪同档 |
| `spread_mult` | 2.5 | 2.5（未改） | 步枪为 2，机枪保持高一档 |
| `bullet_speed` / `effective_range` | 350 / 150 m | 未改 | 用户未要求 |
| `mag_size` / 换弹 | 100 / 6.5 s / 7.5 s | 未改 | 弹链供弹定位 |

新增 `Content/ColdSteelData/combat-weapon-formulas.json` 的 `ue_pkm_lowpoly`：

```
伤害 = round(base' + 强化等级×enhanceFlat' + 力量×(strBase + strPerEnhance×等级)
                                        + 精神×(wisBase + wisPerEnhance×等级)) × (gunsmith 基础伤害 ÷ 公式 base)
```

`base=30`、`enhanceFlat=2`、力量 0.45（+0.075/级）、精神 0.45（+0.075/级）。
新值 ÷ 公式 base = 30 ÷ 30 = **1.0 倍**，即最终单发伤害就等于公式输出。
旧值 7 与公式 base 7 也是 1.0，但公式 base 极低（7+0.45×10+0.25×10≈14），
再乘 `damage/base` 后几乎全被 30 倍倍率主导，属于"加成越高越虚"的错误结构。

标定（装备无增伤、无附魔、无精通）：

| 强化 | 力量×精神 | 单发 | 与 ASH-12（417）DPS 比 |
| --- | --- | --- | --- |
| +0 | 10×10 | 39 | 484 / 417 = **1.16×** |
| +0 | 20×20 | 48 | 596 / 417 = 1.43× |
| +5 | 10×10 | 50 | 620 / 417 = 1.49× |
| +15 | 10×10 | 65 | 807 / 417 = 1.94× |

结论：0 强化同点位比 ASH-12 高约 16%（换 100 发弹箱 + 6.5 s 换弹 + 持械 33% 减速），
强化成长明显更陡（perEnhance 0.075 × 属性 + 2 固定/级）。**这是配置推算，不是实测 DPS。**

### 机枪归类

`items.json` 的 PKM `weaponType` 由 `rifle` 改为 **`machineGun`**，命中
`ColdSteelAdditionalMasteries.cpp` 既有的 `machineGun`/`machinegun`/`lmg` 分支，从此吃 **机枪精通**
（力量 +1/级、伤害 +1%/级、+1 固定/级）而不是步枪精通。目录里已有 `movementMultiplier` 承载第 3 节减速。

改归类带来两处副作用，均为有意为之：

- 不再获得步枪精通的 **智慧 +1/级** 与 **要害伤害 +1%/级**（用户指定机枪按力量+精神成长，不是要害流）。
- 不再获得步枪精通的换弹/固定伤分支；机枪精通有独立的伤害分支。

`source-combat-items.json` 的 `PKM.attackFormula` 保留了原型历史值（base 7 / str 0.3+0.045 / wis 0.25+0.04），
它**不参与运行时**：`ColdSteelEnhancementSystem::AttackFormula` 先查 `combat-weapon-formulas.json`，
按 `Item.Definition`（`ue_pkm_lowpoly`）命中新条目后直接返回。历史资料按归档决策保留，不清洗。

## 3. 机枪类持械 33% 移速惩罚

新增乘区，持有**机枪类**武器时行走／疾跑／瞄准／蹲行的四个速度上限统一 ×0.67。

- 配置：`skills.json` 的 `machineGunMastery.movementMultiplier = 0.67`（0 表示不配置，加载时钳制到 0–1.5）。
- 承载：`FColdSteelSkillDefinition::MovementMultiplier` → `FColdSteelSkillEffect::MovementMultiplier`
  → `UColdSteelStatusModel::MachineGunMovementMultiplier()`。机枪判定复用
  `WeaponMastery()` 的唯一入口（`weaponType=machineGun`），目录新增机枪不必再维护第二份清单。
- 生效：`FPSGAMECharacterProfile.cpp` 把 `PistolMovementMultiplier() × MachineGunMovementMultiplier()`
  合进同一个 `PistolMoveSpeedMultiplier`，四个速度上限与蹲行瞄准速度（`FPSGAMECharacter.cpp`）共用它。
  **乘区只在这一处出现一次**，没有第二层重复相乘。
- 表现：角色面板「步行/奔跑速度」行详情、技能页机枪精通页脚都写明 ×0.67 / 减速 33% 与"收起武器即恢复"。

### 3.1 副作用：滑铲静默失效（用户报告，2026-09-22 修复）

用户报告"持有 PKM 时不能滑铲了"。定位到入铲门槛用的是**固定值比实时速度**：

```cpp
if (IsMovingOnGround() && HorizontalSpeed() >= SlideMinimumSpeed) StartSlide(); else Crouch();
```

`SlideMinimumSpeed = 600`，而 `HorizontalSpeed()` 取实时速度，疾跑上限却是
`SprintSpeed 700 × PistolMoveSpeedMultiplier`：

| 状态 | 疾跑上限 | 固定门槛 600 | 结果 |
| --- | --- | --- | --- |
| 空手 / 工具 / 步枪 / 手枪 | 700 | 700 ≥ 600 | 可滑铲 |
| **PKM（×0.67）** | **469** | 469 < 600 | **不触发，退化成蹲下** |

所以这不是"移速变慢所以滑得短"，而是**跨不过门槛、机制直接消失**——469 差 600 有 131 cm/s（21.8%）。
滑铲在 gamedev 原型里并不存在（那里只有敌人沿墙滑动），没有原始设计可对照，是 UE5 版新增机制。
已确认翻越与闪避没有类似速度门，不受本乘区影响。

修复：门槛跟随同一个乘区缩放，并加一个下限。

```cpp
float SlideEntrySpeed() const
{
    return FMath::Max(SlideMinimumSpeedFloor,
        SlideMinimumSpeed * FMath::Min(PistolMoveSpeedMultiplier, 1.0f));
}
```

| 状态 | 疾跑上限 | 入铲门槛 | 余量 |
| --- | --- | --- | --- |
| 空手 / 工具 / 步枪 | 700 | 600（未变） | 100 |
| PKM（×0.67） | 469 | **402** | 67 |
| 假设 ×0.50 | 350 | 402（地板生效） | −52，**有意不触发** |

- `SlideMinimumSpeedFloor = 402`（用户指定），即 `600 × 0.67`，是这个门槛允许的最低值。
  乘区若更狠导致疾跑上限低于它，滑铲就是**被有意关掉**的，而不会又出现"按键变成蹲下"的静默失效。
- 乘区上限取 `1.0`：只允许惩罚方向下调门槛，手枪的移速加成不会顺带放宽入铲要求，
  保持"满速要求 600"这个基准不被加成破坏。
- 门槛收敛到 `SlideEntrySpeed()` 一个入口；`SlideCombatAudit` 与 `FPSGAMEGunplayAudit`
  原本各自写 `HorizontalSpeed() >= SlideMinimumSpeed`，现改为调用同一函数，避免实现与审计分叉。
- 滑铲助推仍按带惩罚的 `SprintSpeed` 计算：机枪滑铲初速 938 而不是 1400，
  与"重武器操控性差"一致（按用户选择保留该副作用）。
- 在 `RefreshMovementState()` 的疾跑上限处留了注释：这两个数值互相耦合，
  只改其中一个会让受影响武器再次静默失去滑铲。

## 4. 存量存档的归类同步

改判 `weaponType` 后，**旧存档里的 PKM 实例仍存着 `"rifle"`**（物品 Data 是存档时序列化的目录副本），
`WeaponMastery()` 会继续返回 `rifleMastery`，于是持械减速与专精结算都还按步枪走。

在 `ColdSteelProfileRuntime.cpp::ReloadProfile()` 增加一处目录归类同步（与既有符文/图标按目录刷新的分支同模式）：
目录里存在该定义且 `weaponType` 非空、与实例存值不同时才写回，写回即走既有的 A/B 校验提交。
伤害公式不受影响（按 `Item.Definition` 查表），需要同步的只有归类。

## 5. 开火声"阶段不连续"的排查与修复（2026-09-22 追加）
用户反馈开火声有阶段不连续感。逐段实测后定位到三个各自独立的成因。

### 5.1 素材本身（PKM）

交付的 `pkm_half_sec.wav` 是 **0.5 秒容器只装 64 ms 声音**：

| 区段 | 时长 | 内容 |
| --- | --- | --- |
| 0 – 50 ms | 50 ms | 数字静音 |
| 50 – 110 ms | 60 ms | 实际枪声（峰值 −2.6 dBFS） |
| 110 – 113.8 ms | 3.8 ms | 收尾，然后**从约 −12 dBFS 直接砍到数字零** |
| 113.8 – 500 ms | 386 ms | 数字静音 |

三个后果：前导静音让每发都相对射击时钟延后 50 ms；样本没有衰减尾，
650 发/分的间隔是 92.3 ms，于是每发之间留 **27 ms 硬静音**（一顿一顿）；硬截断本身是爆音。
另外整文件 RMS 被静音稀释，让它看起来与 AKM"只差 0.07 dB"，
实际**有声段 RMS 是 −6.46 dBFS，比 AKM 的 −15.48 dBFS 高 9 dB** —— 之前的电平核对口径是错的。

修复（`author_audio.py`，可复现）：

- 按静音边界裁掉前导静音与硬截断，保留完整瞬态，不动音高/时长/音色（攻击段不做 EQ）。
- 用主爆音自身分频段零相位滤波 + 平滑指数衰减（τ 75/45/28 ms）重建 65 ms 尾音，
  并按拼接处 RMS 对齐后再交叉淡化 10 ms，避免电平台阶。
- 峰值归一到 0.6025，与 AKM 参考一致，保持全枪族峰值口径；运行期音量乘数不变。
- 输出 0.130 s，**最长低电平段落 0.5 ms**（原为 27 ms 静音），包络最小 −34.8 dB、无零陷。

### 5.2 单声部硬切（系统性问题）

`FireShot()` 三条播放分支行为不一致：

| 分支 | 武器 | 行为 |
| --- | --- | --- |
| 变体库 `PlaySound2D` + concurrency 6 | M4 / QBZ191（消音同） | 每发新声部，自然叠尾 |
| `M4FireVoice->Stop(); Play()` | PKM（以及手枪） | **每发硬切一个声部** |
| `PlaySound2D` | AKM / A762 / M16 | 每发新声部 |

PKM 因为 `bUsingM4Infima` 为真，走的是**硬切**那条；加上素材没有尾音，两者叠加就是顿挫的主因。

修复：新增开火语音池 `FireVoices`（`M4FireVoice` + 3 个轮转声部），
每发选一个**当前未在发声**的声部，以 15 ms `FadeIn` 从静音起音，绝不硬切在发声的声部；
池耗尽时对最旧声部用 15 ms `FadeOut` 优雅退休。M4 仍独占 `M4FireVoice`
（`MuzzleMigrationAudit` 按名字读这个组件），PKM 与其余武器改走池。

同一处硬切也存在于 `PlayMechanicalSound`（机械音/换弹音重触发时 `Stop()` 会在满幅切断），
一并改为 `FadeIn` 12 ms 起音。

### 5.3 修复过程中的两次自我纠错

- 第一版尾音用"末段 Hann 窗平铺"合成，包络出现周期性零陷；改为分频段零相位滤波后消除。
- 第一版漏了 `bUsingM4Infima` 对 PKM 也为真，语音池对 PKM 实际未生效；已按武器定义分流。
- `UAudioComponent::PlayQuantized` 需要 Quartz 时钟句柄，签名与预期不同（编译期发现），改用 `FadeIn`。

## 6. 质感提升（2026-09-22 第二轮追加）

连续性修好之后，用户要求再提升质感。同样先客观诊断，再按测量收敛。

### 7.1 诊断

与已接受的 AKM 参考逐频段对比，PKM 的问题是**倾斜错了**，不是简单的"太轻"：

| 频段 | PKM 占比 | AKM 占比 | 差 |
| --- | --- | --- | --- |
| 40–80 Hz | 5.9% | 8.0% | −2.1 pp |
| 80–160 Hz | 7.2% | 23.3% | **−16.1 pp** |
| 160–315 Hz | 22.9% | 31.0% | −8.1 pp |
| 315–630 Hz | 22.4% | 21.0% | +1.4 pp |
| 630–1250 Hz | 13.6% | 9.4% | +4.2 pp |
| 1250–2500 Hz | 8.0% | 3.7% | **+4.3 pp** |
| 2500–10000 Hz | 7.6% | 2.4% | **+5.2 pp** |

即**低频缺、中高频多**——又薄又硬。再按时间切片看，参考的"厚度"来源更清楚：
AKM 的低频占比在最初 15 ms 只有 5.1%，之后的主体段升到 60.0%
（40–315 Hz 4.2+22.6+33.2），是**低频在主体段才绽放**；而 PKM 原始素材 attack 与 body 频谱几乎一样
（低频 45.1% → 30.4%），没有这个绽放过程，所以缺乏"胸腔感"。

### 7.2 加工

- **修正 EQ**：只走"从 PKM 原始倾斜朝参考移动 60%"这一段，保留 PKM 自身性格。
  曲线：90 Hz −1.2 dB、200 Hz +1.8 dB、500 Hz +0.9 dB、900 Hz −1.2 dB、2400 Hz −0.9 dB、7 kHz −1.2 dB。
  **40–80 Hz 不动**——那在参考里是房间隆隆而不是枪声，跟着补只会变成闷响。
- **尾音重建为 85 ms（总长 0.150 s）**，四段零相位滤波各有衰减常数：
  50–200 Hz τ=110 ms（厚度）、200–800 Hz τ=70 ms、800–3500 Hz τ=32 ms（机械细节）、
  3500–9000 Hz τ=16 ms（尾端空气感）。低频长鸣、高频快收，复现参考的绽放而不拖泥。
- **瞬态塑形**：35 ms 之后的主体下沉 10%、主峰软化 30%，让爆音重音更突出。
- 峰值仍归一到 0.6025，与 AKM 参考一致，运行期音量乘数不变。

### 7.3 结果（全部为离线实测）

| 指标 | 第一版 | 本版 | AKM 参考 |
| --- | --- | --- | --- |
| 与参考的频段占比最大偏差 | 20.0 pp | **7.9 pp** | — |
| 40–315 Hz | 18.9% | **53.4%** | 59.9% |
| 630–5000 Hz | 55.0% | **22.5%** | 16.7% |
| −6 dB 时点 | 30 ms | **50 ms** | 30 ms |
| 最长低电平段 | 0.5 ms | 0.5 ms | 0.25 ms |
| 时长 / 峰值 / RMS | 0.130 s / 0.6025 / 0.1776 | 0.150 s / 0.6025 / 0.1778 | 0.395 s / 1.0 / 0.1677 |

尾音比射击间隔（92.3 ms）略长是有意的：连续射击时前发尾音自然垫在下一发下面。
`IsPlaying()` 选空闲声部的机制保证这种情况下不会硬切。

### 7.4 参数是怎么定的

不是手调，是扫描：`sweep_tone.py` 枚举 EQ 强度 × 尾部增益 × 尾部长度，
以"朝参考走一半"的频段占比为目标函数评分，再选 tilt 误差最小者。
第一版手调 EQ（+8 dB 低频架）严重过冲——低频占比从 18.9% 冲到 86%、中高频塌到 5.6%——
这个教训写在这里：**没有试听时，靠"感觉该加多少"很容易过冲，必须用目标函数约束**。
另外两次自我纠错：`tail_gain` 最初被拼接 RMS 匹配抵消（等于没生效），
以及把参考里 40–80 Hz 的房间隆隆误当成人声区内容，导致目标本身偏了。

### 6.1 响度提升（用户反馈实机偏小一倍）

用户要求放大一倍。**不能直接把 WAV 乘 2**：实测那样会有 **1.7% 的样本越过满刻度**
（原始峰值 1.205），产生硬削顶。

分两处给，合计正好 2×：

| 环节 | 增益 | 结果 |
| --- | --- | --- |
| WAV 归一到满刻度 | +4.40 dB（0.6025 → 1.0） | 峰值 1.0，不削顶；RMS 0.29508 |
| 资产的 `volume` 属性 | ×1.205（+1.62 dB） | 与上一项相乘 = **2.00×** |

两项相乘 1.66 × 1.205 = 2.00，即精确的 +6.02 dB。
`volume` 写在 `S_PKM_Fire` 资产上（`import-receipt.json` 已记录 `volume=1.205`），
WAV 本身保持满刻度、不再留静音 padding 造成的电平假象。
运行期音量乘数（`AKMSource::FireVolume × WeaponAudioGain`）**未改动**，全枪族仍共用同一口径。

## 8. 枪械详细介绍重写与显示文案同步（2026-09-22）

用户要求重写全部枪械的详细介绍，覆盖背景、特征，每条 200 字以内。

### 8.1 文案

原 `items.json` 的 `desc` 是"型号 + 口径 + 弹匣"式的一句话参数说明（26–44 字）。
9 把枪改为"背景 + 特征 + 实战定位"，并明确优缺点与适用距离：

| 枪械 | 字数 | 侧重点 |
| --- | --- | --- |
| M4A1 | 140 | AR-15 血统、轻快指向、衡量其他步枪的基准 |
| AKM | 121 | 耐操名声、单发停止作用、后坐代价 |
| QBZ-191 | 120 | 标配导轨、低后坐、稳健输出流派 |
| ASH-12 | 124 | 大口径无托、单发最高一档、屏息换命 |
| M16A2 | 107 | 三连发机制、点射命中率、精准派 |
| A762 | 139 | AK 基础上的改良、火力与操控的均衡点 |
| PKM | 123 | 弹链压制、举枪迟缓、钉阵地的武器 |
| M1911 | 119 | 百年经典、.45 近距停止作用、容量代价 |
| Dan-Wesson 715 | 132 | 高膛压左轮、单发全枪种最高、换弹最慢 |

最长 140 字，均在 200 字以内。介绍只讲性格与定位，射程/射速/后坐等实时数值仍由
`gunsmith.json` 提供、在提示里单独成行，避免两处口径打架。

**核对时改掉三处我自己写错的数据**（把每条数值说法都拿目录 `base` 对了一遍）：

| 原本写的 | 实际 |
| --- | --- |
| ASH-12「单发威力全枪种最高」 | 步枪中最高 48；左轮 DW715 的 68 更高 |
| M16A2「射击间隔全枪种最短」 | A762 才最短（0.0667 s / 900 发），M16A2 是 750 发 |
| DW715「单发伤害是手枪之首」 | 实为全枪种最高单发（68） |

### 8.2 只改 items.json 对已持有的武器无效

物品提示的说明文字走
`ColdSteelItemTooltipData` → `CombatItemFormula::Read(实例)`，读的是**物品实例 Data 里的快照**，
不是直接读 `items.json`。实测存档证实了这一点：

| 检查 | 结果 |
| --- | --- |
| 旧文案在 `ColdSteelPlayer_A.sav` | M4A1/PKM 各 1 处，AKM/DW715 各 2 处 |
| 新文案在同一存档 | **0 处** |
| 实例内 `desc` 字段 | 50 处 |

所以不修的话，已经持有的武器会一直显示旧介绍，只有新获得的物品才用新文案。

### 8.3 显示文案同步

在 `ColdSteelProfileRuntime.cpp::ReloadProfile()` 既有的按目录同步块里，
增加 `desc` 同步：目录有非空 `desc` 且与实例存值不同（或实例根本没有该字段）时写回，
并置 `Removed` 走既有的 A/B 校验提交。只同步纯展示文本，
不碰数值、改造件或附魔数据。

实例里**没有**该字段时也要补上——否则 `CombatItemFormula::Read` 的补全逻辑
会因为 `if(!Data->HasField(Pair.Key))` 而继续留着旧值。

### 8.4 生效链路（三步，顺序不能反）

1. **构建**：迁移代码必须先编进 `UnrealEditor-FPSGAME.dll`（22:29:05）。
2. **重启编辑器**：`items.json` 只在 `UColdSteelStatusModel::Initialize()` 时读一次并缓存，
   所以编辑器启动必须晚于文案修改。
3. **进入游玩**：编辑器不创建 game instance，`UColdSteelStatusModel` 就没有实例、
   `ReloadProfile()` 不会被调用。实测查证：编辑器里 `game instance: None`。
   用 MCP 的 `EditorAppToolset.StartPIE` 启动一次 PIE 才触发迁移。

### 8.5 结果（写盘实测）

| 检查 | A 槽 | B 槽 |
| --- | --- | --- |
| 新 M4A1 / PKM / ASH12 / M16A2 / QBZ-191 / A762 | 0 | **各 1 处** |
| 新 AKM / DW715 / M1911 | 0 | **各 2 处** |
| 旧 M4A1 / PKM | 1 | **0** |

`ColdSteelPlayer_B.sav` 更新于 22:30:38（135203 字节），A 槽保留 22:24:25 的旧快照。
按 A/B 双槽的 generation 选新规则，读取时用的就是含新文案的 B 槽。

### 8.6 近战三把（第三轮补充）

用户要求继续，把同样的口径补到三把双手剑上：

| 武器 | 字数 | 侧重点 |
| --- | --- | --- |
| 苍蓝星辉·双手符文剑 | 115 | 符文自充能设定、三段连击/蓄力/格挡、模块化长线重铸 |
| 寒晶·双手剑 | 118 | 智力与精神各 10% 转附加魔法伤害、法术配点收益最高、侵蚀已固化 |
| 高地·双手剑 | 127 | 高地工匠形制、与符文剑同档的稳健替代、靠距离与节奏 |

全部 12 条介绍最长 140 字（限 200）。

**又改掉两处我自己写错的说法**：

| 原本写的 | 实际 |
| --- | --- |
| 高地剑「攻击距离在双手剑中偏长」 | 三把双手剑触及**同为 180 cm**，属同档 |
| 寒晶剑「无法再安装普通侵蚀符文」 | 机制是 `ColdSteelFrostRunes::Upgrade()` 把 `erosion_rune` **转成** `spirit_burst_rune`，故改为"插入侵蚀符文会被转化为精神迸发" |

近战文案在 22:33 才写入，而存档最后一次提交是 22:31:20，
因此**这三条尚未进入存档**，实测两槽命中数均为 0；需要再走一次 §8.4 的第 2、3 步。

### 8.7 文案口径修订（第四轮，用户裁定）

用户提出两条要求：

1. **不要用"最""第一第几"这类设定词** —— 后续还会加武器，排行式说法会互相冲突。
2. **现实存在的武器参考百科那样论述；剑类奇幻武器编写背景。**

于是把 12 条按来源分成两类重写：

| 类别 | 武器 | 写法 |
| --- | --- | --- |
| 现实存在 | M4A1、AKM、QBZ-191、ASH-12、M16A2、PKM、M1911、Dan-Wesson 715 | 补回真实设计者、自动原理、服役背景，再落到游戏内手感与定位 |
| 虚构 | A762（Meshy 生成枪体，非现实型号）、苍蓝星辉·双手符文剑、寒晶·双手剑、高地·双手剑 | 编写背景：边境工坊仿制改型、苍蓝之地符文匠、永冻矿脉结晶、高地工匠同门 |

**清除的排行与跨型号依赖表述**（新武器一加即失效）：

| 原表述 | 改为 |
| --- | --- |
| M4A1「流通量最大」 | 「常用作衡量其他步枪的参考」 |
| AKM「适应性最强…之一」 | 「适应性很强的近战火力平台」 |
| QBZ-191「低后坐流派的首选」 | 「低后坐流派容易上手的平台」 |
| ASH-12「单发威力最高一档」「后坐最大」「射程最短」 | 「用单发威力换掉对面」「后坐与镜头震动沉重」「有效射程不长」 |
| M16A2「射速处于上位」 | 「连发节奏偏快」 |
| A762「介于 AKM 与 M4A1 之间」 | 「火力与操控都不偏废」（去掉跨型号引用） |
| PKM「全枪种最高的持续火力」「耗时最长」 | 「不间断的压制火力」「换弹耗时偏长」 |
| DW715「全枪种之首」「射击间隔最长」 | 「单发威力扎实」「转轮结构让它天生射速慢」 |
| 寒晶剑「收益最高」 | 「能从中拿到可观收益」 |

第三轮我把现实背景写没了（改成"废墟里""旧大陆工坊"），本轮按用户裁定恢复为百科口径。
一条保留待确认：M16A2 文案里提到 **M16A1**，那是该枪现实中的前代型号、属百科常规写法，
不是游戏内排行；扫描会命中，但判断可以保留。

全部 12 条最长 147 字（限 200）。

### 8.8 写入存档实测（第四轮）

按 §8.4 的链路重走一次，并用 MCP 逐条核对：

| 步 | 操作 | 结果 |
| --- | --- | --- |
| 1 | 关闭编辑器（`request_exit.py` 正常退出请求） | 编辑器退出，存档未受损 |
| 2 | 重启编辑器 | 启动 22:36:43，晚于 `items.json` 的 22:35:13，故内存里是新目录 |
| 3 | MCP `EditorAppToolset.StartPIE`（`warmupSeconds=14`） | 迁移执行并写盘 |
| 4 | MCP `EditorAppToolset.StopPIE` | **本次未崩溃**，编辑器存活 |

`ColdSteelPlayer_A.sav`（136355 字节，22:37:12）**12/12 条**全部命中新文案
（M4A1 1 处、AKM 2 处、QBZ-191 1 处、ASH-12 1 处、M16A2 1 处、A762 1 处、PKM 1 处、
M1911 2 处、DW715 2 处、符文剑 1 处、寒晶剑 1 处、高地剑 1 处）。
B 槽保留上一代快照，属 A/B 校验事务的正常轮换。

## 9. 武器「特殊性质」段落（第五轮，用户要求）

用户要求在详细介绍下新增一段说明武器特殊性质，并用**不同颜色的字**显示。

### 9.1 数据归属：放枪匠目录，因此免迁移

`desc` 走物品实例快照、必须迁移才能更新；`traits` 放**枪匠目录**（`gunsmith.json` /
`melee-gunsmith.json`），而目录是每次读盘解析的，所以改 `traits` **直接生效、不需要迁移**。
这是刻意的选择：以后加武器写 `traits` 就行。

`icon` 只是语义标签，由 UI 层映射颜色，因此新增武器不必改 C++：

| icon | 颜色 | 用于 |
| --- | --- | --- |
| `special` | `#176C86` | 特殊攻击模式、键位技能 |
| `magic` | `#6B4FA8` | 魔法伤害与冷却、符文 |
| `mechanic` | `#0F7B6C` | 供弹、后坐、弹匣、开镜 |
| `drawback` | `#B82020` | 代价 |
| `neutral` | `#697278` | 其余特性 |

调色板加在 `ColdSteelUIStyle.h`，与既有 `ItemTooltipPositive/Negative` 分开，
不影响现有参数行配色。

### 9.2 改动文件

| 文件 | 改动 |
| --- | --- |
| `ColdSteelUIStyle.h` | 新增 5 个 `ItemTrait*` 颜色 |
| `ColdSteelItemTooltipData.h` | 新增 `FColdSteelTooltipTrait`；`FColdSteelTooltipContent` 加 `Traits` |
| `ColdSteelItemTooltipData.cpp` | 从 `ModifiableWeapon(...)->Source` 解析 `traits` |
| `ColdSteelItemTooltipLayout.cpp` | `TraitColor()` 映射 + 「物品说明」段之后渲染「特殊性质」段 |
| `MeleeGunsmith.cpp` | 近战目录条目改为对象并保留 `Source`；兼容旧字符串写法 |
| `gunsmith.json` | 10 把枪加 `traits` |
| `melee-gunsmith.json` | 3 把剑加 `traits` |

**两个容易漏的坑**：

- `UGunsmithSystem::Weapon()` 只查枪械表，近战在 `MeleeWeapons` 里，所以工具提示必须用
  `ModifiableWeapon()`；用 `Weapon()` 的话近战永远没有这一节。
- 近战目录的 `weapons` 原本是**纯字符串数组**且没有 `Source`，已改成对象数组
  （`{"id":..., "traits":[...]}`）并保留原始 JSON，同时兼容旧的纯字符串写法。

### 9.3 已写入的性质（每条都按代码/目录核实）

- **符文长剑**：命中减全部技能冷却 0.5 s（剑身Ⅱ 金色符文再 +0.5 s，同一挥只结算一次）
  · G 键 4 把环绕飞剑，驻留 30 s、逐把射向准星、（武器攻击＋魔攻）×1.2
  · 射完或超时进 15 s 冷却，击杀可缩短
- **寒晶剑**：智力×10%＋精神×10% 转附加魔法伤害、随连击/重击倍率放大
  · 精神迸发符文使该段翻倍 · 侵蚀符文会被自动转化为精神迸发
- **PKM**：**移动速度 −33%**（机枪类持械）· 弹链 100 发弹箱、间隔 92 ms
  · 瞄准 450 ms 偏慢、腰射散布大于步枪
- **M16A2**：三连发（组内 80 ms、组间 180 ms）
- **A762**：间隔 67 ms、后坐 75、稳定性 1.25 倍
- **其余枪械**：击发方式与间隔、弹匣、后坐/散布特征、可改造槽位

**未给 `ue_svd` 写 `traits`**：它只存在于枪匠目录、`items.json` 里没有，
判断是并行会话在途的新武器，不属本次范围，也没有改它的任何数值。

## 10. 构建与验收边界

- 音频资产在编辑器内导入并保存落盘。首次导入时编辑器处于 PIE，UE 禁止写包；按用户授权停 PIE 后保存成功。
  之后改为 0.130 s 版本时，离线 `-run=pythonscript` commandlet 因编辑器已打开、包被占用而保存失败，
  改回经由互斥桥在编辑器内重导入，资产时长已确认为 0.1299999952 s。
- **Live Coding 在本工程不可用**：`CompileLiveCoding` 多次返回 `CompileNotStarted` / `Live coding canceled`，
  编辑器日志无任何 `LogLiveCoding` 服务器构建记录，`.lc.obj` 与 `patch_*` 时间戳不前进。
- 第一轮（导入 + 数值 + 移速惩罚）在用户正常退出编辑器后由 `Tools/Build/Build-Editor.ps1` 完成：
  226 个动作全部成功、无编译错误，8 个改动翻译单元均编译并链接进
  `Binaries/Win64/UnrealEditor-FPSGAME.dll`（2026-09-22 20:58:26）。日志 `Saved/BuildEditor/build-20260922-205618.log`。
- 第二轮（开火声连续性修复）在编辑器仍未关闭时先跑了一次编译验证，**抓到并修掉一个真错误**：
  `AKMSource::FireVoiceFadeSeconds` / `MechanicalVoiceFadeSeconds` 漏了命名空间限定（C2065）。
  修正后完整构建成功：
  `[1/4] Compile FPSGAMECharacter.cpp → [3/4] Link UnrealEditor-FPSGAME.dll → Result: Succeeded`，
  无编译错误，DLL 更新为 2026-09-22 21:09:56。日志 `Saved/BuildEditor/compilecheck2-20260922-210950.log`。
  这一步说明"靠肉眼审查源码"不足以替代编译器：限定名遗漏只有编译才能暴露。
- 清理了 commandlet 保存失败时残留在 `Saved/` 的两个 `S_PKM_Fire*.tmp`（SavePackage 中间产物）。
- 第三轮（质感提升）只改素材，**不涉及源码**：编辑器已关闭且包未被占用，离线
  `-run=pythonscript` commandlet 导入成功（`Success - 0 error(s)`），
  资产 `/Game/Weapons/PKMLowpoly20260922/Audio/S_PKM_Fire` 时长 0.1500000060 s、
  磁盘时间 2026-09-22 21:34:20。因此无需重新构建 DLL，第二轮源码仍是最新。
  `author_audio.py` 结果确定：同一输入重复运行得到同一 SHA-256
  （`d881e11131e862f2e12da748f58dc22c44477401a9cfacfa6fea6208aca3ccfd`）。
- 滑铲门槛修复（§3.1）改动 C++，在编辑器关闭状态下完成常规构建：
  `FPSGAMECharacter.cpp` / `SlideCombatAudit.cpp` / `FPSGAMEGunplayAudit.cpp` 编译通过并链接，
  `Result: Succeeded`、无编译错误，DLL 更新为 2026-09-22 21:38:43。日志
  `Saved/BuildEditor/slidegate-20260922-213744.log`。
- 响度提升（§6.1）与镭射修复（见 `pkm-laser-ads-20260922.md`）在同一次常规构建中完成：
  `TacticalDeviceComponent.cpp` 编译通过并链接，`Result: Succeeded`、无编译错误，
  DLL 更新为 2026-09-22 21:57:24。日志 `Saved/BuildEditor/laser-audio2-20260922-215718.log`。
  构建前先跑了一次编译验证并**抓到两个真错误**：`FRotator` 没有 `GetUpVector()`
  （C2039/C2737，要先转四元数），以及上一处 `set_world_transform` 的参数个数。
  这再次说明源码肉眼审查不能替代编译。
- 镭射"开镜到位后再对齐"的第二次修订（见 `pkm-laser-ads-20260922.md`）分两次构建：
  - `laser-ads-20260922-220920.log`：`Result: Succeeded`，DLL 22:09:41。
    这一版判定已经改成"ADS 到位后再对齐"，但对齐用的是**逐帧插值**——指数逼近，
    60 fps 下名义 0.08 s 实际要 0.283 s 才降到 2% 残余。属于逻辑缺陷，不是编译错误。
  - `laser-ads2-20260922-221000.log`：改为按经过时间解析求值后重建，
    `Result: Succeeded`、无编译错误，DLL 22:10:12（后一次链接覆盖为 22:10:12）。
- 显示文案同步（§8.3）的构建：`ColdSteelProfileRuntime.cpp` 编译通过并链接，
  `Result: Succeeded`、无编译错误，DLL 更新为 2026-09-22 22:29:05。
  日志 `Saved/BuildEditor/desc-sync-20260922-222850.log`。
  首次尝试的 `laser-audio-20260922-215657.log` 是 `Result: Failed (OtherCompilationError)`，
  即 `FRotator` 缺少 `GetUpVector` 那一处，修正版为 `laser-audio2-20260922-215718.log`。
- 近战介绍重写（§8.6）只改数据，构建返回 `Target is up to date`（0 action），
  日志 `melee-desc-20260922-223258.log`。
- 武器「特殊性质」段落（§9）改动 4 个 C++ 翻译单元，常规构建：
  `ColdSteelItemTooltipLayout.cpp`（26/112）、`ColdSteelItemTooltipData.cpp`（30/112）、
  `GunsmithSystem.cpp`（63/112）、`MeleeGunsmith.cpp`（74/112）全部编译通过并链接，
  `Result: Succeeded`、无编译错误，DLL 更新为 2026-09-23 07:49:00。
  日志 `Saved/BuildEditor/traits-20260923-074739.log`。
- **没有试听、没有实机测试、没有 PIE 验收**（用户规则：默认不主动测试）。
  连续性与音色倾斜由包络、频段占比和电平实测支撑；滑铲门槛由算术核对支撑
  （满速 700 ≥ 600、机枪 469 ≥ 402）；镭射方向由 socket/骨骼实测支撑。
  以上三项的实际手感与观感仍由用户判断。
- 素材为单声道 44.1 kHz，按引擎默认重采样，未做立体声化或音高变更。
  参考 `S_AKM_Fire` 是双声道，PKM 因此没有它的立体声宽度；crest 也仍低于参考
  （10.6 对 15.5 dB）——这两项都保留现状，需要时再单独处理。
