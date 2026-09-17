# 镜头抖动强度强化 · 2026-09-17

用户反馈：开火时的镜头抖动幅度太小（"应该是基数太低了"），换挡（换弹／装备过渡）过程中的抖动几乎看不到，要求整体强化 gunplay 的力量感。本轮只改**镜头表现层的强度**，弹道后坐、射速、伤害、散布与视模（枪身／枪口）弹簧全部不动。

## 原因：两个基数把镜头层压得很低

1. 开火镜头层（`CameraKick`、`CameraJitter`、`FireTrauma`、`FOVPunch`）在 `FPSGAMECharacter::ApplyShotFeedback()` 里统一乘 `AKMSource::FeedbackScale`，而它是 `0.5`。叠加 `ImpulseScale = Lerp(9,13,ADS)`，首发单发的镜头俯仰峰值只有约 **0.06°**（连射末发约 0.18°，镜头 jitter 再加约 0.09°）——视模在抖，十字线背后的画面几乎没动。现在首发约 **0.17°**、末发约 **0.53°**，jitter 约 0.34°。
2. 换挡层（`UWeaponActionCameraComponent::Apply()`）已经要乘 `CameraMotionScale = 0.45`，再用旧的 `Strength 2.0 / ImpactStrength 1.75`，接触脉冲（弹匣脱出／插入／压实／拉栓）的峰值约 4.4°；用户实测看不到。

## 1 开火镜头层（`Source/FPSGAME/FPSGAMECharacter.cpp`）

| 项 | 旧 | 新 | 相对旧值 |
| --- | --- | --- | --- |
| `AKMSource::FeedbackScale`（该层总基数） | 0.5 | **1.0** | ×2 |
| 镜头 kick 冲量 `Lerp(…, WeaponADSFactor)` | 9 / 13 | **13 / 19** | ×1.44（腰射）/ ×1.46（ADS） |
| 镜头 jitter 系数（位置 / 旋转） | 0.06 / 0.18 | **0.11 / 0.34** | ×1.83 / ×1.89 |
| `FireTrauma` 每发增益 | 0.06 | **0.11** | ×1.83（平方渲染，见下） |
| `AKMSource::ShakeDecay`（trauma 衰减） | 3.5 | **3.0** | 停留更久 |
| `FOVPunch`（腰射 / ADS） | 0.65° / 0.15° | **1.2° / 0.4°** | ×1.85 / ×2.67 |

综合到镜头上的倍率：kick 约 **×2.9**，jitter 约 **×3.7**，FOV punch 约 **×1.9（腰射）～×2.7（ADS）**。Trauma 因为渲染时取平方，观感提升比线性更大：6 发时 trauma 值 0.36→0.66，平方后 0.130→0.436，再乘新基数 ×2，约 **×6.7**；10 发即封顶 1.0（旧值 0.6），约 ×5.6。也就是说连射会**越打越晃**，这是本轮"力量感"的主要来源；单发靠 kick ＋ jitter 的短促脉冲。

双持手枪走 `ApplyDualWieldShotFeedback()`，同一套系数与 CVar，另乘原有的 `Dual.CameraGain`（手枪 1.25 / 左轮 1.60）不变。

## 2 换挡镜头层（`WeaponActionCameraComponent` ＋ `Config/DefaultGame.ini`）

`UWeaponActionCameraComponent` 的三个强度是 `Config` 属性，工程里 `Config/DefaultGame.ini` 的 `[/Script/FPSGAME.WeaponActionCameraComponent]` 段会覆盖 CDO，两处必须同步改（已同步）。

| 项 | 旧 | 新 | 相对旧值 |
| --- | --- | --- | --- |
| `Strength` | 2.0 | **2.8** | ×1.4 |
| `FollowStrength`（跟随曲线） | 1.5 | **2.0** | ×1.33 |
| `ImpactStrength`（接触脉冲） | 1.75 | **2.6** | ×1.49 |

落到画面：接触脉冲约 **×2.08**、跟随曲线约 **×1.87**。例：弹匣脱出脉冲的 roll 峰值 2.8°，生效值从约 4.4° 提到约 **9.2°**（已含 `CameraMotionScale 0.45`）。`ImpactStrength` 的 `ClampMax` 从 2.0 提到 4.0 以满足新值。曲线关键帧（Out / Insert / Seat / Bolt 的时间与角度）保持原样，只改强度倍率。

## 3 调参入口（控制台变量，默认即当前手感）

| 变量 | 默认 | 作用 |
| --- | --- | --- |
| `fps.Camera.Shake` | 1 | 开火镜头层总倍率：kick、jitter、trauma 渲染强度、FOV punch（单持与双持都生效） |
| `fps.Camera.ActionShake` | 1 | 换弹／装备镜头层总倍率 |

两个 CVar 都只乘表现层，不参与控制流。设 0.5 即回到接近旧幅度的感觉，设 2 可再翻倍；不需要重新编译。

## 4 红线：本轮明确没动的东西

- **弹道与瞄准**：`FWeaponHandling::Pattern`、`BallisticRecoilScale`、`SetControlRotation` 的弹道后坐、`ComputeShotDirection()`、`GetHipSpread()` 全部未改。镜头叠加偏移本来就参与相机基准，本轮只改幅度，不改耦合方式。
- **视模（枪身／枪口）弹簧**：`GunKick*`、`GunJitter*`、`GunFlip`、`FPSVisualRecoil::FProfile`、`VisualRecoilScale`、`AKMSource::ViewmodelGain` 未改——用户澄清要的是镜头抖动，枪口那层留待单独要求。
- **回稳时间与分区不变**：相机弹簧 `CameraKickStiffness/Damping`、`ADSJitterMultiplier`、`CameraMotionScale`、`FOVPunchDecay`、`WeaponHandling` 的 `RecoveryTimeScale` 与 `ADSRecoveryMilliseconds()` 未改；只有 trauma 的衰减 `ShakeDecay` 3.5→3.0 是有意延长。30/60/144 Hz 分区与"90% 包络"关系仍按原公式成立。
- 射速、伤害、弹匣、散布、音效、存档、枪匠数值与图标未改。

## 5 已知边界

换挡镜头层只对 **M4**（`bM4Camera` 判定：M4 Infima、非 QBZ191、非手枪）生效。AKM／QBZ-191／M1911／Dan Wesson 的换弹目前**没有**这一层（它们已有 `MechanicalCueTimes` 接触时刻，后续可按同一模板接，但每把枪的源时钟映射要单独核对）。

## 6 状态

- 代码：`Source/FPSGAME/FPSGAMECharacter.cpp`、`Source/FPSGAME/Weapons/WeaponActionCameraComponent.h/.cpp`；配置：`Config/DefaultGame.ini`。
- 构建：`Tools/Build/Build-Editor.ps1` 返回 `Result: Succeeded`（15 个动作，含 `FPSGAMECharacter.cpp`、`WeaponActionCameraComponent.cpp` 编译与新 `UnrealEditor-FPSGAME.dll` 链接），日志 `Saved/BuildEditor/build-20260917-111414.log`；产物 `Binaries/Win64/UnrealEditor-FPSGAME.dll`（2026-09-17 11:14）。构建前的警告 `VoxelCollapseFragment.cpp C4305` 为既存项，与本轮无关。
- 按用户规则**未启动游戏、未截图、未做手感验收**。实机建议：M4 上依次试单发、连射（体会 trauma 随发数增长）、ADS、普通换弹／空弹换弹／弹鼓换弹与切枪装备；不合意就先用两个 CVar 当场调，再把默认值回灌本文件。

## 7 发布边界（2026-09-17 提交时）

本轮发布只包含开火镜头层：`FPSGAMECharacter.cpp` 的基数、各层系数与 `fps.Camera.Shake`。**换挡层（`WeaponActionCameraComponent.h/.cpp` 的 2.8／2.0／2.6 与 `fps.Camera.ActionShake`、以及 `Config/DefaultGame.ini` 的同名段）未随本次提交发布**——该组件是另一个工作会话尚未提交的产物（其调用点也在对方的未提交 hunk 里），按"不夹带并行在途工作"的规则留在工作区，由该会话自行发布。`fps.Camera.ActionShake` 的默认值语义（1 = 当前手感）在它发布后生效。
