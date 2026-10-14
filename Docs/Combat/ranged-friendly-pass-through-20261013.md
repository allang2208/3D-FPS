# 远程攻击穿过友方单位：逐项排查与接入

2026-10-13，用户要求：删除螺柱喷射前的卡通蓄力音；怪物和玩家的所有远程攻击均不受友方单位阻挡，并逐项排查。本文记录本轮源码/配置排查及制作，不代表游戏或联机测试。

## 共同规则

新增 `Source/FPSGAME/Combat/RangedAttackQuery.h/.cpp`。优先使用双方明确的 GenericTeamId；未配置双方队伍时沿用现有玩家/怪物阵营：玩家角色、玩家控制单位及 `Player / Friendly / Companion / Summoned` 为玩家方，带怪物战斗组件或 `Enemy` 的单位为怪物方。中立未知单位不自动视为友方。

友方的胶囊、骨骼碰撞，以及实际附着在友方身上的独立装备 Actor 都跳过。仅由玩家拥有、并未附着到单位的冰墙、门和建筑仍是实体障碍；不按 Owner 递归把建筑当作队友，也不修改单位的移动碰撞配置。

- 单射线/单扫掠：命中友方后忽略该 Actor，重新查询原始完整线段，保留友方身后的敌人、墙、楼板、门与原碰撞部位。
- 通道多扫掠：友方作为首个阻挡时重新查询，避免仅过滤结果却丢失后方接触。
- 对象多扫掠：已有完整接触列表，先过滤友方再选择最近碰撞。
- 友方不触发命中表现、落地引信、插箭或弹体销毁，也不消耗贯穿次数；射程仍按实际飞行距离计算。
- 不新增全场友军遍历、独立 Tick、资源加载或第二套攻击时钟。普通场景沿用一次查询，有友军实际相交时才重查。

`MagicOcclusion` 增加显式远程来源参数，范围/连锁调用使用施法者阵营。原有镂空栏杆规则继续独立存在；实体投射物仍按实际碰撞走，不因本次改动获得穿墙或穿楼板能力。

## 怪物逐项

排查以正式 F6 目录、角色攻击选择/释放入口、所有原生伤害调用和投射物类为入口，覆盖存量旧巫婆与当前 WitchRebuilt 共用路径。

| 怪物 | 远程或传播路径 | 本轮处理 |
| --- | --- | --- |
| 鼓囊 M-09 | 发现/起手视线、目标地面、抛物线预判、囊弹实际飞行、爆炸暴露 | BellowSacLobber / BellowSacProjectile 接入统一过滤；不能只改实际弹体而遗漏起手预判 |
| 螺柱 M-14 | 喷射起手、喷口出口、黏液弹飞行 | SpiralPillarM14 / SpiralPillarM14Attacks / M14MucusProjectile 接入 |
| 毒蛆 | 喷射起手、毒液弹、多次喷吐共用弹体 | PoisonMaggotMonster / PoisonMaggotProjectile 接入 |
| 巫婆（含 WitchRebuilt） | 普通毒弹、抛瓶、落地寻地、毒池边界及伤害遮挡 | WitchMonster / WitchProjectile 接入；抛瓶不在友军身上提前落地 |
| 盲祷者 M-07 | 法术起手/出口，火球、冰柱、闪电，火球爆炸暴露 | BlindSupplicantCombatMagic / M07MagicAttack 接入；保留头部到上半身的低遮挡判定 |
| 伏窥者 M-08 | 索敌解剖采样、空气炮起手、空气炮弹体 | LurkerM08Pursuit / LurkerM08AirCannon / M08AirCannonProjectile 接入 |
| 涡电匣 M-25 | 凝聚空间、起手视线、提前量、闪电和雷枪第一接触 | M25MagicComponent 接入 |
| 悬钟 M-09 | 起手视线、凝视光束的 Visibility/Pawn 两路扫掠、共振传播 | HangingBellM09 / M09Gaze 接入；两路均跳过友方，取剩余最近实体阻挡 |
| 百目炉渣 | 起手视线、眼部激光长度、激光逐目标遮挡、黑雾暴露 | HundredEyedSlagMonster / HundredEyedSlagSpecialAttacks / SlagBlackMist 接入 |
| 沉匣 M-10 | 吼叫起手/传播、后部毒气出口/视线、毒雾上升及暴露 | M10Mawcrawler / M10Howl / M10RearGas / M10PoisonGas / SlagBlackMist 接入 |
| 缚群 M-88 | 远距触手起手视线、移动尖端和末段触手扫掠 | BoundCongregate / BoundCongregateTentacle 接入；成功捕获后既有持续伤害不经过弹道 |
| 手脑 | 远距吼叫起手和范围逐目标视线 | HandBrainMonster::CanSee 接入 |
| 胖子僵尸 | 死亡脓池 | 原对象列表本就排除 Pawn，按实际地面三角形覆盖结算；无需新增弹体路径 |
| 毒液僵尸 SpitterZombie | 当前正式实现为随机近战及命中叠毒 | 源码名不能当成存在吐弹的证据；本轮没有新增旧 Godot 喷射行为 |
| 护士、三类无面职员、突变体-3、螳螂、大小皮肤手及现存犬类 | 当前攻击为近战、移动冲锋或身体飞扑 | 未发现独立远程弹体；身体移动/飞扑仍使用物理碰撞，不让怪物身体穿队友 |

共同感知也已排查：原生 AI sight 的首个友军可能阻止发现玩家。上述远程物种现在通过原有 10 Hz 知识服务枚举玩家并使用同一过滤视线补充发现；保留原警戒距离、视野角度、M08/M25 既有全向发现及被动受击发现延迟。

## 玩家逐项

| 类别 | 本轮覆盖 |
| --- | --- |
| 全部单持枪械、霰弹每颗弹丸 | FPSGAMECharacter 的近墙收枪判断、准星目标、相机至枪口、瞬时射线、射线穿透后续段；FPSBallisticsComponent 的所有飞行弹丸及命中表现 |
| 双持手枪、法杖副手枪 | PistolDualWieldAim / PistolDualWieldCombat 的双手瞄准与枪口，加共用弹道组件 |
| Super90 服务端发射 | ColdSteelSuper90Authority 的枪口遮挡与每颗弹丸目标，加服务端共用弹道 |
| 碎裂/跳弹词条 | FPSBallisticsShatter 的候选阵营及遮挡；飞行子弹沿用共用弹道，不被友军附件截断 |
| 弓及所有箭种 | BowWeaponComponent 准星射线、BowArrow 出生段和逐子步飞行；命中后的箭支回收遮挡仍是交互规则 |
| 火球 | 手部/杖尖凝聚避障、悬浮/飞行扫掠、命中目标与爆炸暴露 |
| 冰锥 | 凝聚空间、整组逐枚飞行、连续碰撞段、命中阵营 |
| 共用魔法预览 | FPSMagicPreview 准星选点、分段扫掠与实际弹道同口径 |
| 闪电及过载 | FPSLightningComponent 首目标、释放复查、连锁/过载视线及 ColdSteelLightningModel 阵营 |
| 雷暴领域、贯穿雷枪 | FPSElectricMagicComponent 候选、逐目标暴露、光束终点、贯穿目标/要害射线、放电源净空 |
| 圣光 | 敌伤/友疗的目标之间视线跳过旁站友军；保留主动选择友方治疗与 Alt 自愈，不把治疗目标过滤掉 |
| 陨星与火场 | FPSFireMagicComponent 地点选择、FireMagicArea 地面/顶板/传播与地面目标，FPSMeteorStrike 继续调用同一入口 |
| 龙息 | FireMagicArea 共用传播用于喷口避障、逐目标身体采样及可见火焰长度；友方不截断 |
| 暴风雪 | BlizzardEnvironment 原本跳过单位，本轮补齐友方附着部件；逐目标范围传播、空间采样及冰雹表现同口径 |
| 冰墙落下 | 落下净空跳过友方；合法落点、玩家占位、排挤与成墙后的实体碰撞仍属于建筑/地形合同 |
| 符文飞剑 | RuneOrbBladesComponent 瞄准/悬浮避障，RuneOrbBladeProjectile 飞行与命中阵营 |
| 裂斩波 | FPSRiftSlashProjectile 在原有贯穿身体逻辑前统一过滤友方及附件 |
| 蟠螭飞龙 | PanChiDragonFlight 在原有飞行伤害与墙面截断前统一过滤友方及附件 |
| 苍龙远距爪击 | RuneSwordTraceSettings 显式开启友方穿透，仅扩展攻击/爪击使用；普通近战维持既有接触规则 |
| 武器衍生连锁电击 | FPSMeleeLightningComponent 的连锁候选与遮挡接入共用阵营和查询 |
| 多人命中复核 | ColdSteelPlayerState 的命中视线跳过友方；服务端仍保留射程、实体遮挡及命中几何复核 |

当前 `gunsmith.json` 的 16 个枪械 ID 已逐项映射到以上共同路径：
`ue_m4a1`、`ue_akm`、`ue_qbz191`、`ue_m1911`、`ue_pit_viper2011`、`ue_g18`、`ue_dan_wesson715`、`ue_rsh12`、`ue_ash12`、`ue_m16a2`、`ue_a762`、`ue_svd`、`ue_pkm_lowpoly`、`ue_lmg201`、`ue_hk416`、`ue_super90`。
当前弓 `bow_dark`、长杖 `ue_apprentice_staff` 及其部件/弹种没有独立碰撞实现，分别复用弓箭、法术与副手枪路径。
四种当前箭种 `arrow_wood`、`arrow_broadhead`、`arrow_poison`、`arrow_serrated` 均走同一个 BowArrow 发射和飞行路径。

剩余原始查询逐项按用途排除：角色移动/接地/攀爬/飞扑、普通近战、建筑放置/玩家排挤、箭支拾取、脚步落点、弹壳/碎片、手电/瞄准激光与热成像观察、怪物听声遮挡、交互和装饰效果。它们不是另一个遗漏的远程伤害入口。`Plugins/ColdSteelNet/Source` 未发现额外射线、扫掠或独立伤害投射物实现。

## 螺柱喷射声音

`PresentState` 不再从喷射状态起点播放整段 `SpitSound`。`TickAttack` 使用既有秒制攻击时钟，在跨过 `SpitReleaseSeconds` 时从录音的 1.10 秒处播放喷射尾段；迟帧按已有进度 seek，专服不播放。中途退出喷射状态不会再从前摇预排一段释放声音。

此方案对已经加载的旧 SoundWave 同样有效，不依赖替换资产。原料保留用于恢复；作者脚本也把前 1.10 秒保持静音，避免后续重建恢复前奏。本轮没有重制其他螺柱声音。

## 构建与边界

本轮静态排查包含攻击入口、起手/瞄准、真实飞行、命中/传播、可视预览、服务端复核、正式目录及剩余查询用途。查询入口与枪/箭目录记录在 `Saved/RangedFriendly20261013/query-inventory.json`。所涉源码的差异空白检查返回 0，源码已落盘。

- `FPSGAME` Win64 Development 后台增量构建成功：`Saved/RangedFriendly20261013/build-game.log`，UBT 报告 `Target is up to date`、`Result: Succeeded`，4.56 秒。输出为 `Binaries/Win64/FPSGAME.exe`。
- `FPSGAMEEditor` Win64 Development 常规后台构建成功：`Saved/RangedFriendly20261013/build-editor.log`，已链接 `UnrealEditor-FPSGAME.dll`，`Result: Succeeded`，14.15 秒。
- 已有构建与 commandlet 运行时等待其结束，没有联系其他对话、终止进程或启动编辑器。共享工程的增量构建可能同时包含其他已落盘源码；没有回退、清理或提交并行工作。
- 螺柱声音通过原生播放入口删除前奏，正式音频资产保留；本轮无需重导音频或修改蓝图，不能把作者脚本修订称为新 WAV 已导入。

未运行游戏、PIE、自动行为或联机测试，未试听。用户体验和游戏行为由用户测试；不将源码覆盖或编译成功写成实机无遗漏验证。
