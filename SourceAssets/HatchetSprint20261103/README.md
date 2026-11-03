# 碳钢战斧：双持冲刺就绪跑姿（2026-11-03）

用户：**双持**从普通跑步到触发冲刺攻击的就绪状态，按待机手势过渡；就绪状态时**左手沿用原来弯刀冲刺奔跑的姿势**，**右手再往上方举一些**。冲刺攻击本身不变，仍是原来的双手下劈。

三段 clip，套用剑的冲刺模式（进入 / 循环 / 退出），目标目录 `/Game/Weapons/TacticalHatchet20261101/Animations/`：

| clip | 资产 | 时长 | 说明 |
| --- | --- | --- | --- |
| `HatchetDualSprintEnter` | `A_TacticalHatchet_DualSprintEnter` | 0.30 s | 双持待机手势 → 举斧就绪；左手离开握姿进入跑步摆臂 |
| `HatchetDualSprintReady` | `A_TacticalHatchet_DualSprintReady` | 80/120 s 循环 | 右手举斧（比上一版高）、刃口向前；左手是原弯刀冲刺跑姿的摆臂 |
| `HatchetDualSprintExit` | `A_TacticalHatchet_DualSprintExit` | 0.25 s | 举斧就绪 → 双持待机手势 |

## 要点

- **进入**：第一帧就是双持待机（`DualIdle` 第 0 帧）的手势，所以从普通跑步进来是先收回握姿再抬手，和“按待机手势过渡”一致。
- **就绪循环**：
  - 右手：`author_dual_sprint_right_arm.RAISE` 解出的姿势，头在准星右上方约 `0.34, −0.93`（上一版约 −0.76，这次更高）。
  - 左手：**保持双持待机（`DualIdle` 第 0 帧）的手势**，不再套用弯刀冲刺跑姿的摆臂（2026-11-03 用户指正：冲刺就绪跑姿应当直接以待机手势奔跑）。三段动画都用同一套左手。
  - 右手带减半幅度的跑步起伏，与双持跑步同循环长度，全速跑时和腿对得上。
- **退出**：反向回到待机手势。
- **触发条件**：双持两把都是斧头、`DashReadyFraction()` 满格、地面冲刺 > 300。缺任一 clip 时整组回退到 `DualRun`。
- **攻击衔接**：就绪后点左键，从这三段任一状态进入原冲刺攻击时用 0.26 s 混合（普通 0.18 s），并把状态机复位。

## 运行接入

- `KukriWeaponComponent`：`bHatchetReadyRun`（三段都加载才生效）、`bDualHatchet`、`ReadyRunPhase`（0 无 / 1 进入 / 2 循环 / 3 退出）；`TickReadyRun()` 负责状态机和采样，`TickComponent` 在攻击分支之后调用它。
- `KukriDashAttack.cpp`：从就绪三段进入攻击时 0.26 s 混合并复位 `ReadyRunPhase`。
- `IsRunClip` 认这三段，进出与跑步共用混合时间。

## 2026-11-03 修正（第二次）：左手（已撤回）

- 曾把三段动画的左手权重改成 0（双持待机手势），用户复核后要求**撤回**该修改。
- 现状：左手恢复为 **`A_Kukri_DualRun` 同相位的左臂**（即上一版），进入/退出随右手一起缓入缓出，循环段权重 1。
  已核对 `clavicle_l / upperarm_l / lowerarm_l / hand_l` 与 `DualRun` 第 0 帧位姿完全一致。
- 右手举斧、跑步起伏、时序都不变。

## 2026-11-03 修正：手与斧穿模

- 原因：`assemble()` 合成左臂后从 `R.base_local` 重建整副姿态，把已解出的右臂打回基础站姿，右手与举起的斧头错开约 17 cm（`|K-hand_r|` 7.6→16.8 cm）。现已改为在解出的姿态上只覆盖左臂。
- 复核（`Work/check_ready_contact.py` + `Work/check_ready_fine.py`，V7 手模 + 真实斧网格）：
  - 右手握持压入 0.69 cm，与已验收的装备握持（0.65–0.77 cm）同量级；左手 0.76 cm。
  - 斧头对另一侧手臂、头、自身前臂的穿插均为 0。
- 修正后三段已全部重导（`import_receipt.json`）。

## 文件

- `author_hatchet_ready_run.py`：拼三段 clip，输出 `Clips/HatchetDualSprint{Enter,Ready,Exit}.json`、`HatchetReadyRhythm.h` 和预览。
- `author_dual_sprint_right_arm.py`：解出右手举斧的关键姿势（`ready_frame()`，比攻击起手的 trigger 更高）。
- `import_hatchet_ready_run.py`：后台导入三段，回执 `import_receipt.json`。

## 资产与构建

- 三段已导入：`A_TacticalHatchet_DualSprintEnter` 0.300 s、`A_TacticalHatchet_DualSprintReady` 0.667 s 循环、`A_TacticalHatchet_DualSprintExit` 0.250 s。
- `FPSGAMEEditor Win64 Development` 构建 Succeeded：`Saved/BuildEditor/build-hatchet-ready3-20261103-202832.log`；DLL 里能查到三个 clip 名。
- Game 目标未构建。未运行游戏、测试或验收。

## 预览

V7 可编辑手模，非实机：`PreviewsReady/sheet_0.jpg`、`sheet_1.jpg`（就绪循环，每 1/30 s 一格）。

## 未覆盖

- 第三人称跑步仍是 `Kukri.FullBody.Dual.Run`，没有单独做举斧跑姿。
- 单持斧头的跑步与冲刺攻击都不变。
