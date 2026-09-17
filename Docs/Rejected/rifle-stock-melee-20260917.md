# 步枪快速进战：枪托砸击（已废案，2026-09-17）

> **状态：废案退役（2026-09-17）。** 用户实机判定 V1/V2 均不符合预期，开发留待下次。代码已从共享文件精确回退，文件与参考素材移入 `trash/rifle-stock-melee-retired-20260917/`（散列清单 [Docs/AssetArchives/rifle-stock-melee-retired-20260917.json](../AssetArchives/rifle-stock-melee-retired-20260917.json)）。本文保留调研结论、读谱数据与恢复入口，供下次开发接手，不作为可用功能文档。

# 步枪快速进战：枪托砸击（F 键家族步枪版）

日期：2026-09-17。范围：M4/AKM/QBZ191 三把步枪在 F 键「快速进战」下的枪托近战；动作、接触结算、技能提交全套接入。手枪版见 [快速进战记录](../Skills/left-hand-occupied-notice-20260916.md) 与 `FPSQuickCombatComponent`；这是待续清单里的「其他武器版本」之一。

## V2：按参考视频复刻（2026-09-17 当晚）

用户提供 B 站参考 [BV13K421e7Rw](https://www.bilibili.com/video/BV13K421e7Rw/) 1:05–1:07 的 AK47 枪托近战，要求参考复刻。视频经 yt-dlp 下载本机逐帧读谱（30 fps 源，63–69s 粗读 + 64.8–67.6s 每 1/15s 密集帧提亮细读；截图留在 `Saved/Reference/RifleStockBV13K421e7Rw20260917/`，参考视频不入库）。

读谱结论（起势 65.27–65.65 / 扫击 65.65–66.10 / 收势 66.10–66.55，全程约 1.28 s）：

- **蓄势**：整枪拉近右抬，托底甩向右上方镜前、枪口左摆下沉（yaw −30°、pitch +18°）——是"托底翻上右肩"的蓄势，不是小幅后拉。
- **扫击**：整枪向前左下横扫，枪口继续左摆至 −75°、压低 28°，托底自右上扫过画面中心命中（约 65.9s，对齐 ContactTime=0.64）。
- **收势**：约 0.45 s 回到持枪位。双手全程持枪（左手护木随动），与既有实现假设一致。

V2 改动：`QuickCombatRifleMotion.h` 时间轴 0.14/0.38/0.42/0.92 → **0.36/0.64/0.72/1.26s**，偏移改为 (-3,4,6)/(12,-10,-5) cm，姿态偏转从双轴 (yaw/roll) 扩为 **yaw/pitch/roll 三轴**（`ApplyRifleStockMeleePose` 的 Swing 增加绕相机右轴的 Pitch）。命中判定点 0.64 s 对齐托底扫过画面中心。构建 21:59 链接完成，未实机测试。

## GitHub 复用调研结论（2026-09-17）

按用户要求先查了 GitHub/免费库，结论是**没有可直接拿来用的枪托近战动画**：

- [OctavianTocan/Realistic-Assault-Rifle-Template](https://github.com/OctavianTocan/Realistic-Assault-Rifle-Template)：README 明说 "serves as a project showcase and does not contain the actual template assets"，许可随 FAB/Gumroad 购买渠道，非开源。
- [ItsPogle/Unity-First-Person-Melee](https://github.com/ItsPogle/Unity-First-Person-Melee)：CC0 但是 Unity 工程、单手剑系模板，无步枪无枪托。
- ArcCW/Sven Co-op/GMod 系武器包（含 bash 动画）是商业游戏资产移植，不可再分发；本工程已有先例（ARC9 MW22）只作结构参考、不取资产。
- OpenGameArt CC0 包（如 [Low Poly FPS Rifle and Hands](https://opengameart.org/content/low-poly-fps-rifle-and-hands)）风格与骨架均不匹配，且只有射击/装填。

即使用许可允许，骨架（本工程 SK_M4_Infima 臂 + 各枪 WPN 组）、每握把接触与命中窗标准也要全套重适配——按近战标准的口径（先确认第一/第三人称、源骨架、真实 clip 与许可），直接自制更省。本功能因此走工程内程序化姿态管线，与手枪砸击同构；GitHub 仅作节奏结构参考。

## 实现方式（程序化姿态层，无烘焙片段）

沿用 `UFPSQuickCombatComponent` + `UFPSCastingMeshComponent::ApplyQuickCombatPose` 的成熟结构：

- **动作组件** `Skills/FPSRifleStockMeleeComponent`：阶段 `SetBack(0.14s) → Strike(接触 0.38s / 到位 0.42s) → Recover(0.92s)`，时钟常量在 `Skills/QuickCombatRifleMotion.h`。接触用 `GetMeleeAimTransform()` 沿视线 32 cm 半径球扫（ECC_Pawn，单目标），伤害走 `ColdSteelSkills::ApplyHit`（`Shot.bRifle=true`，走 rifleMastery 修炼），击退/眩晕 `ReceiveStun`，命中音复用 `S_MeleeHit_Quick`；冷却与修炼提交与手枪版同一事务（`CommitQuickCombatCast`/`FinishQuickCombatCast`/`TrainQuickCombat`）。
- **姿态层** `UFPSCastingMeshComponent::ApplyRifleStockMeleePose`：与手枪版根本区别是**双手保持持枪**——武器组（`WPN_root` 子树）在相机空间做刚体偏移（绕自身入场支点：后拉右沉蓄势 `(-9,5,-3)cm/+7°yaw/+4°roll` → 前撞 `(+17,-8,+2)cm/-10°/-6°`，枪托底自右向左扫过画面中心），双腕目标=入场手位×同一刚体差值，双臂两骨 IK 重解（恒骨长，超出 93% 平移肩带不拉伸），双手指骨随各自手的父级刚体跟随（保持已接受握持，不开指）。锁骨保持动画驱动；收势阶段按进度交还动画层。入场快照按动作 Serial 缓存，姿势是当前 idle（含各握把变体）之上的相对动作，天然兼容全部握把配置，无需 5×3 套片段。
- **接入**：`FPSGAMECharacter` 新增 `QuickCombatRifle` 组件与 `TriggerRifleStockMelee/CanTriggerRifleStockMelee/IsRifleStockMeleeArmed`（Gate 日志与手枪版同格式）；`FirePressed` 与 `IsWeaponBusy` 在砸击期间拦截开火与其他武器动作；`IsCastBlockingLeftHandAction` 纳入占用判定；`UColdSteelStatusModel::TriggerQuickCombat` 路由扩为 剑→配重锤 / 手枪→握把砸击 / **步枪→枪托砸击**。

## 文件与状态

- 新增：`Source/FPSGAME/Skills/FPSRifleStockMeleeComponent.h/.cpp`、`Source/FPSGAME/Skills/QuickCombatRifleMotion.h`。
- 修改：`FPSCastingMeshComponent.h/.cpp`（枪托姿态分支 + 左手跟随集）、`FPSGAMECharacter.h/.cpp`、`Skills/ColdSteelSkillModel.cpp`（路由）。
- 构建：2026-09-17 21:42 链接进 `UnrealEditor-FPSGAME.dll`（含「枪托砸击」日志串与 RifleStockBash 查询统计），后续 `Build-Editor.ps1` 复核 Result: Succeeded（全最新）。构建曾被并行会话的罗马凉亭 commandlet 进程按预检挡过一次，进程自然退出后完成。
- 未运行游戏；按全局规则由用户实测。测点建议：F 键（步枪在手）后拉-前撞节奏、接触命中/未命中、砸击中开火被拦、各握把与瞄准/奔跑状态进入、换枪/死亡中断。

## 数值边界

动作幅度、节奏与查询半径是 V1 制作参数（`QuickCombatRifleMotion.h` 集中放置），等实机反馈再调；伤害/距离/眩晕取快速进战技能数值（`QuickCombatStats()`），与手枪版共享同一套成长，未单独为步枪开新数值契约。

## 恢复入口（下次开发接手清单）

- 路由：`UColdSteelStatusModel::TriggerQuickCombat()` 剑/手枪分支之后加步枪分支；仲裁模板照抄 `TriggerPistolQuickCombat()`（Gate 日志同格式）。
- 姿态层：`UFPSCastingMeshComponent::FinalizeBoneTransform` 加第三分支；双手持枪的刚体偏移+双臂重解做法见本文"实现方式"节与 trash 里的 `ApplyRifleStockMeleePose` 原实现（双手腕目标=入场手位×武器刚体差值，指骨随父级跟随不开指）。
- 伤害：`GetMeleeAimTransform()` 视线球扫（ECC_Pawn 单目标）→ `ColdSteelSkills::ApplyHit`（`Shot.bRifle=true`）→ `ReceiveStun`；命中音 `S_MeleeHit_Quick`；冷却/修炼与手枪版同事务。
- 输入闸：`FirePressed`、`IsWeaponBusy`、`IsCastBlockingLeftHandAction` 三处与手枪版并排。
- 参考读谱（BV13K421e7Rw 1:05-1:07）：蓄势 0.38s 托底甩右上镜前（yaw−30°/pitch+18°）、扫击 0.45s 前左下横扫过画面中心（yaw−75°/pitch+28°，接触约 0.64s）、收势 0.45s；素材在 trash 的 reference/。
- 下次开发建议先做** Blender 内逐帧拟合预览**（把 trash 里的读谱帧导入 Blender 对位）再接回运行时；V1/V2 的失败点是没有实机画面比对就交付，参数拍脑袋成分高。
