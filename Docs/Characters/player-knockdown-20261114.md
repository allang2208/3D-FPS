# 玩家击倒：倒地-站起（双手剑基准，V2 加整身动作）

2026-11-14 按用户要求制作玩家被击倒的第一人称动作，先以双手剑为标准，参考
[Kubold FPP Melee Animset - Two Handed Sword](https://www.youtube.com/watch?v=NTrzxPIXer4) 的 2:14–2:16。
测试键 **Y**。本轮未启动游戏或编辑器测试，实机效果由用户体验。

V1 用户反馈“镜头对了”，指出后倒距离太近、腿脚没处理、第三人称没同步。V2（同日）加入整身倒地-起身：
世界身体播放完整动作，所有观察者按复制的开始时间同步；第一人称看得到自己的腿，镜头位置跟随这具身体的
头部（头落在胶囊后方约 0.9 m），旋转保留 V1 认可的曲线。

## 参考读取

本地副本 `Saved/Reference/KnockdownNTrzxPIXer420261114/ref_1080p60.mp4`（1080p60，不入库），读图表在同目录
`sheets/`，重建脚本 `SourceAssets/PlayerKnockdown20261114/Reference/extract_reference.py`。

| 文件时间 | 动作 | 本作时间 |
| --- | --- | --- |
| 133.35–133.45 s | 受击：剑被打向右下，双手下沉 | 0.00–0.10 s |
| 133.45–133.67 s | 后仰下落：双臂前伸到画面中央，剑指右上 | 0.10–0.45 s |
| 133.70–133.93 s | 镜头快速仰起到天花板，背部着地 | 0.45–0.62 s（0.62 s 触地） |
| 133.93–134.40 s | 仰躺：双手在画面下方中央，剑斜指右上 | 0.62–1.05 s |
| 134.45–135.07 s | 坐起：双臂前推，镜头从仰视压回平视略低 | 1.05–1.50 s |
| 135.07–135.55 s | 跪起、站起：双手在右下，剑逐步回正 | 1.50–2.30 s |
| 135.55–135.95 s | 回到待机 | 2.30–2.60 s |

参考视频 2:13–2:16 前后还有一段向前扑倒（129.5–132.5 s），本轮没有采用。

## 实现

- **共同时钟**：`Source/FPSGAME/Movement/PlayerKnockdownMotion.h`，总长 2.60 s、触地 0.62 s。相机与双手剑
  动作按同一时钟取样，手臂触地关键帧和相机触地震动在同一帧。
- **状态与联机**：`UPlayerKnockdownComponent`（`Movement/PlayerKnockdownComponent.*`）。服务端 `Apply()` 记录
  开始时间并复制给所有人；本机和客户端按开始时间重放。期间沿用破防硬直的锁定方式：移动、视角和动作输入锁
  定，先打断换弹、检视、蓄力等动作。死亡中不开始；正在击倒时重复触发被忽略。
- **第一人称相机**：在 `AFPSGAMECharacter::UpdateCamera` 的所有相机层之后叠加，下一帧开头先还原，避免与
  原有平滑插值互相累积。旋转沿用 V1：俯仰覆盖到仰视 60°（触地回弹 64°），坐起时低头 −14°，再回到原瞄准
  俯仰；包含轻微侧倾、偏航和触地阻尼震动。位置（V2）取整身动作导出的眼位轨迹（头骨＋头部局部 [0,7,6] cm，
  与家具休息相同约定），0–0.18 s 从分层相机过渡到头部，1.95–2.55 s 站起时回到分层相机（第一人称眼位在
  胶囊前 56 cm）。地面射线保证离地至少 14 cm，从胶囊中心球形扫掠防止镜头穿墙。视模挂在第一人称相机下，
  随相机一起倒下。第三人称观察视角下不改相机，只看身体动作。
- **世界身体（V2）**：`player_body.json` 的 `clips/Knockdown` → `J_Knockdown_Standing`。
  `UFPSPlayerBodyAnimInstance` 在游戏线程读取击倒组件的时钟（与家具休息相同的方式），在最终的整身死亡槽
  （`DeathBlend`）播放，进入 0.08 s、退出最后 0.30 s 渐变回实时姿势；死亡优先。眼位轨迹放在
  `furniture_camera_tracks/Knockdown`，复用现有加载器，只有其 `animation` 与当前 `clips/Knockdown` 一致时才生效。
- **本人身体**：有整身动作时第一人称共用身体照常显示（看得到腿脚和裤鞋）；没有该动作的身体变体（目前
  Kaitlin）仍隐藏共用身体，并用 V1 的关键帧镜头（向后量已改为与整身一致的约 1.5 m）。
- **双手剑手臂**：`A_RuneSword_Knockdown`（`/Game/Weapons/AzureRunesword20260913/`），所有双手剑共用；
  长柄没有专属条目，播放普通柄同一条。`URuneSwordComponent::PresentKnockdown/TickKnockdown`
  （`Weapons/RuneSwordKnockdown.cpp`）按击倒组件时钟取样，结束回待机。
- **测试键**：`AFPSGAMECharacter::KnockdownTestPressed`，按 Y 发送 `ServerTestKnockdown`，联机客户端同样由服务端开始。
  第一、三人称都可用。F6 开发面板打开时输入交给界面（UIOnly），2026-11-15 起面板内也拦截 Y 并调用同一个 RPC
  （`UDevelopmentPanelWidget::NativeOnKeyDown`），在面板里切到第三人称后可直接按 Y 检查。第三人称下镜头不随
  倒地移动，只看身体动作。

## 手臂制作

`SourceAssets/PlayerKnockdown20261114/`：

1. `keys_knockdown.json`：双手+剑作为一个刚体组，相对已认可待机握姿的视模空间平移与绕视线旋转
   （受击右下 → 下落前伸居中 → 仰躺下方居中、剑斜指右上约 54° → 坐起前推 → 右下 → 待机）。
2. `author_knockdown.py`（Blender 5.1，`-b --factory-startup`）：读取 V85 检视同源的 WristLocked V4 待机，
   双手保持待机握点，用 V85 的 `Arm.solve` / `roll_humerus` 和 V9 前臂扭转分配解算整臂，120 Hz 导出
   `Export/A_RuneSword_Knockdown.fbx`，指标写入 `authoring_knockdown.json`。
3. `import_knockdown.py` + `run_import.ps1`：后台 commandlet 新建资产，首尾按 `SwordIdleClose20260926`
   的方法接回当前正式待机，回执 `import_receipt.json`。只会替换本脚本自己保存过的版本。
4. `camera_curve_check.py`：`PlayerKnockdownMotion.h` 相机曲线的离线移植，用于查看眼高与俯仰数值。

作者指标（不是游戏验收）：握点误差 0 mm，无伸展钳制；腕弯最大右 20.7°、左 30.9°；前臂扭转右
60°→91°、左 −60°→−37°；剑尖进深不低于 0.73 m。

## 整身动作制作（V2）

`SourceAssets/PlayerKnockdown20261114/FullBody/`，三个来源都是 CC0：

| 段落 | 来源 | 本作时间 |
| --- | --- | --- |
| 受击后挫 | KayKit Character Animations 1.1 `Death_A` 前 0.07 s | 0.00–0.10 s |
| 后仰、屈膝坐倒、背部落地、回弹 | Mesh2Motion `Hit_Knockback` 0.11–0.40 s（R9：双脚留地，重力限速） | 0.08–0.80 s |
| 仰躺 → 坐起 → 跪起 → 站立 | Mesh2Motion `LayToIdle` 全段 1.5 s | 1.00–2.35 s |

1. `import_donors.py`：导入 KayKit `Death_A`，用现有 `RTG_KayKit_Jason_Sword` 重定向到 Jason。
2. `retarget_m2m.py`：新建 `IK_Jason_Knockdown`、`RTG_M2M_Jason`（源为怪物击倒已用的 `IK_M2M`），重定向
   `LayToIdle`、`Hit_Knockback`。
3. `sample_donors.py`：30 Hz 取样到 `donor-input.json`（单独进程，避开重定向后异步压缩的退出断言）。
4. `author_fullbody.py`：Jason 原生骨长，按上表重定时与交叉渐变；腿部双骨 IK 让双脚在后挫和下落中留在地面
   （原动作双脚扫到约 90 cm 高）；倒地前按重力限速重定时；按足、手、头、背、骨盆的离地下限整体抬高（最多
   6.6 cm，平滑且只抬不降），残余入地的脚单独用 IK 抬起；结尾加一步收回站姿；导出眼位轨迹。
   `preview_fullbody.py` 输出侧视火柴人检查图，`analyze_fullbody.py` 输出重心与接触检查。
5. `save_fullbody.py`：新建 `/Game/Characters/JasonPlayer20261003/Knockdown20261114/Animations/J_Knockdown_Standing`，
   30 Hz、79 帧、2.60 s，关闭根运动。回执 `assets-saved.json`。
6. `publish_fullbody.py`：经 `Tools/PlayerBody/config_transaction.py` 只写 `clips/Knockdown` 和
   `furniture_camera_tracks/Knockdown`。

Mesh2Motion 的落地点与起身起点相差 4 cm（`landing_offset_cm`），所以起身在原地完成，胶囊不需要移动。

KayKit 的 `Lie_StandUp` 是从床面高度起身（骨盆约 70 cm），其 `Death_A` 后段会先跳起约 40 cm，这两段均未采用。

### 人体跌倒检查与 R9 修正（2026-11-15，用户要求检查）

**状态：R9 已安装（2026-11-15）。** `J_Knockdown_Standing` 由 `save_fullbody.py` 保存（sha256 `94d13d8f…`，
79 帧 / 2.60 s），`publish_fullbody.py` 已更新 `furniture_camera_tracks/Knockdown` 眼位。此前 00:10 的保存曾被
一个无窗口、命令行不可读的 `UnrealEditor` 进程挡住（`run_ue.ps1` 把它当作写入者），该进程退出后于 11:30 完成。
R3 备份在 `Work/R3/`。

`analyze_fullbody.py` 用分段质量表算重心，`analysis-fullbody.txt` 为结果。修正前（R3，`Work/R3/`）的问题与 R9 结果：

| 项目 | R3 | R9 |
| --- | --- | --- |
| 下落时重心向下加速度峰值 | 3.6 g（比自由落体快，像被往下拽） | 1.00 g（倒地前按重力限速重定时） |
| 倒地方式 | 双脚被扫到 60–70 cm 高，整个人腾空后背砸地 | 屈膝坐倒：双脚留在地面并前滑 15 cm，臀背着地 |
| 受击后挫 0–0.13 s 脚底 | 两脚滑动约 15 cm，脚尖低于地面 2 cm | 钉在原地 |
| 着地 | 背 0.63 s、骨盆 0.67 s | 背 0.60 s、骨盆 0.67 s，触地时头离地 27 cm、颈部前屈约 23°（护头） |
| 头部躺下 | 1.0 s 以 1.8 m/s 落地 | 1.03 s 以 1.4 m/s 轻放 |
| 起身结束站姿 | 右脚在后 28 cm、髋部转 18°，交回实时姿势时滑步 | 2.18–2.46 s 加一步：右脚回到起始位置，髋部转正，骨盆回到双脚上方 |
| 脚跟入地 | 仰躺时最多 3 cm | 不超过 1 cm |

仍保留的偏差：
- 仰躺时双腿先伸直，起身前再屈膝（来自起身动作的起点），中间约 0.3 s。
- 结束时左脚比起始位置靠前约 13 cm，最后 0.3 s 交回实时姿势时这只脚会滑回。
- 起身中右手撑地（约 0.97 s 离地 12 cm 以内），第三人称手里的武器会短暂碰到地面。
- 只检查了骨骼和重心，没有在 UE 里查看蒙皮网格的自穿插。

## 不同武器的适用范围（2026-11-15 检查）

通用部分：输入锁定、相机倒地、整身动作和联机同步与武器无关。开始击倒时调用（2026-11-15 00:01 修改，00:04 编入编辑器目标，DLL 于 12:13 由并行会话的编辑器编译链接）
`InterruptActionsForPriority(false)`（与手枪、步枪快速近战同一条中断链），所有武器进行中的挥砍、拉弓、
施法、工具使用、换弹，以及闪避、滑铲、翻越都会被打断；此前弯刀等武器的挥砍会继续打完。

| 部分 | 双手剑 | 其他武器 |
| --- | --- | --- |
| 第一人称手臂 | 专属 `A_RuneSword_Knockdown`（受击、撑地、起身） | 保持各自待机姿势固定在镜头前，随镜头一起倒下 |
| 第三人称身体 | 整身动作 | 整身动作相同 |
| 第三人称手中武器 | 跟随右手 | 跟随右手；双手持握的枪、长柄武器会失去左手握持，弓在左手 |

战锤走工具系统，不在双手剑范围内。第一人称共用身体本来就隐藏原手臂、手和颈部分段，倒地时不会出现两套手臂。

### 其他武器的通用第一人称处理（2026-11-15，用户选择通用方案）

双手剑以外的所有武器（枪、手枪、弯刀/手斧、弓、法杖、魔法书、工具/战锤、空手）：受击 0–0.24 s 手臂连同武器
被打出画面（下移 50 cm、后移 12 cm、向下转 38°、侧倾 18°，先快后慢），仰躺期间留在画面外，1.95–2.50 s
站起时抬回原位。曲线在 `PlayerKnockdownMotion::ViewmodelDrop`。

做法：击倒开始时，本机把第一人称相机下的直接子组件（子树里含仅本人可见的图元，即各武器视模）挂到一个
临时根 `KnockdownViewmodelDrop` 下，保持相对变换，由击倒时钟驱动这个根；结束时挂回相机，相对变换不变。
各武器仍按原逻辑驱动自己的组件，不改任何武器代码。双手剑装备时，带剑手臂的那一支不移动，继续播放
`A_RuneSword_Knockdown`。

已知边界：击倒期间新生成并挂到相机上的组件不会跟着压下；少数按相机世界坐标单独摆放的道具（例如法杖副手
近战刀身）不跟随，但它们只在已被打断的动作中出现。按手骨摆放的道具（魔法书、副手刀）随手臂一起移动，
可能滞后一帧。

## 交付状态

- 资产：`/Game/Weapons/AzureRunesword20260913/A_RuneSword_Knockdown` 已由后台 commandlet 新建并保存，312 帧、
  2.60 s，首尾接回当前待机（偏移 Y +6.0 cm、Z −1.2 cm，与 V85 检视同法）。回执
  `SourceAssets/PlayerKnockdown20261114/import_receipt.json`，sha256 `f8e6d82a…`。
- `run_import.ps1` 需设置 `UE_SKIP_UBT_SDK_SETUP=1`：否则 Turnkey 启动时的 SDK 探测会调用 Build.bat，
  在其他会话编译期间一直排队。
- 源码：V1 随并行会话 11:39 开始的全模块编译一起编译（`Saved/Logs/UnknownCombatFacingFinalRetry20261114.log`）。
  V2 的最后一次源码修改为 17:23:20；编辑器 `UnrealEditor-FPSGAME.dll` 于 17:28:57 由并行会话的编辑器编译重新
  链接，相关编译单元（击倒组件、剑击倒、角色、身体动画实例、第一人称身体）的 obj 均在 17:27–17:28 生成，
  UHT 生成代码 17:27:10，已不含 V2 中途删除的后滑字段。
- V2 整身动作已保存并写入配置（配置回执 `Saved/PlayerBodyConfigWrites/20261114T092437.593909Z-97693534/`）。
  `save_fullbody.py` 在保存成功后因回执字段名错误中断，`assets-saved.json` 为离线按已保存包补写，sha256 `bc9b11df…`。
- 未启动游戏、PIE 或编辑器测试。

## 已知边界

- 只有双手剑有专属第一人称手臂动作；其他武器在击倒中保持待机姿势随相机倒下。
- 整身动作只做了 Jason；Kaitlin 女性身体没有 `Knockdown`，第三人称仍站立，第一人称用 V1 回退。
- 只有向后倒：受击方向来自侧面或背后需要另做动作，`Apply()` 目前总是朝当前朝向的反方向倒。
- 第三人称时手里的武器跟随右手；从蹲伏或滑铲中触发会直接切到站姿开始的动作。
- 尚未接入怪物攻击等实际触发源，目前只有 Y 测试键。
- 胶囊不变：倒地期间碰撞仍是站立体积，头部后移只做表现（镜头有碰撞扫掠，身体网格可能穿入身后的墙）。

## 完整性与联机检查（2026-11-20）

源码已被其他会话拆分到 `FPSGAMECharacterInput.cpp`（Y 键绑定）、`FPSGAMECharacterCamera.cpp`（相机还原/叠加）、
`RuneSwordPresentation.cpp`（加载击倒片段）、`RuneSwordActions.cpp`（`CancelAction` 清除击倒姿势），挂钩都还在。

联机流程：服务端 `Apply()` 写 `StartedAt` 并立即 `Begin(0)`；所有客户端在 `OnRep_StartedAt` 按服务端时间
算出已过时长再 `Begin(age)`，晚加入或刚进入相关范围的客户端也能接上；已结束的击倒不会重播。世界身体动画、
计时和解锁在每台机器各自按同一起点运行；第一人称镜头、双手剑手臂和通用武器压下只在本机执行。

本次修正（源码 11-20 已改；2026-11-22 的 FPSGAMEEditor 构建已编译，目标文件晚于源码，`UnrealEditor-FPSGAME.dll` 21:34 生成；未实机测试）：
- **服务端处理远端玩家时误用本机档案。** `Begin()` 原先在任何有控制器的机器上调用
  `InterruptActionsForPriority(false)` 和 `SuspendWeaponForMenu()`。前者会用游戏实例里的本地档案同步并
  重新套用到角色上；在监听服务器上，这是房主的档案，会被套到被击倒的远端玩家身上。现在只有本机控制的角色
  走 `false` 和菜单暂停；服务端上的远端玩家改走 `InterruptActionsForPriority(true)`（只取消动作、不碰档案，
  与死亡相同）。
- 坐在或躺在家具上时不触发击倒（家具休息系统独占身体、镜头和退出流程，没有击倒分支）。

仍存在、未修改的问题：
- **击倒中死亡**：死亡动作优先，身体会在 0.18 s 内从倒地姿势切回站姿死亡动作再前倒；死亡镜头从当前低位
  视角接回站立高度的死亡轨迹。需要改死亡动画槽和死亡镜头。
- **网络延迟窗口**：服务端开始击倒到客户端收到之间（约半个往返），客户端仍可能发起攻击，服务端会照常执行。
  与破防硬直相同，服务端动作入口未检查击倒状态。
- **输入锁叠加**：移动/视角忽略是计数的，`DisableInput/EnableInput` 不是。破防硬直与击倒重叠时，先结束的
  一方会提前恢复按键绑定。
- **空中/水中/蹲伏**：空中触发时身体在半空做倒地动作直到落地；蹲伏触发后起身结束仍是蹲伏。
- 测试 RPC `ServerTestKnockdown` 在所有构建中可用，任意客户端都能让自己倒地；正式接入攻击后应移除或只在
  开发构建保留。
- 动画实例、第一人称身体可见性和相机每帧各做一次 `FindComponentByClass`，开销很小，未缓存。

## 全部问题修复（2026-11-20，源码已改，待编译）

| 问题 | 处理 |
| --- | --- |
| 服务端处理远端玩家时套用房主档案 | 远端玩家的服务端副本改走 `InterruptActionsForPriority(true)`，本机才同步档案和暂停菜单 |
| 击倒中死亡：身体弹回站姿、镜头跳回站立高度 | 倒地或起身途中死亡时，身体保持躺地：未躺稳的继续倒到 1.00 s，正在起身的按实时速度躺回 1.00 s；1.95 s 后（基本站直）才走正常站姿死亡。死亡镜头（`FPSPlayerBodyDeath.cpp`）改为跟随躺地头部，旋转沿用击倒曲线 |
| 网络延迟空档里的攻击仍被执行 | 服务端在击倒期间拒绝：所有命中上报（`ValidateHitReport`）、施法（`ServerCastSpell`，与束缚同码 8）、快速近战开始，并取消拉弓 |
| 破防硬直与击倒叠加时提前恢复按键 | 双方释放时互相检查：另一方仍在进行就不恢复按键绑定；击倒中的破防不再切换双手剑的破防姿势 |
| 空中、水中、飞行、家具上 | 空中受击等落地后开始（最多等 4 s）；水中、飞行、坐卧家具时不触发 |
| 蹲伏触发后起身仍是蹲姿 | 开始时在服务端和本机解除蹲伏（头顶被挡时保持蹲伏） |
| 测试入口在所有版本可用 | Y 键绑定、F6 面板中的 Y 和服务端测试实现只在非发行版存在 |
| 每帧组件扫描 | 击倒组件注册到按角色索引的表，动画实例、相机、第一人称身体、双手剑改为哈希查找；生命、身体组件在开始时缓存 |
