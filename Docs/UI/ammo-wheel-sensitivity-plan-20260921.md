# 长按 R 弹种轮盘：拖动灵敏度修正与调参（2026-09-21）

入口：持枪时长按 R（0.30 秒）打开 `UColdSteelAmmoWheel`，移动鼠标预选弹种，松开 R 换弹。规则见 [冷钢 UI 正式规则](ui-cold-steel-design-system.md)，轮盘与弹药袋合同见 [动态弹种轮盘与弹药袋](../../skills/ue5-ui-umg-slate/references/ammo-radial-and-pouch.md)，玩法事务见 [数字弹药袋](../../skills/ue5-weapon-workflow/references/ammo-pouch-and-types.md)。

## 目标与交付阶段

- 用户反馈：轮盘里鼠标太难拖动，灵敏度太低。目标是把预选光标的手感提到可用水平，并留下可调参数。
- 范围：只改轮盘指针增益与输入换算；不改扇区几何、死区／滞回、提交与换弹流程。
- 阶段：游戏接入中的参数修正。预览与测试未要求，由用户实测手感。

## 原因分析

| 环节 | 事实 | 结论 |
| --- | --- | --- |
| 轴映射 | `Config/DefaultInput.ini`：`+AxisMappings=(AxisName="Turn",Scale=1.000000,Key=MouseX)`、`LookUp` 用 `MouseY` | `Turn/LookUp` 每帧收到鼠标轴值 |
| 轴灵敏度 | 同文件 `+AxisConfig=(AxisKeyName="MouseX",...Sensitivity=0.070000)`（`MouseY` 同值） | 1 个屏幕像素只产生 **0.07** 轴值 |
| 相机口径 | `AddControllerYawInput(Value * LookSensitivityScale())`，腰射时 `LookSensitivityScale()==1` | 相机侧就是按 0.07 设计，正常 |
| 轮盘口径 | `MovePointer`：`Pointer=(Pointer+Delta/200.).GetClampedToMaxSize(.96)` | 把轴值当像素用，等于按 0.07/200 折算 |

`Pointer` 是半径比例（0–1，上限 0.96），所以旧实现需要 `200/0.07 ≈ 2857 px` 鼠标位移才能从中心走到外环，跨屏也拖不满一圈 —— 与“很难拖动”一致。它是**单位错误**（14.3 倍偏慢），不是主观手感问题。

## 交互合同（修正后）

| 项 | 值 | 说明 |
| --- | --- | --- |
| 输入单位 | `MovePointer` 接收**屏幕像素** | 轴值在角色输入层用轴配置灵敏度还原为像素 |
| 增益 | `fps.AmmoWheel.PixelsPerRadius`，默认 **180** | 180 px 走满一个半径；数值越小越灵敏，下限 40 |
| 死区 | 0.30 半径（不变） | 换算后约 54 px 起选 |
| 外限 | 0.96 半径（不变） | |
| 边界滞回 | `min(4°, 扇区宽 10%)`（不变） | |
| 光标初值 | 每次打开从中心开始（不变） | 相对位移积分，不是绝对鼠标位置 |

- 轴灵敏度从 `UPlayerInput::GetAxisProperties(EKeys::MouseX)` 读取，读不到才退回 0.07；这样改轴配置或换输入口径时不必再改轮盘。
- `MouseY` 在映射里 `Scale=-1`，符号已经体现在传入值里，换算只取灵敏度大小，不翻转方向。

## 数据与动作

不涉及存档、道具、扣除与保存。`SelectAmmoWheelHand`、`ReloadInputReleased`、`StartAmmoSwitch` 全部保持原样。

## 状态与输入

| 状态 | 行为 |
| --- | --- |
| 未打开轮盘 | `Turn/LookUp` 走相机，不受影响 |
| 轮盘打开 | 轴值只驱动预选光标，不转相机、不开火 |
| 中心死区内 | `Hover=INDEX_NONE`，松 R 视为取消 |
| 打开期间失焦／死亡／换枪／动作阻塞 | 取消并移除轮盘（`UpdateAmmoSelection`，未改） |

## 文件范围与交付

- 本文件与 [弹药袋面板闪动修复](ammo-pouch-flicker-plan-20260921.md)。
- 源码：`Source/FPSGAME/FPSGAMECharacterAmmo.cpp`（轴值→像素）、`Source/FPSGAME/UI/ColdSteelAmmoWheel.cpp`（增益与控制台变量）。
- 复用资源：无新增资源。
- 必要构建：`FPSGAMEEditor Win64 Development`。
- 用户明确要求的预览／检查／测试：未要求，由用户测试手感。
- 完成后记录实际完成项与未测试项。

## 实施记录（2026-09-21）

- `FPSGAMECharacterAmmo.cpp`：新增文件内静态换算 `MouseAxisToScreenPixels()`，从 `UPlayerInput::GetAxisProperties(EKeys::MouseX)` 读灵敏度，读不到退回 0.07；`MoveAmmoPointer` 改为 `AmmoWheel->MovePointer(Delta * 换算系数)`。
- `ColdSteelAmmoWheel.cpp`：新增 `fps.AmmoWheel.PixelsPerRadius`（默认 180，下限 40）；`MovePointer` 改为 `Pointer=(Pointer+Delta/PixelsPerRadius).GetClampedToMaxSize(.96)`，其余（死区、滞回、越界裁剪、`Invalidate(Paint)`）未动。
- `ColdSteelAmmoWheel.h`：只加注释说明 `MovePointer` 的单位是屏幕像素，无结构变化。
- 效果：走满半径所需鼠标位移从约 2857 px 降到 180 px（约 16 倍）；`fps.AmmoWheel.PixelsPerRadius 120` 可再快一档。
- 编译：单文件编译 `ColdSteelAmmoWheel.cpp`、`FPSGAMECharacterAmmo.cpp` 通过；随后常规构建 `Tools/Build/Build-Editor.ps1`（`FPSGAMEEditor Win64 Development`）`Result: Succeeded`，已重新链接 `Binaries/Win64/UnrealEditor-FPSGAME.dll`（23:45:28），日志 `Saved/BuildEditor/build-20260921-234512.log`。第一次构建因另一会话新增的 `FPSBodyAssetPreloader.cpp` 缺头文件路径失败（exit 6），该文件在构建过程中已被其会话修正，重试通过；本批源码未受影响。
- 未测试：实战手感、双持左右手切换时的指针、`fps.AmmoWheel.PixelsPerRadius` 的取值区间，均由用户实测。