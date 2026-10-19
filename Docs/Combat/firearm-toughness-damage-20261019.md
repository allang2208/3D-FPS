# 枪械默认不造成韧性伤害（2026-10-19）

用户要求（2026-10-19）：枪械类武器除**狙击枪**、**左轮 715**、**RSH** 之外，命中目标均不造成韧性伤害。
经确认「狙击枪」按大口径狙击家族处理，同时包含目录里 `weaponTypeTag` 为「狙击步枪」的 SVD 与「精确射手步枪」的 SVCh。

这条规则接在 [枪械默认不造成怪物硬直（2026-09-17）](firearm-hit-stagger-20260917.md) 之后：那把闸门只管普通怪的硬直，精英以上的韧性条此前仍按枪弹结算；本轮把削韧通道也默认关掉。

## 规则

| 枪械 | 削韧（精英以上的韧性条） | 硬直（普通怪） |
| --- | --- | --- |
| SVD `ue_svd`、SVCh `ue_svch`、左轮 715 `ue_dan_wesson715`、RSH-12 `ue_rsh12` | 保留（目录声明 `"toughness_damage": true`） | 沿用 `hit_stagger` 闸门，缺省不硬直 |
| 霰弹枪 M870 `ue_m870`、M4 Super90 `ue_super90`、Saiga 12K `ue_saiga12k` | **射程内**保留、**射程外 0**（`"toughness_damage": true` + `"toughness_range_limited": true`，见下节） | 同上 |
| 其余枪械（突击步枪／手枪／机枪） | **0**：不累积韧性、不刷新削韧恢复时钟、不破韧 | 同上 |

- 生命伤害、暴击、护甲穿透、弹药状态（毒／流血）、枪弹局部回弹（碎裂跳弹）一律不变，只把韧性通道按 0 倍率结算。
- 手持枪械发动的近战打击（快速进战的握把底／枪托砸击，`bMeleeStrike`）本来就按近战结算，仍照常削韧，不受本规则影响。
- 伤害仍然全额进怪物生命；跳弹、霰弹多弹丸、双持两手都走同一入口，不存在按弹丸数量叠加的例外。

## 后续修订：霰弹枪只算有效射程内的命中（2026-10-19 同日）

用户要求：霰弹枪在有效射程内可以造成韧性伤害，超出则不造成；同时改两把枪的有效射程。

| 枪械 | 有效射程（同时是削韧边界） | 装独头弹 ×2 后 |
| --- | ---: | ---: |
| M870 `ue_m870` | **45 m**（原 35 m） | 90 m |
| M4 Super90 `ue_super90` | 35 m（不变） | 70 m |
| Saiga 12K `ue_saiga12k` | **25 m**（原 35 m） | 50 m |

> 2026-10-19 晚射程分档后：M870 30 m、Super90 25 m、Saiga 20 m（独头 60 / 50 / 40 m），上表与下文括号里的旧数值同日被取代，见 [武器射程分档](weapon-range-bands-20261019.md)。削韧判定逻辑本身未变，只是边界跟着有效射程走。

> 同日再修订：三把霰弹枪有效射程各 +5 m → **M870 35 m、Super90 30 m、Saiga 25 m**（独头 70 / 60 / 50 m），削韧边界同步；见 [霰弹枪射程与伤害分化](shotgun-band-damage-20261019.md)。

- 判定用的距离与伤害衰减**同一口径**：取命中结果自带的射线起点到命中点。枪械命中端统一把射线起点写成枪口／发射点——弹道（`FPSBallisticsComponent`）写 `LaunchOrigin`，枪口顶住目标的即时命中写 `Muzzle`，服务端重建的远端命中写上报的 `AimOrigin`；射程取射手当前武器的有效射程（含弹种倍率）。
- **逐弹丸判定**：同一次射击里，近距离命中的弹丸照常削韧，飞过射程才命中的弹丸不削韧，两种可以同时出现。
- 射程边界随弹种走：装独头弹时有效射程 ×2，削韧边界同样 ×2（M870 90 m、Super90 70 m、Saiga 50 m）。
- 拿不到有效射程的命中（射程 ≤ 0）按超出射程处理，不削韧。
- 射程外只关削韧：生命伤害照常按衰减曲线结算；普通怪仍按 `hit_stagger` 缺省不硬直、不累积（霰弹枪没有开 `hit_stagger`）。

## 实现

- **目录开关**：`Content/ColdSteelData/gunsmith.json` 的武器条目可选 `"toughness_damage": true`，缺省 `false`（枪械默认不削韧）；霰弹枪再加 `"toughness_range_limited": true`，表示只在有效射程内削韧。载入在 `UGunsmithSystem::Initialize`（`FGunsmithWeapon::bToughnessDamage` / `bToughnessRangeLimited`）。
- **命中距离**：不写进开火快照。`UColdSteelStatusModel::ApplySkillWeaponHit` 在每次接触时用 `FVector::Dist(Hit.TraceStart, Hit.ImpactPoint)` 与射手的 `EffectiveWeaponRangeCM` 现算，因此单机、主机弹道与服务端重建的远端命中走同一判定，权威端也不采信客户端的语义位。
- **快照**：沿用开火瞬间捕获的 `FColdSteelSkillShot::ItemDefinition`，已出膛的子弹不因换枪改变归属；碎裂跳弹继承同一 `ItemDefinition`。
- **施加**：`UColdSteelStatusModel::ApplySkillWeaponHit` 对未声明削韧的枪械、以及超程的霰弹枪命中，把削韧倍率压到 0（`ApplyHitWithToughnessScale(0.f, …)`）。受击端 `ReceiveToughnessBarHit` 因 `LastToughnessDamage<=0` 直接返回：不累积韧性、不刷新 3 秒回韧延迟、不触发破韧；普通怪继续走原 `hit_stagger` 闸门。

## 边界

- **破韧窗口内的短硬直保留**：目标已被近战或技能打破韧时，普通枪弹仍造成 0.2 秒短硬直（受击倍率折算 0.15–0.25 秒）。这是硬直不是韧性伤害，本轮未改动；需要一并取消再单独提。
- **新枪默认不削韧**：新增枪械不写这个键就没有韧性伤害；要让某把枪削韧，在它的目录条目加 `"toughness_damage": true`，不需要改 C++。
- 目录里其余枪械**不显式写 `false`**：与 `hit_stagger` 一样按缺省值读，避免每加一把枪都要补一行。

## 状态

源码与目录已落盘。首轮 `FPSGAME Win64 Development` 后台构建成功（`Result: Succeeded`，14:34 生成 `Binaries/Win64/FPSGAME.exe`，日志 `Saved/Diagnostics/FirearmToughness20261019/build-game.log`）；霰弹枪修订后再次构建成功（`Result: Succeeded`，15:29 重新生成同一个可执行文件，日志 `Saved/Diagnostics/ShotgunToughness20261019/build-game.log`）。
`FPSGAMEEditor` 目标两轮都没有构建：期间一直有别的会话在跑 `UnrealEditor-Cmd` 或占用构建互斥，Editor 构建脚本按既有规则拒绝在编辑器进程存在时启动，也没有结束他人进程。编辑器内验证前需要另起一轮 Editor 构建或走 Live Coding。
按用户规则未启动编辑器、未进行游戏测试或验收，交由用户测试。