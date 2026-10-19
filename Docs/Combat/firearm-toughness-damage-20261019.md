# 枪械默认不造成韧性伤害（2026-10-19）

用户要求（2026-10-19）：枪械类武器除**狙击枪**、**左轮 715**、**RSH** 之外，命中目标均不造成韧性伤害。
经确认「狙击枪」按大口径狙击家族处理，同时包含目录里 `weaponTypeTag` 为「狙击步枪」的 SVD 与「精确射手步枪」的 SVCh。

这条规则接在 [枪械默认不造成怪物硬直（2026-09-17）](firearm-hit-stagger-20260917.md) 之后：那把闸门只管普通怪的硬直，精英以上的韧性条此前仍按枪弹结算；本轮把削韧通道也默认关掉。

## 规则

| 枪械 | 削韧（精英以上的韧性条） | 硬直（普通怪） |
| --- | --- | --- |
| SVD `ue_svd`、SVCh `ue_svch`、左轮 715 `ue_dan_wesson715`、RSH-12 `ue_rsh12` | 保留（目录声明 `"toughness_damage": true`） | 沿用 `hit_stagger` 闸门，缺省不硬直 |
| 其余全部枪械（突击步枪／手枪／机枪／霰弹枪） | **0**：不累积韧性、不刷新削韧恢复时钟、不破韧 | 同上 |

- 生命伤害、暴击、护甲穿透、弹药状态（毒／流血）、枪弹局部回弹（碎裂跳弹）一律不变，只把韧性通道按 0 倍率结算。
- 手持枪械发动的近战打击（快速进战的握把底／枪托砸击，`bMeleeStrike`）本来就按近战结算，仍照常削韧，不受本规则影响。
- 伤害仍然全额进怪物生命；跳弹、霰弹多弹丸、双持两手都走同一入口，不存在按弹丸数量叠加的例外。

## 实现

- **目录开关**：`Content/ColdSteelData/gunsmith.json` 的武器条目可选 `"toughness_damage": true`，缺省 `false`（枪械默认不削韧）。载入在 `UGunsmithSystem::Initialize`（`FGunsmithWeapon::bToughnessDamage`）。
- **快照**：沿用开火瞬间捕获的 `FColdSteelSkillShot::ItemDefinition`，已出膛的子弹不因换枪改变归属；碎裂跳弹继承同一 `ItemDefinition`，同样不削韧。
- **施加**：`UColdSteelStatusModel::ApplySkillWeaponHit` 对未声明削韧的枪械把削韧倍率压到 0（`ApplyHitWithToughnessScale(0.f, …)`）。受击端 `ReceiveToughnessBarHit` 因 `LastToughnessDamage<=0` 直接返回：不累积韧性、不刷新 3 秒回韧延迟、不触发破韧；普通怪继续走原 `hit_stagger` 闸门。

## 边界

- **破韧窗口内的短硬直保留**：目标已被近战或技能打破韧时，普通枪弹仍造成 0.2 秒短硬直（受击倍率折算 0.15–0.25 秒）。这是硬直不是韧性伤害，本轮未改动；需要一并取消再单独提。
- **新枪默认不削韧**：新增枪械不写这个键就没有韧性伤害；要让某把枪削韧，在它的目录条目加 `"toughness_damage": true`，不需要改 C++。
- 目录里其余枪械**不显式写 `false`**：与 `hit_stagger` 一样按缺省值读，避免每加一把枪都要补一行。

## 状态

源码与目录已落盘。`FPSGAME Win64 Development` 后台构建成功（`Result: Succeeded`，14:34 生成 `Binaries/Win64/FPSGAME.exe`，日志 `Saved/Diagnostics/FirearmToughness20261019/build-game.log`）。
`FPSGAMEEditor` 目标本轮未构建：构建期间有另一会话的 `UnrealEditor-Cmd` 在跑，Editor 构建脚本按既有规则拒绝在编辑器进程存在时启动，不结束他人进程。编辑器内验证前需要另起一轮 Editor 构建或走 Live Coding。
按用户规则未启动编辑器、未进行游戏测试或验收，交由用户测试。