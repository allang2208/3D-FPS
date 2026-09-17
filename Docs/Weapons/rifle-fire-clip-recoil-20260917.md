# 步枪后坐力表现对齐：火动画差异与补齐层 · 2026-09-17

用户反馈：三把步枪里只有 M4 的后坐力表现合格（模型向后跳动、垂直/水平后坐都看得见），QBZ-191 和 AKM「几乎没有」，要求以 M4 为参照同步另外两把的表现。

## 1 结论（已核实）

用户判断成立。**程序弹簧那层是三把枪共用的，差异全在各自独立的「开火动画」资产上**：M4 的开火动画本身把枪推了出去，191 只带四分之一的量，AKM 的开火动画枪根完全静止。

## 2 排查过程与证据

### 2.1 排除的项（都不是原因）

- **武器后坐力索引**：`Content/ColdSteelData/gunsmith.json` 里 `ue_m4a1` / `ue_akm` / `ue_qbz191` 的 `recoil` 与 `camera_shake` **都是 100 / 100**（手枪类才是 110/95、155/125）。
- **程序表现层**：`ApplyShotFeedback()` → `GunKick*` / `GunFlip` → `UpdateViewmodel()` 的姿势映射对三把枪完全共用，没有按枪分支；`FPSVisualRecoil::ForWeapon()` 的剖面差异很小（AKM 的 `Position.Z 1.22 / Rotation.X 0.94` 甚至比 M4 的 `1.16 / 0.80` 更重）。
- **摆臂弹簧**：刚度/阻尼、`ViewmodelGain`、`VisualRecoilScale` 均共用。

### 2.2 火动画是差异来源

每把枪各自加载自己的开火动画（`LoadAKAMAnimation()`）：

| 枪 | 运行资产 | 帧数/时长 | 来源 |
| --- | --- | --- | --- |
| M4 | `/Game/Weapons/M4ContactImpactFinal/A_AKM_fire` | 24 帧 / 0.767 s | 原 Infima 包 `Fire` 动作，自 `/Game/Weapons/M4InfimaRigV4/` 复制（`SourceAssets/M4ContactImpact20260910/publish.py`） |
| QBZ-191 | `/Game/Weapons/QBZ191/Refined20260913/Animations/base/A_QBZ191_fire` | 46 帧 / 0.767 s | `SourceAssets/QBZ191Refine20260913/build.py` 自烤 |
| AKM | `/Game/Weapons/AKMIntegration/SourceMatched/A_AKM_fire` | **6 帧 / 0.1 s** | `SourceAssets/AKMIntegration20260910/SourceMatched/` |

### 2.3 量化：枪根骨骼在整段动画里的最大位移/转角

用新增的只读读取器 `Tools/AssetPipeline/read_animation_curves_fbx.py` 直接读 FBX 源（懒解析数组，避免大几何缓冲拖死进程）：

```
python Tools/AssetPipeline/read_animation_curves_fbx.py <file.fbx> WPN_root
```

| 枪 | `Lcl Translation` 峰值 | `Lcl Rotation` 峰值 | 峰值时刻 |
| --- | --- | --- | --- |
| M4 | **Z 1.934 cm**（Y 0.205 cm） | **Z 3.040°**（X 1.004°、Y 0.953°） | 0.033 s |
| QBZ-191 | **Y 0.488 cm** | **X 0.732°** | 0.067 s |
| AKM | **0 / 0 / 0** | **0 / 0 / 0** | — |

AKM 那条 0.1 s 的残桩动画里枪根骨骼三个轴全是零——枪在动画里根本没动，全部后坐只能靠共用弹簧，因此观感最弱。QBZ 的量约为 M4 的四分之一，且是 67 ms 的软脉冲（源码 `build.py` 里 `w=sin(min(f/10,1)*π)*exp(-f/9)`，仅前 10 帧有效，位移 0.008 m、转角 1.2°）。M4 则是 33 ms 内一步到位、随后回落的硬脉冲。

### 2.3.1 开镜（ADS）用的是另一支 `aim_fire` 动画

| 枪 | `aim_fire` 位移峰值 | `aim_fire` 转角峰值 | 与腰射的关系 |
| --- | --- | --- | --- |
| M4 | **Z 2.323 cm**（Y 0.049 cm） | **X 0.481°、Y 0.151°**、Z 0° | 位移比腰射更大（1.93 → 2.32 cm），**转角几乎归零**（3.04° → 0.48°） |
| QBZ-191 | Y 0.488 cm | X 0.732° | 与它的腰射是同一支脉冲，未区分 |
| AKM | 0 / 0 / 0 | 0 / 0 / 0 | 同为残桩 |

M4 的 ADS 性格是**整枪直退、几乎不转头**——这正是机械瞄具在开镜连射下仍留在视线上的原因。任何按腰射幅度叠加到 ADS 的做法都会把枪转头（约 2°）并顶满轴向夹值（5.5 cm），瞄具被打出视线。

### 2.4 轴向口径

FBX 里同一根骨骼在三把枪上的主轴不同（M4 主位移在 Z、QBZ 在 Y），说明「枪根骨骼主轴」并不统一。本轮按**量值**对齐：把 M4 的实测幅度中最大的一项落到「向后」（姿势的轴向）与「枪口抬起」（俯仰），其余次要分量分给横摆与侧倾。这是量值映射假设，不是骨骼空间逐轴换算；实机方向与配比由用户按 `fps.Weapon.ClipRecoil` 复核。

## 3 本轮实现：火动画补齐层（程序表现，不动资产）

> **ADS 追加修正（当日第二轮）**：首版把腰射的幅度直接套进 ADS，用户实测 AKM 开镜后"在后坐力冲击下几乎看不到机械瞄具"。原因是 M4 的 ADS 走的是**另一支 `aim_fire` 动画**，性格与腰射完全不同：枪向后**推 2.32 cm**、却只转 **0.48°（俯仰）+ 0.15°（横摆）**——整枪直退、几乎不转头，机械瞄具因此始终留在视线上；腰射那支则是 1.93 cm / 3.04°。首版把 3.04° 转角与 ×3.2 的轴向倍率带进 ADS，等于每发把枪转头约 2° 并顶到 5.5 cm 夹值，瞄具被打出视线。现已按 ADS 单独取值、并按实测 1:1 叠加（不乘 `ADSAxialScale`、转角不乘 `VisualRecoilScale`，只受 `ScopeConvergence` 影响）。

> **ADS 第三轮：机械瞄具可用性与"弹道跟着准星"（同日）**：用户复测 AKM 开镜后"竖线开火后直接消失，无法用机械瞄具瞄准"。根因是**转角与瞄具半径的乘积**：`AKMSoviet::Front - Rear` 的照门—准星间距是 **38.7 cm**（`AKMSovietCalibration.h`），所以枪身转 1° 就会把准星相对照门推开约 **0.68 cm**，而照门缺口只有几毫米——竖线因此被缺口壁挡掉。首版在 ADS 叠加的 0.48° 加上弹簧自身的 0.93°（`0.025 rad 夹值 × VisualRecoilScale 0.65`）合计约 1.4°，正好越过临界。第三轮做三件事：
>
> 1. **ADS 转角补偿归零**（AKM 与 QBZ 都是 `ClipADSRotation = 0`）：任何转角都会同时破坏"准星在缺口内"和"视线可用"，而纯轴向平移不会——沿视线轴的平移既保持照门/准星对齐，也不改变"眼睛→准星"的射线方向，所以弹道方向天然不变。
> 2. **新增 `ADSRotationScale`**：给长基线的机械瞄具压制弹簧自身的 ADS 转角。AKM 取 `0.4`（0.025 × 0.65 × 0.4 ≈ **0.37°**，准星偏离缺口中心约 0.25 cm，留在缺口内）；M4/QBZ 维持 1（基线短，原本可用，不动已接受的手感）。
> 3. **ADS 轴向补偿收到 1.0–1.2 cm**（原 2.32 cm）：整组刚体后退与动画里"身体吸收"的后退不同，视觉上等同于把瞄具拉向眼睛，幅度必须远小于参考动画的骨骼值。
>
> 弹道一致性本身由现有结构保证，本轮未改：`ComputeShotDirection()` 对 AKM 走 `AKMViewmodel->GetSocketTransform("WPN_root").TransformPosition(AKMSoviet::Front)`（即"相机位置→准星基准点"），其它枪型走 `WPN_FrontSight` 骨骼或相机前向；因为读的是**当前**视模变换，补偿层怎么动，射线就跟着动，实弹落点始终等于屏幕上准星的投影位置。项目已有的 `AKMSightAudit` 验的就是这条（准星投影在屏幕中心 <2 px、与照门对齐 <2 px、实弹落点与可见瞄具射线 <2 mm）。

在 `FPSVisualRecoil::FProfile` 增加：

```cpp
// position: 米（Z 向后、X 向右、Y 向上）；rotation: 弧度（X 枪口抬起、Y 横摆、Z 侧倾）
FVector ClipPosition = FVector::ZeroVector;      // 腰射
FVector ClipRotation = FVector::ZeroVector;
FVector ClipADSPosition = FVector::ZeroVector;    // 开镜（另一支 aim_fire）
FVector ClipADSRotation = FVector::ZeroVector;
```

`FPSVisualRecoil::ClipWave(Seconds)` 生成与参考动画同形的时间包络：**33 ms 内平滑到位，之后按 0.11 s 时间常数回落**（参考动作的实测峰值时刻即 0.033 s）。

各枪取值（M4 = 0，因为它本来就由自己的动画携带）。腰射转角取「参考值 − 本枪实测值」且**不为负**（QBZ 的 0.73° 已超过参考的 0.48°）；**开镜转角一律为 0**，只保留一条纯轴向的直退（第三轮结论：长基线机瞄下任何转角都会让准星离开缺口）：

| 枪 | `ClipPosition`（米，腰射） | `ClipRotation`（弧度，腰射） | `ClipADSPosition`（米） | `ClipADSRotation` | `ADSRotationScale` |
| --- | --- | --- | --- | --- | --- |
| M4 | 0 | 0 | 0 | 0 | 1 |
| QBZ-191 | 1.45 cm 向后 | 2.31° / 0.95° / 1.00° | 1.00 cm 向后 | 0 | 1 |
| AKM | 1.93 cm 向后 | 3.04° / 0.95° / 1.00° | 1.20 cm 向后 | 0 | 0.4 |

- 写入口：`AFPSGAMECharacter::ApplyShotFeedback()` 里 `ClipRecoilSeconds=0.f`（每发重置包络）；`UpdateWeaponFeedback()` 累加；切枪时在 `FPSGAMECharacterProfile.cpp` 与其他视觉后坐状态一起归位 `-1`。
- 叠加位置：腰射在弹簧 tanh/长度夹**之后**加到 `GodotPose` 与 `GodotAngles`；ADS 分支同样加在 `GetClampedToMaxSize(0.025)` 之后。理由：它替代的是动画运动，不能被弹簧限幅削平——姿势层的俯仰上限只有 2.58°，低于腰射参考的 3.04°。
- **叠加口径**：补偿按实测值 **1:1** 进入姿势，不再乘 `ADSAxialScale`（3.2）或 `VisualRecoilScale`（0.65）。这两个系数是给弹簧设计的手感倍率，套到动画等效量上会把 2.32 cm 放大到 7.4 cm、把 0.48° 缩到 0.31°，两头都偏离参考。高倍镜仍受 `ScopeConvergence` 影响（与本项目既有的镜内收敛一致）。
- **瞄具可用性**：ADS 的枪身转角 = `ADSKickAngles`（弹簧被 `0.025 rad` 夹住）`× VisualRecoilScale × ADSRotationScale × ScopeConvergence` + `ClipADSRotation`。AKM 的 38.7 cm 照门—准星基线让 1° 就产生约 0.68 cm 的横向错位，因此 `ADSRotationScale = 0.4`；铁瞄下 `ScopeConvergence = 1`，高倍镜才是它收敛的场合。
- 双持手枪、近战与技能路径未接入（剖面补偿量为 0）。
- 调参：`fps.Weapon.ClipRecoil`（默认 1，0 关闭整层，**负值把整层方向翻转**——用于现场核对后坐力反馈方向，不必重编译）。

## 4 边界：本轮没动的东西

- 火动画资产本身（AKM/QBZ 的 FBX 与 uasset 未改）：因此**手臂在开火瞬间仍然不动**，补齐的是枪（含随枪的整组手臂刚体变换）。若要求手臂也参与（M4 那种手腕/肩部吸收），需要重烤三把枪的开火动画，属独立一轮。
- 弹道后坐力（`Pattern`、`BallisticRecoilScale`、`SetControlRotation`）、射速、伤害、散布、准心、音效与存档未改。
- 共用弹簧的刚度/阻尼、`ViewmodelGain`、`VisualRecoilScale`、相机层（`FeedbackScale`、`CameraKick`、`fps.Camera.*`）未改；上一轮的镜头抖动强化保持原样。
- 未改动画时序合同：换弹/装备的接触帧、`MechanicalCueTimes`、`ActionBlendIn` 均未触碰。

## 5 工具

`Tools/AssetPipeline/read_animation_curves_fbx.py`：只读 FBX，按骨骼名打印指定通道的逐轴峰值与峰值时刻。数组按需解码并做长度上界校验（早期版本会一次性展开几何缓冲，导致进程吃满内存）。用法：

```
python Tools/AssetPipeline/read_animation_curves_fbx.py SourceAssets/M4Infima/A_AKM_fire.fbx WPN_root
```

## 6 状态

- 代码：`Source/FPSGAME/Weapons/FPSVisualRecoil.h`、`Source/FPSGAME/FPSGAMECharacter.h/.cpp`、`Source/FPSGAME/FPSGAMECharacterProfile.cpp`；工具：`Tools/AssetPipeline/read_animation_curves_fbx.py`。
- 构建（腰射首版）：`Tools/Build/Build-Editor.ps1` 返回 `Result: Succeeded`（96 个动作），日志 `Saved/BuildEditor/build-20260917-145357.log`，产物 `Binaries/Win64/UnrealEditor-FPSGAME.dll`（2026-09-17 14:54）。
- 构建（ADS 修正版）：先只有编译成功（`FPSGAMECharacter.cpp`、`FPSGAMECharacterVisualRecoil.cpp` 无错误、`.lib` 链接成功），最终 DLL 因编辑器占用被拒（`LNK1104`，日志 `Saved/BuildEditor/build-ads-compile.log`）；用户授权结束遗留的编辑器进程（PID 33216）后重跑，`Result: Succeeded`（2 个动作：链接＋元数据），日志 `Saved/BuildEditor/build-20260917-151539.log`，产物 `Binaries/Win64/UnrealEditor-FPSGAME.dll`（2026-09-17 15:15:42，晚于源码 15:05）。当天**无新增崩溃目录**（最近一次为 9-16 20:14），本轮改动未引发崩溃。
- 构建（第三轮·机瞄可用性）：`Result: Succeeded`（5 个动作，含 `FPSGAMECharacter.cpp` 重编与链接），日志 `Saved/BuildEditor/build-20260917-152221.log`，产物 `Binaries/Win64/UnrealEditor-FPSGAME.dll`（2026-09-17 15:22:32）。当天**无新增崩溃目录**（最近一次为 9-16 20:14），本轮改动未引发崩溃。
- 按用户规则**未启动游戏、未截图、未做手感验收**。实机建议：AKM 开镜连发，确认 1) 准星竖线是否始终留在照门缺口内、开火后仍可瞄准（本轮修正点）；2) 落点是否与竖线一致（项目已有 `AKMSightAudit` 可离线复核这条）；3) 腰射与开镜的向后跳动是否仍与 M4 接近。方向若不对，先 `fps.Weapon.ClipRecoil -1` 现场翻转，再决定是否改默认值。
