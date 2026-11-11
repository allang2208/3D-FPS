# 斧头组合的双持动作与副手单持（2026-11-04）

用户：双持装备斧头时，两只手都替换成现在单持的装备动作；副手装备弯刀或斧头时按双持的副手动画，包括装备、攻击、技能。
确认后的范围：
1. **双斧装备**：两只手都是单持斧头的竖直抛接（`HatchetEquip` V2.1）。
2. **斧 + 弯刀混搭**：每只手按自己的武器播。
3. **主手空、副手单持弯刀/斧**：原来显示双手空拳。现在左手拿武器，单持全套动作镜像到左手，右手不显示（同“主手空、副手单持手枪”）。

## clip（`Clips/*.json` → `/Game/Weapons/TacticalHatchet20261101/Animations/A_TacticalHatchet_<名>`）

| clip | 时长 | 内容 |
| --- | --- | --- |
| `DualEquip` | 1.00 s | 右手单持斧头抛接；左手是它的镜像，晚 0.067 s（同双弯刀）。各自转过斧头、刃口朝前后，在 0.66–0.93 s（左手晚 0.067 s）收进双持待机。两拳全程各向外 8 cm；接住前后左拳靠近镜头 6 cm，右拳远离 3 cm，两把斧头错开。 |
| `PairEquipHK` | 1.00 s | 主手斧头 + 副手弯刀：右手 = 上面的斧头抛接，左手 = 双弯刀 `DualEquip` 的左手。 |
| `PairEquipKH` | 1.00 s | 主手弯刀 + 副手斧头：右手 = 双弯刀 `DualEquip` 的右手，左手 = 上面的左手斧头抛接。 |
| `PairAttack3HK` | 246/120 s | 第三段：右手斧头劈（`HatchetDualAttack3` 右臂），左手弯刀刺（`DualAttack3` 左臂）。 |
| `PairAttack3KH` | 246/120 s | 第三段：右手弯刀刺，左手斧头劈。 |

- 两只手臂是独立骨链，混搭 clip 逐帧取各自来源的手臂；两边都在双持待机结束，较短的一边停在末帧。
- 第三段两个来源都是双刺时钟，命中窗、打击时刻、回执都不变（`HatchetPairRhythm.h` 用 `static_assert` 钉住）。
- 两把武器的最近距离（真实采样点：斧头取头部 8 点，弯刀取刃线）：

| clip | 最近距离 | 参照 |
| --- | --- | --- |
| `DualEquip` | 2.81 cm（0.825 s，收进待机时） | 双持待机本身 3.53 cm，已认可的双斧劈 2.87 cm |
| `PairEquipHK` | 1.86 cm（0.79 s） | 未穿插，但比双弯刀装备（≥ 2.59 cm）近 |
| `PairEquipKH` | 2.91 cm | |
| `PairAttack3HK` / `KH` | 13.2 / 12.2 cm | 双刺 11.8 cm |

- `HatchetPairRhythm.h`（`--header` 生成）：五个 clip 路径；左手斧头在抛接期间相对 `hand_l` 的变换表，60 Hz（`SampleLeftHatchet`），做法同 `KukriDualEquipBlade.h`。

## 运行接入（`KukriWeaponComponent`）

- `bMainHatchet` / `bOffhandHatchet` 记录哪只手拿斧头（`RefreshOffhand`）。`DualEquipClip()` 按组合选装备 clip，缺资产时回退到 `DualEquip`。
- 装备期间按各手的武器选择：右手的抛接风声和握声、镜头曲线（右手斧头时用 `HatchetDrawRhythm`），左手的声音时刻（晚 0.067 s），以及副手武器的飞行表。
- 第三段：两把斧头时仍是 `HatchetDualAttack3`。混搭时，斧头那只手劈、弯刀那只手刺（`bChopRight` / `bChopLeft`）：
  - 打击手感、挥砍风声和剑气时刻用双斧劈的；
  - 剑气只给劈的那只斧头（`KukriRift` 的 `ChopSides`）；
  - 镜头是双斧劈和双刺两条曲线各取一半（`PairChopCamera`）。
- 冲刺就绪举斧：只看右手是不是斧头（左手本来就是双持跑步的摆臂）。主手弯刀 + 副手斧头时仍是原双持跑步。
- 双持旋风的左臂垂下：只看副手是不是斧头。

## 主手空、副手单持（lone off-hand blade）

- `UColdSteelStatusModel::ActiveKukriWeapon()`：主手有物品时就是 `Equipped()`；主手空置时是当前武器组配对副手槽（6→8，9→11）里的弯刀/斧头（`ColdSteelInventory::LoneOffhandBlade`，规则同 `LoneOffhandPistol`）。
- 客户端招式和服务端回执都改用它找出手武器：
  - 弯刀组件：三连击、重击、冲刺攻击、F、上挑；
  - `ColdSteelKukriAuthority`；
  - 上挑、旋风的武器解析（`SwordUppercutWeapon` / `WhirlwindWeapon::Resolve`）；
  - 近战位移校验（`FPSMeleeMovementNetwork`）；
  - 耐力（重击蓄力、攻击次数读数、击杀回复）；
  - F 的属性加成（`QuickCombatModifiers`）。
- 数值按这把副手武器真实结算。命中回执原本就接受配对副手槽的物品。
- 呈现：
  - 视模 `bMirrorRightToLeft` + `bLeftHandOnly`：采样单持 clip，右臂镜像到左臂，右臂隐藏；
  - 武器显示在 `OffhandBlade`（hand_l）上，相对变换 = 右手武器的镜像（`UKukriArmsMeshComponent::MirroredWeaponToHandL`），抛接飞行也一起镜像；
  - 右手刀隐藏，不挂外观部件；
  - `BladeFrame()` 读左手刀，命中检测随之走左手；
  - 镜头偏航/滚转、视模冲击、打击压入、剑气都取镜像；
  - 旋风反向转（同法杖配副手刀）。
- 镜像握持复核（`Work/probe_lone_mirror.py`）：在待机、双持待机两套姿态上，与已认可的左手握持（`left_kukri.json`）相差 0.000°、0.001 cm。镜像修正必须取骨架绑定姿态（`ref_world`），取站姿基准会差 22°。
- 空手组件不再把副手弯刀当作“不呈现”，所以不再出现空拳。

## 资产与构建

- 五个 clip 后台导入（`import_receipt.json`，修订 `HatchetPairs_V1_20261104`，0 错误）。
- `FPSGAMEEditor Win64 Development`：
  - 组合部分 Succeeded（`Saved/BuildEditor/build-hatchet-pairs-20261104.log`，49 个文件）；
  - 副手单持部分 Succeeded（`build-hatchet-lone-offhand-20261104.log`，DLL 15:08:40）。
  - 期间另一会话也构建过一次（`build-20261104-150211.log`）；改动文件的 .obj 都比源文件新。
  - 排查修复后 Succeeded：`build-hatchet-lone-fix-20261104.log`、`build-hatchet-lone-audit-20261104.log`。期间另一会话的构建也编进了部分修改；所有改动文件的 .obj 都比源文件新。
- Game 目标未构建。

## 副手单持排查与修复（2026-11-04，用户：同步与衔接没做好，有穿模错位）

找到的原因：
1. **切换动作时刀离开左手（衔接、错位、穿模）**：左手刀相对 hand_l 的变换是在整副骨架的入场淡化之后，用隐藏的右臂算出来的。右臂在单持左手模式下被收成零缩放，淡化从这个收拢姿态出发。所以每次切 clip（出招、收招、走跑切换、装备结束），在淡化的 0.11–0.25 s 里，右手的位置和旋转都是错的。镜像过去的刀会缩进掌心、转错方向。
   修复：在 `MirrorRightPose` 之后、淡化之前，用 clip 本身的右手-武器关系（套同样的握持锁）和 hand_l 的绑定修正，直接算出左手关系。这个关系与淡化无关。淡化里右臂和右武器链也不再从零缩放姿态长出来（`HiddenRight`）。
2. **视模冲击、打击压入、跳跃摆动没有镜像**：冲刺攻击和 F 的冲击、跳跃摆动都挂在 `JumpRoot` 上，原来只镜像了三连击的冲击。现在在 `JumpRoot` 上整体按镜头竖直面镜像（之前单独加的两处镜像撤回，避免重复取反）。
3. **冲刺攻击的剑气没有镜像**：现在镜像，并按镜像状态缓存。
4. **联机不同步**：所有者发出的身体状态里武器名为空（取自空的主手），服务端认为是空手，于是丢弃所有动作，远端看到的是空手站着。现在所有者与服务端都用 `ActiveKukriWeapon` 给出同一武器名和实例。第三人称身体按单持弯刀族呈现，刀在右手，动作同步；第一人称看不到这把世界武器。

复核（只读，`ULoneOffhandBladeAuditCommandlet`，报告 `Work/lone_audit_after_fix.txt`）：
- 15 段 clip（含斧头装备与劈砍）逐帧 120 Hz，左手刀是右手刀的镜像，刃尖与刃根误差 0.001 cm。
- 8 种切换（出招、收招、走→跑、跑→冲刺攻击、上挑、两种装备结束、第二段→斧劈）：淡化全程左手刀与目标 clip 的握持关系差 0.0000 cm / 0.000°，切换瞬间左拳 0 跳变。
- `clip_grip_drift` 是 clip 本身的刀相对拳头的作者偏离（握持锁放开的那部分，如上挑 5.7 cm），右手单持时完全一样，只作记录。

运行：`UnrealEditor-Cmd.exe FPSGAME.uproject -run=LoneOffhandBladeAudit -Report=<文件> -unattended -nosplash -nullrhi`

## 联机复查（2026-11-04 用户要求复查本轮工作）

副手单持时下面三处仍只读主手（为空），已改成 `ActiveKukriWeapon()`：
- `ColdSteelDashAttackModel.cpp` `DashAttackStats`：客户端出招和服务端 0x16 冲刺攻击的伤害、距离都读这里，原来副手单持时冲刺攻击按空手算；
- `ColdSteelSkillModel.cpp` `QuickCombatStats`：快速连击的狂战倍率读不到副手刀；
- `ColdSteelSkillRules.cpp` `GrantBerserkOnWeaponHit`：命中叠狂战层数时找不到出手的刀。

`FPSGAMEEditor Win64 Development` Succeeded（`Saved/BuildEditor/build-review-lone-net-20261104.log`）。

## 第三人称补齐（2026-11-10 用户要求处理第三人称动作）

1. **副手单持镜像到左手**：身体装备的刀改挂 `hand_l`，身体动画在动作混合完成后、手型抓握之前把整段上半身按骨架绑定位姿镜像（`FControls::MirrorLoneBladeUpperBody`，写法同已认可的单持左手手枪 `FSinglePistolMirrorLayer`）。腿保持原步态，胸/肩/头随手臂一起镜像。`FFPSBodyState.bLoneBlade` 由本地、服务端与 observer（`ActiveKukriWeapon` + 主手空）三方同判。装备、跑步、招式、上挑、旋风、剑气与吊坠都因此落在左手。
2. **斧 + 弯刀混搭第三击各手各的**：新增第三张姿势输入 `SwordAlt`。主取（右手）按主手武器选 `Kukri.Hatchet.DualChop`（斧）或 `Kukri.FullBody.Dual.Thrust`（刀），另一取只提供左手整条链，两者共用双刺 2.05 s 时钟。`FPSBodyKukriMotion::Clip` 按 `HatchetPairAttack3HK/KH` 变体分派，`PreserveHands` 与 observer 剑气窗口同步放开（斧手用斧头刃口采样，刀手保留双刺窗口）。
3. 副手单持旋风：本轮未改动。第三人称按角色实际朝向旋转（lone 的 `TurnDegrees` 取反沿用 2026-11-04 的实现），第一人称仍是既有的 -2θ 表现。

## 未覆盖 / 已知限制

- 第三人称：双斧装备（`HatchetDualEquip`）和混搭装备（`PairEquipHK/KH`）的身体装备动作仍走双弯刀装备表 `Kukri.FullBody.Dual.Equip`，没有各自的抛接动作。
- 第一人称与第三人称的旋风转向表现沿用既有约定，本轮未调整。
- 没有运行游戏、测试或验收。

## 吊坠/附魔与预览（2026-11-04 用户要求一并修复）

**吊坠/附魔**：`KukriDecisiveComponent`（挂绳 `kukri_lanyard_decisive`）、`KukriRelentlessComponent`（挂绳 `kukri_lanyard_relentless`）、
`KukriBerserkerComponent`（附魔 `bloodWolf`）、`KukriFrostRavenComponent`（附魔 `frostHawk`）原来只读主手物品，副手单持时识别不到刀上的挂绳或附魔。
- 改为用 `ActiveKukriWeapon()` 找出手的刀：配置、蓄力、命中结算、服务端起手、伤害与韧性倍率都走这一处。只有出手的刀确实是主手时，才去读配对副手槽。
- 副手单持的刀拿在左手，所以按副手显示：
  - HUD 提示显示“副手 · 藏锋…”，状态栏显示“副手连锋”；
  - `bloodWolf` / `frostHawk` 的手部特效挂在左手（`KukriBerserkerVFXComponent` 也把左手刀当作覆盖层目标）；
  - 第三人称仍按世界武器的手（右手）显示。
- 一次性替换脚本：`Work/swap_pendant_weapon.py`。

**预览**（V7 可编辑手模，真实斧头与弯刀网格，未叠加镜头曲线，非实机）：
- `Previews/<clip>_sheet_*.jpg`：`DualEquip`、`PairEquipHK`、`PairEquipKH`（每 1/30 s 一格），`PairAttack3HK`、`PairAttack3KH`（每 1/20 s），副手单持的 `LoneHatchetEquip`（1/30 s）、`LoneAttack`、`LoneHatchetAttack3`（1/20 s）。
- 副手单持的姿态按运行时同一套镜像算法生成（`preview_pairs.py` 的 `LoneMirror`），右臂按 `bLeftHandOnly` 遮掉。握持期间左手到刀的距离恒为认可握持的 7.6 cm，只在抛接飞行时离手。
- 重建：`python -I preview_pairs.py [pairs] [lone] --render`（Blender 5.1，`render_pair_preview.py`）。
- `Kukri_Editable.blend` 的贴图还指向已退役的 Fab 缓存，渲染时改用 `Kukri20261020/Textures` 下的工程贴图（ORM 的 G/B 通道分别作粗糙度和金属度）。
- 冲刺就绪循环 V3 的预览也重渲了（`HatchetSprint20261103/PreviewsReady/`）。那边的左手斧原来是固定摆位，现在跟着摆动的左拳。

## 重建

```
python -I author_pairs.py --header
UnrealEditor-Cmd.exe D:/FPS3D/FPSGAME/FPSGAME.uproject -run=pythonscript -script=D:/FPS3D/FPSGAME/SourceAssets/HatchetPairs20261104/import_pairs.py -unattended -nosplash
```

`Work/swap_acting_weapon.py` 是本轮一次性的源码替换脚本，记录了改了哪些查找。重跑不会重复替换。
