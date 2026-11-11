# 碳钢战斧：双持冲刺就绪跑姿（2026-11-03）

用户：**双持**从普通跑步到触发冲刺攻击的就绪状态，按待机手势过渡；就绪状态时**左手沿用原来弯刀冲刺奔跑的姿势**，**右手再往上方举一些**。冲刺攻击本身不变，仍是原来的双手下劈。

三段 clip，套用剑的冲刺模式（进入 / 循环 / 退出），目标目录 `/Game/Weapons/TacticalHatchet20261101/Animations/`：

| clip | 资产 | 时长 | 说明 |
| --- | --- | --- | --- |
| `HatchetDualSprintEnter` | `A_TacticalHatchet_DualSprintEnter` | 0.30 s | 双持待机手势 → 举斧就绪；左手离开握姿进入跑步摆臂 |
| `HatchetDualSprintReady` | `A_TacticalHatchet_DualSprintReady` | 80/120 s 循环 | 右手举斧（比上一版高）、刃口向前，按左手的摆动同频同幅摆动（11-04）；左手是原弯刀冲刺跑姿的摆臂 |
| `HatchetDualSprintExit` | `A_TacticalHatchet_DualSprintExit` | 0.25 s | 举斧就绪 → 双持待机手势 |

## 要点

- **进入**：第一帧就是双持待机（`DualIdle` 第 0 帧）的手势，所以从普通跑步进来是先收回握姿再抬手，和“按待机手势过渡”一致。
- **就绪循环**：
  - 右手：`author_dual_sprint_right_arm.RAISE` 解出的姿势，头在准星右上方约 `0.34, −0.93`（上一版约 −0.76，这次更高）。
  - 左手：`A_Kukri_DualRun` 同相位的左臂（原弯刀冲刺跑姿的摆臂，见下方“修正（第二次）”）。
  - 右手：按左手的摆动同频同幅摆动（2026-11-04，见下节），与双持跑步同循环长度，全速跑时和腿对得上。
- **退出**：反向回到待机手势。
- **触发条件**：双持两把都是斧头、`DashReadyFraction()` 满格、地面冲刺 > 300。缺任一 clip 时整组回退到 `DualRun`。
- **攻击衔接**：就绪后点左键，从这三段任一状态进入原冲刺攻击时用 0.26 s 混合（普通 0.18 s），并把状态机复位。

## 运行接入

- `KukriWeaponComponent`：`bHatchetReadyRun`（三段都加载才生效）、`bDualHatchet`、`ReadyRunPhase`（0 无 / 1 进入 / 2 循环 / 3 退出）；`TickReadyRun()` 负责状态机和采样，`TickComponent` 在攻击分支之后调用它。
- `KukriDashAttack.cpp`：从就绪三段进入攻击时 0.26 s 混合并复位 `ReadyRunPhase`。
- `IsRunClip` 认这三段，进出与跑步共用混合时间。

## 2026-11-04 修正：就绪前保持待机移动姿态，右手跟左手同频同幅

用户：从奔跑到激活冲刺攻击奔跑的过程中保持待机移动的姿态；触发冲刺攻击奔跑时右手动画匹配左手的摆动频率和幅度。

- **就绪前**（运行时）：双持两把斧头时，冲刺而冲刺攻击未就绪期间不再切到 `DualRun`（反握冲刺跑姿），而是保持
  `DualWalk`（双持待机握姿 + 走路起伏，速率按速度到 1.4 倍上限）。就绪后从这个握姿进 `Enter`，和原来的起手一致。
  改在 `KukriWeaponComponent::LocomotionClip()`；单持斧头、弯刀都不变。
- **就绪循环的右手**：取 `A_Kukri_DualRun` 左拳一个步幅内的实测轨迹（握点相对步幅均值的屏幕偏移、深度偏移、
  握持旋转），镜像到右侧、**错开半步**（两臂交替；每步两次的起伏仍同步），绕举斧握点按**同样的屏幕轨迹**摆动；
  深度起伏按两拳深度比 0.71 缩放，旋转原样镜像。`ReadySet.left_swing_table()` / `right_swing()`，`SWING_PHASE=0.5`。
  旧的减半起伏（0.35/0.55/0.45 cm，竖直只有二次谐波）删除。
  - 左拳实测：左右 ±4.4 cm、上下 ±2.4 cm（一次）+ 1.0 cm（二次）、前后 ±1.5 cm、转角范围 8.8°，深度约 42 cm。
  - 生成结果：右/左握点屏幕摆幅 0.115/0.206 vs 0.114/0.206（NDC 宽/高）；右臂伸展 0.56–0.64（上限 0.67），
    扭转 −97～−94°，腕弯 ≤ 2.8°；斧头头部 NDC y −1.07～−0.86，摆到最高时略出画面上缘。
- **退出**（运行时）：两拳都在摆，循环可能停在步幅任意位置，`Exit` 改为 0.18 s（`SprintBlendSeconds`）从当前姿态混入，
  原来是 0 s 直接跳到退出首帧。
- 修改前的三段 clip、`clips.json`、头文件备份在 `Work/BeforeSwing20261104/`。导入回执修订号
  `HatchetReadyRun_V3_RightSwing_20261104`。
- 预览已按 V3 重渲（`PreviewsReady/sheet_*.jpg`）。左手斧改为跟着左拳（`virtual_hand` 取实际握点），原来是固定摆位。

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
- `Work/probe_left_swing.py`：打印 `DualRun` 两拳的轨迹范围、一/二次谐波和转角（右手摆动的取样依据）。
- `author_dual_sprint_right_arm.py`：解出右手举斧的关键姿势（`ready_frame()`，比攻击起手的 trigger 更高）。
- `import_hatchet_ready_run.py`：后台导入三段，回执 `import_receipt.json`。

## 资产与构建

- 三段已导入：`A_TacticalHatchet_DualSprintEnter` 0.300 s、`A_TacticalHatchet_DualSprintReady` 0.667 s 循环、`A_TacticalHatchet_DualSprintExit` 0.250 s。
- `FPSGAMEEditor Win64 Development` 构建 Succeeded：`Saved/BuildEditor/build-hatchet-ready3-20261103-202832.log`；DLL 里能查到三个 clip 名。
- 11-04（右手摆动 + 就绪前握姿）：三段重导（修订 `HatchetReadyRun_V3_RightSwing_20261104`，0 错误）；`FPSGAMEEditor` 构建
  Succeeded，`KukriWeaponComponent.cpp` 重编无警告：`Saved/BuildEditor/build-hatchet-ready-swing-20261104.log`。
- Game 目标未构建。未运行游戏、测试或验收。

## 预览

V7 可编辑手模，非实机：`PreviewsReady/sheet_0.jpg`、`sheet_1.jpg`（就绪循环，每 1/30 s 一格）。

## 未覆盖

- 第三人称跑步仍是 `Kukri.FullBody.Dual.Run`，没有单独做举斧跑姿。
- 单持斧头的跑步与冲刺攻击都不变。
