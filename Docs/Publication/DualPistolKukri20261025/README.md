# 主手手枪＋副手尼泊尔弯刀 双持（待机、ADS、快速近战单次突刺与副手上挑）

本批公开手枪＋副手弯刀（`ue_kukri` 放入副手槽）双持的第一人称动作：BV1hQnh6hEio
参考视频的刀＋枪交叉持握待机与 ADS、快速近战（F）的单次左手突刺——参考 40.33-41.00 s
逐帧配准，命中按**副手武器物理面板（基础＋附加）的 200%** 结算——以及
快捷栏 `swordUppercut` 技能的副手上挑（主手弯刀上挑的镜像共轭，出手时持枪右手
按逐键取景让开刀路）。作者源：`SourceAssets/DualPistolKukri20261025/`（拟合脚本、
键表导出、参考相机/模糊配准、集成补丁重生）。

**此提交不是完整本机工程的可构建检出。** 共享宿主只发布 `Integration/` 下按
HEAD 对齐的差量补丁（`integration-prerequisites.json` 给出每份的规范化前置/结果
SHA-256；哈希不符时合并语义，不覆盖现有文件）。Fab 弯刀资产不随批再分发。

## 直接进入运行树的内容

- `Source/FPSGAME/Weapons/Kukri/OffhandKukriComponent.h/.cpp`：副手弯刀组件本体——
  V9 裸臂 IK 解算（复用 `SpellbookPistolArm::Solve`）、右手（持枪手）姿态重组、
  待机↔ADS 过渡、装备/可见性合同。
- `OffhandKukriAuthoredPose.h`：待机/ADS 姿态键、右手重组目标、数字手指拟合、
  枪身取景（HipFraming/ADS 解缠）。
- `OffhandKukriAuthoredStrike.h`（生成文件）：快速近战单次突刺 18 键姿态表（手腕偏移、
  手旋转、肩/极点 IK 目标、锁骨跟随份额、逐键枪身取景——手枪先甩出画面再升回，左臂从左缘
  水平扫入、上臂抬起）＋21 采样参考相机曲线（yaw/pitch/roll/FOV）与背景高斯模糊包络；
  全长 0.633 s，首尾键与待机位姿完全一致。
- `OffhandKukriThrust.h`：突刺的配对判定与伤害公式（副手物理面板 200% × 快速近战增伤 +
  快速近战技能伤害），客户端与服务端 `ComputeServerDamage` 共用。
- `OffhandKukriStrike.cpp`：快速近战运行时——技能合同同其他武器
  （CommitQuickCombatCast 一次性体力、占用 F、确定性接触查询、挥空也有镜头冲击、
  用/杀经验）；伤害走 `OffhandKukriThrust::Damage`（服务端按申报副手物品重算同式），
  刀刃形态；唯一一次接触在全伸展帧、每目标每次动作至多命中一次，刀尖够到的墙面有顿帧/火花；
  打击感以 `KukriQuickRhythm` 为基础、突刺专用倍率加重（镜头、接触重音、顿帧、冲击）；背景高斯
  模糊用旋风批的 `M_WhirlwindFocus`（视模子树写 stencil 231，引擎 motion blur 关闭）。
- `OffhandKukriAuthoredUppercut.h`（生成文件）：副手上挑 77 键姿态表（左腕偏移、
  左手朝向、肩/极点 IK 目标、锁骨跟随份额、逐键枪身取景——右手避让含在取景内），
  正握窗口内 19 根手指骨的正握拟合，40 采样镜像刀路丝带；全长 1.2667 s（作者时间，
  播放走 `KukriRhythm::UpperTempo`，约 1.08 s）。
- `OffhandKukriUppercut.cpp`：副手上挑运行时——共享 `swordUppercut` 技能合同
  （`CommitSwordUppercutRelease` 接触起点扣体力＋冷却、0x14 命中回执、
  `TrainSwordUppercut` 结算、拒绝取消）；镜像相机曲线与命中重音、刀路丝带、
  顿帧作者时钟、120 cm 突进；伤害 = `Stats.Damage × UppercutMultiplier`。

## 共享宿主差量（Integration/，20 份补丁）

- `FPSGAMECharacter.cpp`：F 触发期间的出刀姿态（AdvanceActionBeforeCamera 钩子）、
  开火门（出刀/上挑中不接开火）、相机曲线/FOV 叠加、HipFraming 取景块（出刀与上挑
  时逐键取景）、左手占用/忙门、菜单挂起取消、副手重载与身体动作左臂让位。
- `FPSGAMECharacterActionPriority.cpp`：快速近战优先级门（出刀/上挑中拒绝二次触发）
  与优先级打断取消。
- `Skills/ColdSteelSkillModel.cpp`：`TriggerQuickCombat` 在弯刀主武器之后、手枪砸击
  之前路由到副手弯刀出刀。
- `Skills/FPSCastingMeshComponent.cpp`：副手弯刀手臂网格的 tick/finalize 入口。
- `Skills/ColdSteelHeavyStrikeModel.cpp`：`UppercutItem` 解析——主手双持手枪时上挑的
  体力、冷却、伤害面板与位移倍率按副手槽单手近战物品取值。
- `Multiplayer/ColdSteelPlayerState.cpp`：`ComputeServerDamage` 的 0x80 分支——申报
  副手物品为单手近战且主手为双持手枪时走 `OffhandKukriThrust::Damage`，否则走原技能面板；
  该配对的快速近战攻击形态为刀刃（其余快速近战仍为钝击）；0x14
  上挑命中校验按"主手双持手枪→副手槽单手近战"解析申报武器。
- `Multiplayer/ColdSteelUppercutAuthority.cpp`：上挑申报/验收/结算三处做同样的
  副手槽解析；服务器拒绝回执时取消副手上挑。
- `UI/ColdSteelQuickBarModel.cpp`、`UI/ColdSteelQuickSlot.cpp`：快捷栏 `swordUppercut`
  在主手弯刀之后、双手剑之前路由到副手弯刀，并给出副手上挑的状态文案。
- `Weapons/OffhandReloadHandoff.h`、`FPSGAMECharacterOffhandReload.cpp`：副手换弹交接按副手种类取放下
  时长——弯刀 0.30 s（法术书仍 0.55 s），客户端与服务端换弹计时同一函数。
- `UI/ColdSteelProfileRuntime.cpp`（`.r8.patch`，叠加在原补丁之后）：读档时所有近战武器按目录同步
  基础伤害、距离、攻击间隔、出手时长、体力与格挡数值。
- `Movement/FPSMeleeMovementNetwork.cpp`：`AuthorizeMeleeMove` 的 `KukriUppercut`
  分支对主手双持手枪＋副手弯刀组合放行上挑突进；弯刀上挑（主手、副手）的突进后硬直按弯刀
  自身节奏（`KukriRhythm::UpperRealSeconds`）计算，不再沿用更长的双手剑上挑时长。

## 数据

- `Content/ColdSteelData/items.json`：`ue_kukri.attack_seconds` 1.9792 → 0.8（用户定标）。
- `Multiplayer/ColdSteelQuickCombatAuthority.cpp`：服务器拒绝回执时取消副手出刀。
- `UI/ColdSteelInventoryRules.cpp`、`UI/ColdSteelProfileRuntime.cpp`：副手槽接受
  `ue_kukri` 并识别主手双持手枪配对。
- `Items/FPSPotionUseComponent.cpp`、`FPSGAMEConsumableUse.cpp`：消耗品使用期间
  副手弯刀的收放合同（与魔法书同一 stow 路径）。
- `Characters/FPSPlayerBodyMotion.cpp`：第三人称——`OffhandKukri` PoseFamily 用
  解剖映射的静态挂点（不采 FPS 相机手腕），视模支撑手为副手刀让位。
- `Weapons/Unarmed/FPSUnarmedIdleComponent.cpp`：被捕获时的挣脱拳与副手刀互斥。

## 边界

- 仅第一人称；第三人称身体侧已有 PoseFamily 挂点，远端视觉验收未完成。
- 运行时本地已构建（FPSGAMEEditor）；F 出刀的实战手感与服务器对账未验收。
