# 高倍镜（LPVO 1–6×）开火表现 · 2026-09-17

用户反馈：高倍镜下开火只有镜内一个小火光，看起来"没打枪"。本轮按三层方案实现，**仅作用于 1–6× 高倍镜**（`lpvo_1_6x`），2× 棱镜与其它瞄具不受影响。

## 原因

- 高倍 ADS 时 `AFPSGAMECharacter::UpdateScopePresentation()` 把整支第一人称枪模（含枪口）对持枪者隐藏，镜内画面由 `ULPVOScopeWidget` 的环形遮罩 + 分划提供。
- 枪口 Niagara 仍按世界空间生成在枪口 socket 上；6× 下相机 FOV 很窄，枪口在视线下方几度就已出画，只剩落进窄视锥的那一小块可见。
- 原 `bScope` 分支（`ShouldHideCasings()`，语义恰好等于 LPVO 1–6×）只调整了世界火光的侧面概率与亮度，没有独立的表现层。

## 已实现

### 第 1 步 镜内表现层（`Source/FPSGAME/UI/LPVOScopeWidget.cpp`）

画在**镜口遮罩之上、分划之下**，十字线始终最后绘制。由开火时间戳驱动的软径向光斑（8 段同心带，白热→橙），中心在镜口中心右下偏下（枪口方向），沿枪口轴拉长 15%、横向压窄 20%，每发用时间戳推导的确定性随机值产生 ±23° 倾斜。衰减 `(1-t)²`，默认 70 ms。

### 第 2 步 世界层倍率补偿（`Source/FPSGAME/Weapons/FPSWeaponFXComponent.cpp`）

仅在 `bScope`（LPVO 1–6×）时生效：世界火光按 `pow(倍率, 指数)` 受控放大，硬上限夹住，并把生成点沿枪口轴向前推一点，让更多火光落进窄视锥。默认 6× 补偿系数约 2.4×、前移约 17 cm；不会出现"巨大模糊球"。

### 第 3 步 镜片效应（同镜内层）

- **镜口边缘泛光**：射击瞬间镜口内缘一圈暖色辉光，随火光一起衰减（同一 70 ms 窗口）。
- **镜片污渍**：7 个固定位置的极淡污点常驻镜内，被枪口火光短暂点亮（经典的 lens dirt 反应）。
- **射击后热浪烟丝**：220 ms 内两条柔软烟雾飘带自镜口下缘向上飘散、淡入淡出，位置是开火时间的纯函数（控件无状态），每发带随机偏移。

## 参数（控制台变量，默认值即当前手感；设 0 即关闭该项）

| 变量 | 默认 | 作用 |
| --- | --- | --- |
| `fps.Scope.FlashAlpha` | 0.55 | 镜内火光峰值透明度 |
| `fps.Scope.FlashHoldMs` | 70 | 镜内火光生命周期（ms） |
| `fps.Scope.FlashRadius` | 0.30 | 火光半径占镜口半径比例 |
| `fps.Scope.FlashOffsetX / Y` | 0.16 / 0.52 | 火光中心偏移（镜口半径为单位） |
| `fps.Scope.EdgeBloomAlpha` | 0.38 | 镜口边缘泛光强度 |
| `fps.Scope.LensDirtAlpha` | 0.10 | 镜片污渍基础不透明度 |
| `fps.Scope.SmokeAlpha` | 0.16 | 热浪烟丝峰值不透明度 |
| `fps.Scope.SmokeHoldMs` | 220 | 热浪烟丝生命周期（ms） |
| `fps.Scope.WorldScaleExponent` | 0.5 | 世界火光倍率补偿指数（0 = 不补偿） |
| `fps.Scope.WorldScaleMax` | 2.5 | 世界火光补偿硬上限 |
| `fps.Scope.WorldForwardCM` | 12 | 满补偿时沿枪口轴前移量（cm） |

## 不影响射击与瞄准的红线

1. 特效层不写 `ControlRotation`；命中方向仍来自相机/分划基准（`ComputeShotDirection` 未改）。
2. 世界层只改 Niagara 组件的位置与 `User.Global Scale`，枪口 socket、射向与射线不动。
3. 镜内元素一律避开分划中心（按偏移夹住半径，内缘不越过十字），火光有硬性生命上限，任何一帧都不挡瞄点。
4. 不新增 `SceneCapture`、灯光、阴影；所有镜内元素共用白色笔刷与自定义顶点，空闲时（无最近射击）仅剩一层极淡污渍，可再关掉。

## 覆盖范围

只覆盖 `lpvo_1_6x`（`GetScopePresentationAlpha()` / `ShouldHideCasings()` 的判定即为此镜）。2× 棱镜不隐藏枪模、世界火光本来可见，本轮未改；需要的话可单独开分支。

## 状态

`FPSGAMECharacter.cpp`、`M4GunsmithVisual.cpp`、`LPVOScopeWidget.cpp`、`FPSWeaponFXComponent.cpp` 均编译通过、无诊断（日志 `Saved/BuildEditor/build-scopefx23-compile.log`）。按用户规则**未启动游戏、未截图、未做视觉验收**；实机请在 1×/2×/6× 下确认尺寸、亮度、连发观感与分划可读性。落地时编辑器仍开着，DLL 链接被占用（`LNK1104`），需关闭编辑器或授权结束后重跑 `Tools/Build/Build-Editor.ps1`。
